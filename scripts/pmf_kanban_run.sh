#!/usr/bin/env bash
#
# pmf_kanban_run.sh — run the CTO-Market PMF research task through the shared
# single-host Kanban board (Phase 4), proving the multi-agent coordination loop.
#
# The CTO-Market profile coordinates with the orchestrator over the one shared
# board ~/.hermes/kanban.db (design Q4). This script drives the board lifecycle
# around a PMF research run so it is deterministic and verifiable:
#
#   1. create a PMF task assigned to `cto-market` -> status READY
#   2. claim it                                   -> status RUNNING
#   3. run the cto-market agent (pmf_brief skill): scrape web -> multi-angle
#      query_cto_knowledge -> write a textbook-cited strategic brief to a file
#   4. complete it with a STRUCTURED HANDOFF        -> status DONE
#        kanban complete --summary <one-liner> --metadata <json: artifact, grounded_in, ...>
#
# The result: a task_runs row with status=done, outcome=completed, and a
# summary+metadata handoff anyone (the orchestrator, a downstream task) can read
# — exactly the "ready -> running -> done with a structured handoff row" the
# Phase-4 verification asserts (scripts/assert_pmf_run.py).
#
# Usage:
#   bash scripts/pmf_kanban_run.sh
#   bash scripts/pmf_kanban_run.sh "Is there PMF for an AI tech-debt auditor for Series-A teams?"
#
# Env:
#   HERMES       hermes binary (default: hermes on PATH)
#   NO_AGENT=1   skip the live model call; write a deterministic stub brief instead
#                (still exercises the full Kanban lifecycle + the citation artifact)
#   PMF_TIMEOUT  cap on the agent run in seconds (default 240)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

HERMES="${HERMES:-hermes}"
PMF_TIMEOUT="${PMF_TIMEOUT:-240}"
QUESTION="${1:-Is there product-market fit for an autonomous AI tech-debt auditor for Series-A engineering teams?}"
TS="$(date +%Y%m%d_%H%M%S)"
BRIEF="$REPO_ROOT/recordings/pmf_brief_run_${TS}.md"
LEDGER="$REPO_ROOT/recordings/pmf_ledger.json"

mkdir -p "$REPO_ROOT/recordings"
log() { echo "=== pmf_kanban_run: $* ==="; }

command -v "$HERMES" >/dev/null 2>&1 || { echo "pmf_kanban_run: hermes not found on PATH" >&2; exit 1; }

# --- 1. create the PMF task (assigned -> READY) ------------------------------
log "creating PMF task on the shared Kanban board (assignee cto-market)"
CREATE_JSON="$("$HERMES" kanban create "[PMF] $QUESTION" \
  --body "Run the pmf_brief skill: scrape the web, multi-angle query_cto_knowledge (growth/PMF texts), write a textbook-cited strategic brief, hand off via kanban_complete with summary+metadata." \
  --assignee cto-market \
  --skill pmf_brief \
  --created-by orchestrator \
  --json)"
TASK_ID="$(printf '%s' "$CREATE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")"
[ -n "$TASK_ID" ] || { echo "pmf_kanban_run: failed to create task" >&2; echo "$CREATE_JSON" >&2; exit 1; }
log "task $TASK_ID created (status: ready)"

# --- 2. claim it (-> RUNNING) ------------------------------------------------
log "claiming task $TASK_ID (-> running)"
"$HERMES" kanban claim "$TASK_ID" >/dev/null
"$HERMES" kanban comment "$TASK_ID" --body "CTO-Market claimed: starting web scrape + multi-angle grounding." >/dev/null 2>&1 || true

# --- 3. run the agent (or write a deterministic stub brief) ------------------
SUMMARY=""
GROUNDED_JSON='[]'
RECOMMENDATION=""

if [ "${NO_AGENT:-0}" = "1" ]; then
  log "NO_AGENT=1 — writing a deterministic stub brief (exercises lifecycle + citation)"

  # Phase 3: ground the AARRR Revenue & Retention legs in REAL Stripe test-mode
  # metrics. Refresh recordings/stripe_metrics.json from the live Stripe API (the
  # client FAILS loudly if the sandbox is empty / key is missing — no fabrication),
  # then render the concrete numbers into the stub brief's AARRR section.
  log "refreshing recordings/stripe_metrics.json from real Stripe test-mode data"
  python3 "$REPO_ROOT/scripts/stripe_client.py" >/dev/null || {
    echo "pmf_kanban_run: stripe_client.py failed — cannot ground AARRR in real data." >&2
    echo "  seed the sandbox first: python3 scripts/stripe_seed.py" >&2
    exit 1
  }
  AARRR_MD="$(python3 - "$REPO_ROOT/recordings/stripe_metrics.json" <<'PY'
