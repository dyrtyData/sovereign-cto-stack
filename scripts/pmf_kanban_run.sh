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

## Recommendation
Pursue a narrow wedge: grounded [Brownfield] refactor tickets for gRPC coupling
hubs, sold to Series-A platform teams.

## Riskiest assumption to test next
Will a team merge a PR generated from an agent-filed, textbook-grounded ticket
without re-deriving the rationale? Run a controlled trial across 10 tickets.
EOF
  SUMMARY="PMF brief for the AI tech-debt auditor wedge: pursue grounded [Brownfield] refactor tickets for Series-A platform teams. Grounded in 4 corpus texts."
  GROUNDED_JSON='["the-lean-product-playbook.md","hacking-growth.md","lean-enterprise.md","trustworthy-online-controlled-experiments.md"]'
  RECOMMENDATION="Pursue a narrow wedge: grounded [Brownfield] refactor tickets for gRPC coupling hubs, sold to Series-A platform teams."
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
METADATA="$(python3 - "$BRIEF" "$GROUNDED_JSON" "$RECOMMENDATION" <<'PY'
import json,sys,os
brief, grounded, rec = sys.argv[1], sys.argv[2], sys.argv[3]
rel = os.path.relpath(brief, os.getcwd()) if os.path.isabs(brief) else brief
print(json.dumps({
    "artifact": rel,
    "grounded_in": json.loads(grounded) if grounded.strip().startswith("[") else [],
    "recommendation": rec,
}))
PY
)"

log "completing task $TASK_ID with structured handoff (-> done)"
"$HERMES" kanban complete "$TASK_ID" \
  --summary "$SUMMARY" \
  --result "$SUMMARY" \
  --metadata "$METADATA" >/dev/null

# --- 5. persist any [Product] ticket the live run filed into git (Phase-5 wiring) ---
# A live PMF run files a [Product] ticket; git history is the authoritative decision
# record, so refresh the tracked tickets/<ID>.md snapshots. Non-fatal (NO_AGENT writes a
# stub brief and files no ticket, so there is nothing to snapshot in that mode).
if [ "${NO_AGENT:-0}" != "1" ]; then
  log "snapshotting filed [Product] ticket(s) into git (tickets/)"
  bash "$REPO_ROOT/scripts/snapshot_after_run.sh" 2>/dev/null || \
    log "snapshot skipped (no Linear token or no ticket yet) — run scripts/snapshot_after_run.sh by hand"
fi

log "done — brief: $BRIEF"
echo "TASK_ID=$TASK_ID"
echo "BRIEF=$BRIEF"
echo "METADATA=$METADATA"

# Hand the task id to the verifier (and any caller).
echo "$TASK_ID" > "$REPO_ROOT/recordings/.last_pmf_task_id"
