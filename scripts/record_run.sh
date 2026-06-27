#!/usr/bin/env bash
#
# record_run.sh — capture an autonomous agent run to recordings/run_<ts>.mp4
# (Phase 4 demo capture for the Hermes Hackathon).
#
# x11grab records PIXELS, so the recorded job MUST drive a VISIBLE surface onto
# the recorder's virtual display :99 BEFORE capture starts (review decision), or
# the .mp4 is a flat black frame. This script therefore, in order:
#
#   1. brings up the recorder sidecar (Xvfb :99 + ffmpeg, healthy);
#   2. PAINTS the visible surface onto :99 *before* triggering the agent
#        - hero  : a LIVE SPLIT-SCREEN — an xterm running `tail -f` on the agent
#                  log (the reasoning/tool calls SCROLL as the loop runs) on the
#                  LEFT, and a browser showing graphify-out/service-graph.html (the
#                  legible frontend=7 / checkout=6 coupling graph) on the RIGHT —
#                  the before→after money shot. The left pane CHANGES over time so
#                  the capture is demonstrably non-static, not a still page.
#        - pmf   : a split-screen of the live PMF agent log (left) + the brief /
#                  research surface (right);
#   3. GUARDS with a non-blank check (a mapped window must exist) — never black;
#   4. starts the recorder (ffmpeg x11grab -> recordings/run_<ts>.mp4);
#   5. TRIGGERS the chosen agent job (default: the Phase-3 tech-debt hero loop),
#      streaming its reasoning into the log the left pane is tailing (live scroll);
#   6. stops the recorder gracefully (q -> finalizes the moov atom);
#   7. verifies the output (valid container, duration>0, moov present, non-blank
#      mid-run frame, AND non-static: >=2 frames at different timestamps differ)
#      via scripts/verify_recording.py.
#
# Keep the laptop PLUGGED IN with the LID OPEN for the recorded run (only you can
# satisfy this — the run drives the agent + capture for 1–3 minutes).
#
# Usage:
#   bash scripts/record_run.sh                 # hero tech-debt loop (default)
#   bash scripts/record_run.sh hero
#   bash scripts/record_run.sh pmf "Is there PMF for an AI tech-debt auditor for Series-A startups?"
#   JOB=hero RECORD_SECONDS=120 bash scripts/record_run.sh
#
# Env:
#   JOB              hero | pmf            (or pass as $1; default hero)
#   RECORD_SECONDS   hard cap on capture if the agent job runs long (default 180)
#   NO_AGENT=1       record the surface only (skip triggering the agent) — useful
#                    to validate the capture pipeline without a live model call
#   HERMES           path to the hermes binary (default: hermes on PATH)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

JOB="${1:-${JOB:-hero}}"
PMF_QUESTION="${2:-${PMF_QUESTION:-Is there product-market fit for an autonomous AI tech-debt auditor for Series-A engineering teams?}}"
RECORD_SECONDS="${RECORD_SECONDS:-180}"
HERMES="${HERMES:-hermes}"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_NAME="run_${JOB}_${TS}.mp4"
SVC="recorder"
EXEC="/opt/recorder/entrypoint.sh"

mkdir -p "$REPO_ROOT/recordings"

# The agent's reasoning/tool-call log. It lives under recordings/ (a host<->container
# BIND MOUNT), so the container's xterm can `tail -f` the SAME file the host agent
# streams into — that is what makes the left pane scroll live during capture. We
# create it now (empty) so tail -f has something to follow the moment we paint.
AGENT_LOG="recordings/agent_${JOB}_${TS}.log"      # host-relative
AGENT_LOG_IN_CTR="/recordings/agent_${JOB}_${TS}.log"  # container path (bind mount)
: > "$REPO_ROOT/$AGENT_LOG"

log() { echo "=== record_run: $* ==="; }

dc() { docker compose "$@"; }
rexec() { dc exec -T "$SVC" "$EXEC" "$@"; }

# --- 0. preconditions --------------------------------------------------------
command -v docker >/dev/null 2>&1 || { echo "record_run: docker not found" >&2; exit 1; }

if [ "$JOB" = "hero" ] && [ ! -f "$REPO_ROOT/graphify-out/service-graph.html" ]; then
  echo "record_run: graphify-out/service-graph.html missing — run scripts/run_graphify.sh first" >&2
  exit 1
fi

# --- 1. bring up the recorder sidecar (Xvfb :99), wait for healthy -----------
log "starting recorder sidecar (Xvfb :99 + ffmpeg)"
dc --profile record up -d --build "$SVC"