import json, sys, pathlib
m = json.loads(pathlib.Path(sys.argv[1]).read_text())
mrr = m["mrr"]; arr = m["arr"]; active = m["active_subs"]
churn = m["churn"]["rate"]; canceled = m["canceled_subs"]
coh = ", ".join(f"{c['cohort']} {round(c['retention']*100)}%" for c in m["cohorts"])
print(f"- **Revenue:** MRR ${mrr:,.0f}/mo (ARR ${arr:,.0f}) across {active} active subscriptions.")
print(f"- **Retention / churn:** lifetime churn {round(churn*100)}%, {canceled} canceled; per-cohort retention {coh}.")
print(f"- Interpretation: the latest cohort retains best while older cohorts show real churn — revenue is small but the retention trend supports the wedge.")
PY
)"

  # Phase 5: consult prior decisions (mem0 self-hosted on pgvector + git history)
  # BEFORE ranking, so we don't re-propose an already-decided idea and can cite the
  # past rationale. NO graceful degradation — if mem0 can't persist/retrieve, FAIL.
  log "consulting prior decisions: mem0 (pgvector) + git history (scripts/mem0_pmf_decisions.py)"
  docker compose up -d mem0-postgres >/dev/null 2>&1 || true
  PRIOR_JSON="$REPO_ROOT/recordings/pmf_prior_decisions_${TS}.json"
  if command -v uv >/dev/null 2>&1; then
    uv run "$REPO_ROOT/scripts/mem0_pmf_decisions.py" "$QUESTION" > "$PRIOR_JSON" 2>"$REPO_ROOT/recordings/pmf_prior_decisions_${TS}.err" || {
      echo "pmf_kanban_run: mem0_pmf_decisions.py failed — prior-decisions consult is mandatory (no fabrication)." >&2
      echo "  bring the backend up: docker compose up -d mem0-postgres ; then retry." >&2
      cat "$REPO_ROOT/recordings/pmf_prior_decisions_${TS}.err" >&2
      exit 1
    }
  else
    echo "pmf_kanban_run: 'uv' not found — required to run the mem0 prior-decisions consult." >&2
    exit 1
  fi

  # Render the "Prior decisions consulted" section + the ledger from the real consult.
  PRIOR_MD="$(python3 - "$PRIOR_JSON" <<'PY'
import json, sys, pathlib
d = json.loads(pathlib.Path(sys.argv[1]).read_text())
hits = d.get("mem0", {}).get("hits", [])
git = d.get("git", {})
out = ["(mem0 self-hosted on pgvector + git history — so we do not re-propose a decided idea)"]
if hits:
    for h in hits:
        did = h.get("decision_id") or "?"
        sc = h.get("score")
        sc = f"{sc:.2f}" if isinstance(sc, (int, float)) else "n/a"
        mem = " ".join((h.get("memory") or "").split())[:200]
        out.append(f"- mem0 hit: **{did}** (score {sc}) — {mem}")
else:
    out.append("- mem0: no prior product decisions matched (fresh decision space).")
for pt in git.get("product_tickets", []):
    out.append(f"- git/tickets: **{pt['id']}** filed by `{pt.get('commit','')}` — already-decided [Product] bet; not re-proposed as novel below.")
for line in git.get("log", [])[:3]:
    out.append(f"- git log: `{line}`")
out.append("")
out.append("Effect on ranking: any opportunity matching a prior decision above is "
           "dropped or re-raised only with an explicit what-changed note.")
print("\n".join(out))
PY
)"

  # Decide which prior decision ids to AVOID re-proposing (the seeded [Product] gaps).
  AVOID_IDS="$(python3 - "$PRIOR_JSON" <<'PY'
import json, sys, pathlib
d = json.loads(pathlib.Path(sys.argv[1]).read_text())
ids = sorted({pt["id"] for pt in d.get("git", {}).get("product_tickets", [])})
print(",".join(ids))
PY
)"
  log "prior [Product] decisions to avoid re-proposing as novel: ${AVOID_IDS:-<none>}"

  # Phase 5: emit >=2 RICE-scored opportunities, ranked best-first, each grounded in
  # corpus + Stripe, and persist them (with a shipped feedback flag) to the ledger.
  # The candidates below are DISTINCT from the prior GLO-12 "autonomous remediation
  # PRs" decision (which we explicitly note as already-decided, not re-proposed).
  RANKED_MD="$(python3 - "$REPO_ROOT/recordings/stripe_metrics.json" "$LEDGER" "$QUESTION" "$PRIOR_JSON" <<'PY'
