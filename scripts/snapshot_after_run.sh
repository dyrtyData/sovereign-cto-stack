#!/usr/bin/env bash
#
# snapshot_after_run.sh — wire ticket-filing into git (Phase 5).
#
# Git history is the authoritative decision record (design "Desired End State"); the
# agents file tickets into Linear, so after any filing run this persists them into the
# tracked tickets/<ID>.md via scripts/snapshot_tickets.py.
#
# Two modes:
#   - explicit ids  : snapshot exactly those (e.g. right after the agent reports GLO-13)
#       bash scripts/snapshot_after_run.sh GLO-13 GLO-14
#   - discovery     : with NO args, list every [Brownfield]/[Product] ticket the agents
#                     file on the team and snapshot them all (idempotent)
#       bash scripts/snapshot_after_run.sh
#
# This is the lightweight, minimal wiring the skills point at (their "persist into git"
# step) and the Phase-4 run scripts call as a post-step. It does NOT commit — review the
# diff, then `git add tickets/ && git commit`.
#
# Env:
#   LINEAR_TEAM   team name (default in linear_mcp.py: "Global South Ai Safety")
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

command -v python3 >/dev/null 2>&1 || { echo "snapshot_after_run: python3 not found" >&2; exit 1; }

if [ "$#" -gt 0 ]; then
  echo "=== snapshot_after_run: snapshotting explicit ids: $* ==="
  python3 scripts/snapshot_tickets.py "$@"
  exit $?
fi

echo "=== snapshot_after_run: discovering agent-filed [Brownfield]/[Product] tickets ==="
# Discover ids over the same MCP endpoint, then hand them to snapshot_tickets.py.
mapfile -t IDS < <(python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
import linear_mcp as L
L.init()
ids = []
for q in ("[Brownfield]", "[Product]"):
    res = L.tool("list_issues", {"query": q, "team": L.TEAM, "limit": 50})
    issues = res.get("issues", res) if isinstance(res, dict) else res
    for i in issues or []:
        title = str(i.get("title", ""))
        if title.startswith(q):
            ident = i.get("id") or i.get("identifier")
            if ident:
                ids.append(ident)
# stable, de-duplicated
for ident in sorted(set(ids)):
    print(ident)
PY
)

if [ "${#IDS[@]}" -eq 0 ]; then
  echo "snapshot_after_run: no [Brownfield]/[Product] tickets found to snapshot" >&2
  exit 0
fi

echo "=== snapshot_after_run: snapshotting ${IDS[*]} ==="
python3 scripts/snapshot_tickets.py "${IDS[@]}"