log "waiting for recorder display to be ready"
ready=""
for _ in $(seq 1 40); do
  if dc exec -T "$SVC" xdpyinfo -display :99 >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[ -n "$ready" ] || { echo "record_run: recorder display :99 never came up" >&2; dc logs "$SVC" | tail -20 >&2; exit 1; }

# --- 2. PAINT the visible surface onto :99 BEFORE capture --------------------
# Hero & PMF both paint a LIVE SPLIT-SCREEN: an xterm tailing the agent log (left,
# CHANGES as the loop runs) + a browser showing the graph/brief (right). The left
# pane is what makes the recording non-static — it scrolls the agent's reasoning
# and tool calls in real time as they are written to $AGENT_LOG.
case "$JOB" in
  hero)
    log "painting hero split-screen: live agent log (left) + service-graph.html (right)"
    rexec surface-split "$AGENT_LOG_IN_CTR" /graphify-out/service-graph.html "tech-debt audit"
    ;;
  pmf)
    # For PMF the live agent drives a Browser-Use/Playwright session and writes the
    # brief; we tile the live agent log (left) next to a rendered surface (right).
    # If a brief from a prior run exists, show it; otherwise show a research banner.
    # shellcheck disable=SC2012  # timestamped alnum names; -t recency is the intent
    latest_brief="$(ls -t "$REPO_ROOT"/recordings/pmf_brief_*.md 2>/dev/null | head -1 || true)"
    if [ -n "$latest_brief" ]; then
      log "painting pmf split-screen: live agent log (left) + latest brief (right)"
      rexec surface-split "$AGENT_LOG_IN_CTR" "/recordings/$(basename "$latest_brief")" "PMF research"
    else
      log "painting pmf split-screen: live agent log (left) + research banner (right)"
      rexec surface-banner "Sovereign CTO — CTO-Market PMF research run"
      rexec surface-logterm "$AGENT_LOG_IN_CTR" "PMF research"
    fi
    ;;
  *) echo "record_run: unknown JOB '$JOB' (expected hero|pmf)" >&2; exit 2 ;;
esac

# --- 3. GUARD: non-blank — a client window must be mapped on :99 -------------
log "guard: confirming a visible window is mapped on :99 (never record black)"
if ! rexec has-window >/dev/null 2>&1; then
  echo "record_run: GUARD FAILED — no visible window on :99; refusing to record a black frame" >&2
  dc logs "$SVC" | tail -20 >&2
  exit 3
fi
log "guard OK: surface is painted"

# --- 4. start the recorder (ffmpeg x11grab -> recordings/run_<ts>.mp4) -------
log "starting capture -> recordings/$OUT_NAME"
rexec start "$OUT_NAME"

LIVE_FEED_PID=""   # set by start_heartbeat (defined in step 5); cleared on EXIT
stop_recorder() {
  stop_heartbeat 2>/dev/null || true
  log "stopping capture (graceful q -> finalize moov)"
  rexec stop || true
}
trap stop_recorder EXIT

# --- 5. TRIGGER the chosen agent job -----------------------------------------
# Stream the agent's output into $AGENT_LOG (the file the LEFT pane is tailing) so
# the reasoning/tool calls scroll live on screen. `stdbuf -oL -eL` + `tee` keep the
# stream line-buffered so the pane updates continuously (never block-buffered until
# the end — that would make the recording look static, the exact failure we fix).
stream() { stdbuf -oL -eL tee -a "$REPO_ROOT/$AGENT_LOG"; }