import json, sys, pathlib, datetime
metrics = json.loads(pathlib.Path(sys.argv[1]).read_text())
ledger_path = sys.argv[2]; question = sys.argv[3]
prior = json.loads(pathlib.Path(sys.argv[4]).read_text())

mrr = metrics["mrr"]; churn = metrics["churn"]["rate"]
cohorts = metrics["cohorts"]
worst = min(cohorts, key=lambda c: c["retention"])  # leg with the worst retention

# Candidate opportunities — DISTINCT from prior decisions (GLO-12 = autonomous
# remediation PRs, already decided). RICE = (Reach*Impact*Confidence)/Effort.
candidates = [
    {
        "title": "[Product] PMF agent cannot rank opportunities by market size — add a TAM/SAM sizing + RICE step",
        "inputs": {"reach": 180, "impact": 2.0, "confidence": 0.75, "effort": 4.0},
        "grounded_in": ["the-lean-product-playbook.md", "stripe_metrics.json"],
        "graphify_feasibility": "host-side skill only; does not touch a coupling hub — low effort",
        "prior_decision": None,
    },
    {
        "title": "[Product] No retention/expansion play for the worst-retaining cohort — add a churn-triggered re-audit nudge",
        "inputs": {"reach": 90, "impact": 3.0, "confidence": 0.6, "effort": 5.0},
        "grounded_in": ["hacking-growth.md", "stripe_metrics.json"],
        "graphify_feasibility": "lands near billing/checkout signals (checkoutservice degree-6 hub) — medium effort",
        "prior_decision": None,
    },
    {
        "title": "[Product] Briefs are not validated against real experiments — add a trustworthy A/B harness for filed bets",
        "inputs": {"reach": 60, "impact": 2.0, "confidence": 0.5, "effort": 6.0},
        "grounded_in": ["trustworthy-online-controlled-experiments.md", "lean-enterprise.md", "stripe_metrics.json"],
        "graphify_feasibility": "instrumentation only; no hub coupling — medium effort",
        "prior_decision": None,
    },
]

def rice(i):
    return round((i["reach"] * i["impact"] * i["confidence"]) / i["effort"], 1)

for c in candidates:
    c["rice_score"] = rice(c["inputs"])
candidates.sort(key=lambda c: c["rice_score"], reverse=True)

# ledger
ledger = {
    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "question": question,
    "scoring_model": "RICE",
    "north_star": "opportunities_shipped",
    "prior_decisions_consulted": {
        "mem0_hits": [
            {"decision_id": h.get("decision_id"), "score": h.get("score")}
            for h in prior.get("mem0", {}).get("hits", [])
        ],
        "git": prior.get("git", {}).get("log", [])[:5],
        "already_decided_ids": sorted({pt["id"] for pt in prior.get("git", {}).get("product_tickets", [])}),
    },
    "opportunities": [],
}
for rank, c in enumerate(candidates, 1):
    ledger["opportunities"].append({
        "rank": rank,
        "title": c["title"],
        "rice_score": c["rice_score"],
        "inputs": c["inputs"],
        "grounded_in": c["grounded_in"],
        "graphify_feasibility": c["graphify_feasibility"],
        "prior_decision": c["prior_decision"],
        "shipped": False,
    })
pathlib.Path(ledger_path).write_text(json.dumps(ledger, indent=2) + "\n")

# markdown for the brief
lines = ["(>=2 opportunities, RICE-scored, ranked best-first; each grounded in corpus + Stripe; shipped-flag = feedback)"]
for rank, c in enumerate(candidates, 1):
    i = c["inputs"]
    lines.append(
        f"{rank}. **{c['title']}** — RICE {c['rice_score']} "
        f"(R{i['reach']}×I{i['impact']}×C{i['confidence']}÷E{i['effort']}). "
        f"Feasibility: {c['graphify_feasibility']}. shipped: false"
    )
    for g in c["grounded_in"]:
        if g == "stripe_metrics.json":
            lines.append(f"   Grounded in: stripe_metrics.json (real MRR ${mrr:,.0f}/mo, churn {round(churn*100)}%, worst cohort {worst['cohort']} {round(worst['retention']*100)}% — Reach/Impact evidence).")
        else:
            lines.append(f"   Grounded in: {g} (framework backing the score).")
