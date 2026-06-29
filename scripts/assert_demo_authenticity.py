#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""assert_demo_authenticity.py — prove the recorded demo shows REAL tool calls.

Phase-1 (P0) automated check (outline §"Automated Verification"): the recorded run
must scroll GENUINE agent activity, not the old scripted progress ticker. Before P0,
the left pane was driven by a `printf` loop that emitted a fixed string
("… in progress … (tick N) — grounding via query_cto_knowledge, surface live"); the
real per-tool-call events are not streamed to any tailable agent.log on the `-z`
path; the authoritative record is the per-profile Hermes session store
(~/.hermes/profiles/<profile>/state.db, `messages` table). record_run.sh drains that
store after the run and appends one `[live] tool <name> completed` line per GENUINE
tool call into recordings/agent_<job>_<ts>.log (the file the recorder's xterm tails),
while a recorder heartbeat keeps the surface non-static during the run.

This gate asserts that authenticity is what landed in the log:

  1. >= 1 REAL tool-call COMPLETION line is present — either the raw Hermes form
     (`agent.tool_executor: tool <name> completed (...)`) OR the sed-normalized
     surface form the host tee writes (`[live] tool <name> completed`). A concrete
     tool name (e.g. `mcp_cto_knowledge_query_cto_knowledge`) must appear.
  2. the log is NOT just the old scripted ticker — it must contain at least one
     real tool line that is NOT the fixed ticker string. (We do not fail merely
     because a ticker-like line exists; we fail if there is NO real tool line.)

Exit 0 on PASS, 1 on FAIL. exit 2 on usage error.

Usage:
  python3 scripts/assert_demo_authenticity.py recordings/agent_hero_<ts>.log
  python3 scripts/assert_demo_authenticity.py            # newest recordings/agent_*.log
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RECORDINGS = REPO_ROOT / "recordings"

# A genuine tool-call completion line, in either form:
#   raw Hermes:  ... agent.tool_executor: tool <name> completed (0.08s, 13555 chars)
#   normalized:  [live] tool <name> completed
# The tool name must be a concrete identifier (so the fixed-ticker string, which has
# no "tool <name> completed", never matches).
REAL_TOOL_RE = re.compile(
    r"(?:agent\.tool_executor:\s*tool|\[live\]\s*tool)\s+([A-Za-z0-9_.\-]+)\s+completed",
)
# The old scripted ticker string we are replacing (must NOT be the only content).
OLD_TICKER_RE = re.compile(r"in progress .*\(tick \d+\).*surface live")


def _newest_log() -> Path | None:
    if not RECORDINGS.is_dir():
        return None
    logs = sorted(RECORDINGS.glob("agent_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def main(argv: list[str]) -> int:
    if argv:
        path = Path(argv[0])
    else:
        nl = _newest_log()
        if nl is None:
            print(f"FAIL: no recordings/agent_*.log found under {RECORDINGS}")
            return 1
        path = nl
        print(f"(no path given — using newest log: {path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path})")

    if not path.is_file():
        print(f"FAIL: log not found: {path}")
        return 1

    text = path.read_text(errors="replace")
    real_tools = REAL_TOOL_RE.findall(text)
    ticker_hits = OLD_TICKER_RE.findall(text)

    ok = True
    print(f"log: {path}  ({path.stat().st_size} bytes)")

    if real_tools:
        distinct = sorted(set(real_tools))
        print(f"PASS: >= 1 REAL tool-call completion line present "
              f"({len(real_tools)} line(s), {len(distinct)} distinct tool(s): {distinct[:5]})")
    else:
        print("FAIL: no real 'agent.tool_executor'/'[live] tool ... completed' line — "
              "the demo log shows no genuine tool call (scripted ticker only?)")
        ok = False

    # Informational: the old ticker may coexist transiently, but a real tool line
    # must dominate the authenticity claim. We only fail on its ABSENCE (above).
    if ticker_hits:
        print(f"NOTE: {len(ticker_hits)} old-style ticker line(s) also present "
              f"(tolerated — the real tool line above is the load-bearing proof)")
    else:
        print("ok: no scripted-ticker lines (clean real-event stream)")

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