# P0 (demo authenticity) — sourcing REAL tool-call events.
# Two facts about Hermes' one-shot `-z` path on this build drive the design:
#   1. it buffers its answer and prints it only at the END, so $AGENT_LOG (the file
#      the left pane tails) would otherwise sit still for most of the run and the
#      recording would read as STATIC; and
#   2. it does NOT stream genuine per-tool-call lines to any tailable agent.log
#      (~/.hermes/logs/agent.log and the per-profile logs/agent.log carry only CLI
#      startup lines for a `-z` run) — so the old "tail the log" source was empty.
# The authoritative record of real tool calls is instead the per-PROFILE Hermes
# session store: ~/.hermes/profiles/<profile>/state.db, `messages` table
# (role='tool', tool_name, timestamp). It is flushed near session end, so we:
#   - run a 2s recorder HEARTBEAT during the agent run → guarantees the surface keeps
#     moving (provably non-static), making no fake claims (it is not the old ticker);
#   - DRAIN the session store after the run and append one real
#       [live] tool <name> completed
#     line per GENUINE tool call into $AGENT_LOG. These are the load-bearing proof
#     that assert_demo_authenticity.py checks (e.g.
#       [live] tool mcp_cto_knowledge_query_cto_knowledge completed ).
LIVE_FEED_SINCE=""   # epoch seconds at agent-launch; window for the session-store drain
start_heartbeat() {
  LIVE_FEED_SINCE="$(date +%s)"
  ( n=0
    while :; do
      n=$((n+1))
      printf '[%s] recorder live — agent running, capturing (elapsed ~%ds)\n' \
        "$(date +%H:%M:%S)" "$((n*2))" >> "$REPO_ROOT/$AGENT_LOG"
      sleep 2
    done ) &
  LIVE_FEED_PID=$!
}
stop_heartbeat() { [ -n "$LIVE_FEED_PID" ] && kill "$LIVE_FEED_PID" 2>/dev/null || true; LIVE_FEED_PID=""; }
# Drain genuine tool-call rows recorded by THIS run from the profile session store and
# append them as real `[live] tool <name> completed` lines (timestamp-windowed to this
# run via LIVE_FEED_SINCE so historical calls are not replayed).
emit_real_tool_calls() {
  local db="$1"
  if ! command -v sqlite3 >/dev/null 2>&1; then
    log "sqlite3 unavailable — cannot drain real tool calls from session store"; return 0
  fi
  [ -f "$db" ] || { log "session store not found ($db) — no real tool lines to emit"; return 0; }
  sleep 1   # let the session-end commit land in state.db
  local out
  out="$(sqlite3 "$db" \
    "SELECT '[live] tool '||COALESCE(NULLIF(tool_name,''),'tool')||' completed' \
       FROM messages \
      WHERE role='tool' AND timestamp > ${LIVE_FEED_SINCE:-0} \
      ORDER BY timestamp;" 2>/dev/null)"
  if [ -n "$out" ]; then
    printf '%s\n' "$out" >> "$REPO_ROOT/$AGENT_LOG"
    log "emitted $(printf '%s\n' "$out" | grep -c 'tool .* completed') real tool-call line(s) from session store"
  else
    log "no real tool rows recorded for this run in $db (gate will report this honestly)"
  fi
}

if [ "${NO_AGENT:-0}" = "1" ]; then
  log "NO_AGENT=1 — no live model call; driving the log pane with a heartbeat for ${RECORD_SECONDS}s"
  # Even without the agent, write a moving heartbeat so the left pane SCROLLS and
  # the recording is provably non-static (validates the capture pipeline offline).
  end=$(( $(date +%s) + RECORD_SECONDS ))
  n=0
  while [ "$(date +%s)" -lt "$end" ]; do
    n=$((n+1))
    printf '[%s] sovereign-cto recorder heartbeat #%d — surface live, frame advancing\n' \
      "$(date +%H:%M:%S)" "$n" >> "$REPO_ROOT/$AGENT_LOG"
    sleep 2
  done
else
  case "$JOB" in
    hero)
      log "triggering the tech-debt hero loop (cto-architecture profile) — output streams to the left pane"
      # The auditor reads the coupling graph (visible on the right), multi-angle
      # grounds via query_cto_knowledge, and files the [Brownfield] ticket; its
      # reasoning scrolls live in the left pane via $AGENT_LOG (+ the ticker).
      start_heartbeat
      timeout "$RECORD_SECONDS" "$HERMES" -p cto-architecture -z \
        "Run the tech-debt audit loop: read graphify-out/service-coupling.json, identify the highest-degree coupling hub, GROUND it by issuing MULTIPLE query_cto_knowledge calls (one per dimension: coupling; technical-debt economics/interest; service decomposition & granularity tradeoffs; delivery/throughput performance) and cite the UNION of the distinct source_file(s). Then file ONE HumanLayer-ready [Brownfield] Linear ticket (team 'Global South Ai Safety', labels ['Brownfield'], priority 2) naming the concrete src/<service>/ file(s) with one 'Grounded in:' line per cited source_file. Use the file_brownfield_ticket skill." \
        --skills file_brownfield_ticket --yolo 2>&1 | stream || \
        log "agent job exited non-zero or hit the ${RECORD_SECONDS}s cap (capture still finalized)"
      emit_real_tool_calls "$HOME/.hermes/profiles/cto-architecture/state.db"
      stop_heartbeat
      ;;
    pmf)
      log "triggering the PMF research run (cto-market profile) — output streams to the left pane"
      BRIEF="recordings/pmf_brief_run_${TS}.md"
      start_heartbeat
      timeout "$RECORD_SECONDS" "$HERMES" -p cto-market -z \
        "Run the PMF research loop with the pmf_brief skill for this question: \"$PMF_QUESTION\". Scrape the web for current market signal, then GROUND the analysis by issuing MULTIPLE query_cto_knowledge calls (one per dimension: problem/solution fit; target customer & market sizing; experimentation/validated learning; growth loops/acquisition) and cite the UNION of the distinct source_file(s). Write the strategic brief to $BRIEF with one 'Grounded in:' line per cited corpus source_file (at least one real corpus *.md). Print the final summary + metadata JSON." \
        --skills pmf_brief --yolo 2>&1 | stream || \
        log "agent job exited non-zero or hit the ${RECORD_SECONDS}s cap (capture still finalized)"
      emit_real_tool_calls "$HOME/.hermes/profiles/cto-market/state.db"
      stop_heartbeat
      ;;
  esac