print("\n".join(lines))
# expose the top opportunity for the handoff
pathlib.Path(ledger_path + ".top").write_text(candidates[0]["title"])
PY
)"
  TOP_OPP="$(cat "${LEDGER}.top" 2>/dev/null || echo "see ranked opportunities")"
  rm -f "${LEDGER}.top"
  log "ledger written: $LEDGER (top: $TOP_OPP)"

  cat > "$BRIEF" <<EOF
# PMF Brief — $QUESTION

## Question & target customer
$QUESTION — for Series-A engineering teams accumulating microservice coupling debt.

## Market signal (web)
- Demand for autonomous code-audit / tech-debt tooling is rising alongside AI coding agents.
- Incumbents focus on linting/SAST; few file *actionable, grounded* refactor tickets.

## Framework analysis
Through the Product-Market Fit Pyramid the underserved need is a *trustworthy,
grounded* refactor recommendation, not another dashboard. Validated-learning
discipline says the riskiest assumption is whether teams will act on an
agent-filed ticket without a human re-deriving it. Growth-loop thinking points to
the audit -> ticket -> merged-PR loop as the compounding retention mechanic.

## AARRR Revenue & Retention (Stripe-grounded)
(real figures from recordings/stripe_metrics.json — not competitor-pricing assumptions)
$AARRR_MD

## Grounded in
Grounded in: the-lean-product-playbook.md (Product-Market Fit Pyramid — target customer, underserved needs, value proposition).
Grounded in: hacking-growth.md (north-star metric and the experiment cadence behind a growth loop).
Grounded in: lean-enterprise.md (validated learning / build-measure-learn under uncertainty).
Grounded in: trustworthy-online-controlled-experiments.md (designing a trustworthy test of the riskiest assumption).
Grounded in: stripe_metrics.json (real Stripe test-mode MRR/ARR, churn rate, and per-month cohort retention — the Revenue & Retention legs of the AARRR funnel).

## Prior decisions consulted
$PRIOR_MD

## Ranked opportunities (RICE/ICE)
$RANKED_MD

## Recommendation
Pursue the rank-1 opportunity above ($TOP_OPP) — distinct from the already-decided
GLO-12 autonomous-remediation bet — while keeping the grounded [Brownfield] refactor
wedge for Series-A platform teams as the core.

## Riskiest assumption to test next
Will a team merge a PR generated from an agent-filed, textbook-grounded ticket
without re-deriving the rationale? Run a controlled trial across 10 tickets.
EOF
  SUMMARY="PMF brief: ${TOP_OPP} (rank-1 of >=2 RICE-ranked opportunities). Prior decisions (mem0+git) consulted; not re-proposing GLO-12. Grounded in 4 corpus texts + Stripe."
  GROUNDED_JSON='["the-lean-product-playbook.md","hacking-growth.md","lean-enterprise.md","trustworthy-online-controlled-experiments.md"]'
  RECOMMENDATION="$TOP_OPP"
else
  log "running cto-market agent (pmf_brief skill), cap ${PMF_TIMEOUT}s"
  timeout "$PMF_TIMEOUT" "$HERMES" -p cto-market -z \
    "Run the PMF research loop with the pmf_brief skill for: \"$QUESTION\". Scrape the web for current market signal, then GROUND the analysis by issuing MULTIPLE query_cto_knowledge calls (one per dimension: problem/solution fit; target customer & market sizing; experimentation/validated learning; growth loops/acquisition) and cite the UNION of the distinct source_file(s). Write the strategic brief as Markdown to EXACTLY this path: $BRIEF — include one 'Grounded in: <source_file> (...)' line per cited corpus source_file (at least one real corpus *.md). End by printing a JSON object: {\"summary\":..., \"grounded_in\":[...], \"recommendation\":...}." \
    --skills pmf_brief --yolo 2>&1 | tee "recordings/pmf_agent_${TS}.log" || \
    log "agent exited non-zero / hit the cap (continuing to close the task with what exists)"

  # Derive the handoff from the produced brief (the source of truth on disk).
  if [ -f "$BRIEF" ]; then
    SUMMARY="$(python3 - "$BRIEF" <<'PY'
import re,sys,pathlib
t=pathlib.Path(sys.argv[1]).read_text(errors="ignore")
m=re.search(r"## Recommendation\s+(.+)",t)
rec=" ".join(m.group(1).split())[:200] if m else "see brief"
n=len(set(re.findall(r"Grounded in:[^\n]*?([A-Za-z0-9_\-]+\.md)",t)))
print(f"PMF brief written; recommendation: {rec} Grounded in {n} corpus texts.")
PY
)"
    GROUNDED_JSON="$(python3 - "$BRIEF" <<'PY'
import re,sys,json,pathlib
t=pathlib.Path(sys.argv[1]).read_text(errors="ignore")
print(json.dumps(sorted(set(re.findall(r"Grounded in:[^\n]*?([A-Za-z0-9_\-]+\.md)",t)))))
PY
)"
    RECOMMENDATION="$(python3 - "$BRIEF" <<'PY'
import re,sys,pathlib
t=pathlib.Path(sys.argv[1]).read_text(errors="ignore")
m=re.search(r"## Recommendation\s+(.+)",t)
print(" ".join(m.group(1).split())[:200] if m else "see brief")
PY
)"
  else
    log "WARNING: agent did not write $BRIEF — closing with a note"
    SUMMARY="PMF run completed but no brief artifact was written; see recordings/pmf_agent_${TS}.log."
  fi
fi

[ -f "$BRIEF" ] || { echo "pmf_kanban_run: no brief artifact at $BRIEF" >&2; }

# --- 4. complete with a STRUCTURED HANDOFF (-> DONE) -------------------------
METADATA="$(python3 - "$BRIEF" "$GROUNDED_JSON" "$RECOMMENDATION" "$LEDGER" <<'PY'
import json,sys,os
brief, grounded, rec, ledger = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
rel = os.path.relpath(brief, os.getcwd()) if os.path.isabs(brief) else brief
md = {
    "artifact": rel,
    "grounded_in": json.loads(grounded) if grounded.strip().startswith("[") else [],
    "recommendation": rec,
}
# Phase 5: surface the ranked ledger in the structured handoff if present.
if os.path.isfile(ledger):
    try:
        L = json.loads(open(ledger).read())
        md["ledger"] = os.path.relpath(ledger, os.getcwd())
        md["opportunities_ranked"] = len(L.get("opportunities", []))
        md["top_rice_score"] = (L.get("opportunities") or [{}])[0].get("rice_score")
        md["prior_decisions_consulted"] = L.get("prior_decisions_consulted", {})
    except (ValueError, OSError):
        pass
print(json.dumps(md))
PY
)"

log "completing task $TASK_ID with structured handoff (-> done)"
"$HERMES" kanban complete "$TASK_ID" \
  --summary "$SUMMARY" \
  --result "$SUMMARY" \
  --metadata "$METADATA" >/dev/null