fi

# --- 5b. close the file->ticket loop on screen (P0 ending) -------------------
# While the recorder is STILL CAPTURING, navigate the right pane to the Linear
# ticket the run just filed so the .mp4 visibly ends on the ticket appearing in the
# browser. We resolve the newest [Brownfield]/[Product] ticket URL over the same
# Linear MCP endpoint Hermes uses (read-only). Best-effort: a missing token (e.g.
# NO_AGENT) or no-ticket-yet simply skips the navigation — the capture still ships.
if [ "${NO_AGENT:-0}" != "1" ] && command -v python3 >/dev/null 2>&1; then
  log "resolving filed ticket URL to navigate the right pane (file->ticket ending)"
  TICKET_URL="$(JOB="$JOB" python3 - <<'PY' 2>/dev/null || true
import os, sys
sys.path.insert(0, "scripts")
try:
    import linear_mcp as L
    L.init()
    prefix = "[Product]" if os.environ.get("JOB") == "pmf" else "[Brownfield]"
    res = L.tool("list_issues", {"query": prefix, "team": L.TEAM, "limit": 25})
    issues = res.get("issues", res) if isinstance(res, dict) else res
    for i in issues or []:
        if str(i.get("title", "")).startswith(prefix):
            ident = i.get("id") or i.get("identifier")
            full = L.tool("get_issue", {"id": ident})
            full = full.get("issue", full) if isinstance(full, dict) else full
            url = (full or {}).get("url") or i.get("url") or ""
            if url:
                print(url)
            break
except Exception:
    pass
PY
)"
  if [ -n "$TICKET_URL" ]; then
    log "navigating right pane to filed ticket: $TICKET_URL"
    rexec navigate "$TICKET_URL" || log "navigate failed (non-fatal) — capture continues"
    # hold a few seconds so the ticket page renders into the capture before stop
    sleep "${TICKET_HOLD_SECONDS:-6}"
  else
    log "no filed ticket URL resolved — skipping file->ticket navigation (capture still ships)"
  fi
fi

# --- 6. stop the recorder (also runs on trap) --------------------------------
stop_recorder
trap - EXIT

OUT_PATH="$REPO_ROOT/recordings/$OUT_NAME"
[ -f "$OUT_PATH" ] || { echo "record_run: expected output $OUT_PATH not produced" >&2; exit 1; }

# --- 7. verify the recording (container/duration/moov + non-blank frame) -----
log "verifying $OUT_PATH"
if command -v python3 >/dev/null 2>&1; then
  python3 "$REPO_ROOT/scripts/verify_recording.py" "$OUT_PATH" || {
    echo "record_run: verification FAILED for $OUT_PATH" >&2; exit 1; }
fi

# --- 8. persist any ticket the live run filed into git (Phase-5 wiring) ------
# A live hero/pmf run files a Linear ticket; git history is the authoritative decision
# record, so refresh the tracked tickets/<ID>.md snapshots. Non-fatal: a missing Linear
# token (e.g. NO_AGENT pipeline check) must not fail the recording.
if [ "${NO_AGENT:-0}" != "1" ]; then
  log "snapshotting filed ticket(s) into git (tickets/)"
  bash "$REPO_ROOT/scripts/snapshot_after_run.sh" 2>/dev/null || \
    log "snapshot skipped (no Linear token or no ticket yet) — run scripts/snapshot_after_run.sh by hand"
fi

log "OK — recording at $OUT_PATH"
echo "$OUT_PATH"