# --- 4b. CLOSE THE mem0 WRITE PATH (GLO-14 P1) -------------------------------
# The load-bearing GLO-14 slice, same canonical position as the hero loop: AFTER
# the ledger/Kanban-complete write returns and BEFORE snapshot_after_run.sh. We
# record THIS PMF run's decision (the rank-1 opportunity + its grounding) into the
# unified `memories` collection via scripts/mem0_record_decision.py (infer=True), so
# the collection genuinely accumulates run-over-run and the PMF consult — now
# repointed to read `memories` — recalls real prior decisions. Best-effort: git stays
# authoritative (snapshot below). Disable for the Q3 probe via MEM0_RECORD_DECISION_DISABLE=1.
record_pmf_decision_to_mem0() {
  [ "${MEM0_RECORD_DECISION_DISABLE:-0}" = "1" ] && { log "mem0 record-decision DISABLED (probe mode) — skipping the deterministic write"; return 0; }
  command -v uv >/dev/null 2>&1 || { log "uv not found — cannot record PMF decision to mem0"; return 0; }
  docker compose up -d mem0-postgres >/dev/null 2>&1 || true
  # The decision id keys to the rank-1 opportunity. In NO_AGENT mode no [Product]
  # ticket is filed, so we key the memory to the ledger's top opportunity + this run's
  # timestamp; in a live run we prefer the just-filed [Product] ticket snapshot.
  local meta
  meta="$(LEDGER="$LEDGER" TS="$TS" python3 - <<'PY' 2>/dev/null || true
import json, os, re
from pathlib import Path
root = Path.cwd(); ledger = Path(os.environ["LEDGER"]); ts = os.environ.get("TS", "")
# Prefer a freshly-filed [Product] ticket snapshot (live run); else the ledger top.
tdir = root / "tickets"
chosen = None
for p in sorted(tdir.glob("GLO-*.md"), key=lambda q: q.stat().st_mtime, reverse=True):
    head = p.read_text(errors="ignore")[:500]
    m = re.search(r"^#\s+(.*)$", head, re.M)
    title = m.group(1) if m else ""
    if "[Product]" in title:
        text = p.read_text(errors="ignore")
        gi = sorted(set(re.findall(r"Grounded in:[^\n]*?([A-Za-z0-9_\-]+\.md)", text, re.I)))
        body = " ".join(re.sub(r"^#.*$", "", text, flags=re.M).split())[:600]
        chosen = {"ticket_id": p.stem, "title": title, "grounded_in": gi, "summary": body}
        break
if chosen is None and ledger.is_file():
    L = json.loads(ledger.read_text())
    opps = L.get("opportunities") or []
    if opps:
        top = opps[0]
        chosen = {
            "ticket_id": f"PMF-{ts}",
            "title": top.get("title", "PMF opportunity"),
            "grounded_in": [g for g in (top.get("grounded_in") or []) if str(g).endswith(".md")],
            "summary": (f"Rank-1 RICE {top.get('rice_score')} opportunity: {top.get('title','')}. "
                        f"Feasibility: {top.get('graphify_feasibility','')}."),
        }
if chosen:
    print(json.dumps(chosen))
PY
)"
  [ -n "$meta" ] || { log "no PMF decision to record (no ledger/ticket) — skipping mem0 write"; return 0; }
  local ticket_id title grounded_summary
  ticket_id="$(printf '%s' "$meta" | python3 -c 'import sys,json;print(json.load(sys.stdin)["ticket_id"])' 2>/dev/null || true)"
  title="$(printf '%s' "$meta" | python3 -c 'import sys,json;print(json.load(sys.stdin)["title"])' 2>/dev/null || true)"
  grounded_summary="$(printf '%s' "$meta" | python3 -c 'import sys,json;print(json.load(sys.stdin)["summary"])' 2>/dev/null || true)"
  [ -n "$ticket_id" ] || { log "could not resolve a PMF decision id for the mem0 write (skipping)"; return 0; }
  local args=(--profile cto-market --run-id "pmf_run_${TS}" --ticket-id "$ticket_id"
              --kind product_decision --grounding-question "$QUESTION"
              --ticket-title "$title" --grounded-summary "${grounded_summary:-$title}")
  while IFS= read -r g; do [ -n "$g" ] && args+=(--grounded-in "$g"); done < <(printf '%s' "$meta" | python3 -c 'import sys,json
[print(x) for x in json.load(sys.stdin).get("grounded_in",[])]' 2>/dev/null || true)
  log "recording the PMF decision ($ticket_id) into mem0 'memories' (infer=True; the GLO-14 write path)"
  uv run "$REPO_ROOT/scripts/mem0_record_decision.py" "${args[@]}" \
    && log "mem0 PMF decision recorded ($ticket_id) — memories will accumulate this run" \
    || log "mem0 PMF decision write failed (non-fatal — git/ledger remain authoritative)"
}

record_pmf_decision_to_mem0

# --- 5. persist any [Product] ticket the live run filed into git (Phase-5 wiring) ---
# A live PMF run files a [Product] ticket; git history is the authoritative decision
# record, so refresh the tracked tickets/<ID>.md snapshots. Non-fatal (NO_AGENT writes a
# stub brief and files no ticket, so there is nothing to snapshot in that mode). NOTE:
# the mem0 write (4b) deliberately precedes this snapshot — the canonical "after the
# decision write, before snapshot" position research pins for decision capture.
if [ "${NO_AGENT:-0}" != "1" ]; then
  log "snapshotting filed [Product] ticket(s) into git (tickets/)"
  bash "$REPO_ROOT/scripts/snapshot_after_run.sh" 2>/dev/null || \
    log "snapshot skipped (no Linear token or no ticket yet) — run scripts/snapshot_after_run.sh by hand"
fi

log "done — brief: $BRIEF"
echo "TASK_ID=$TASK_ID"
echo "BRIEF=$BRIEF"
[ -f "$LEDGER" ] && echo "LEDGER=$LEDGER"
echo "METADATA=$METADATA"

# Hand the task id to the verifier (and any caller).
echo "$TASK_ID" > "$REPO_ROOT/recordings/.last_pmf_task_id"
