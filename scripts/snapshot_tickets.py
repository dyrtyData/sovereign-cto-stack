#!/usr/bin/env python3
"""snapshot_tickets.py — persist filed Linear tickets into git as tickets/<ID>.md.

Phase-4 follow-up (TASK 3): git history is the authoritative decision record, but
the filed Linear tickets live only in Linear. This script reads each ticket back
over the SAME Linear MCP endpoint Hermes uses (scripts/linear_mcp.py, OAuth token
from the gitignored Hermes token cache) and writes a TRACKED snapshot to
`tickets/<IDENTIFIER>.md` containing: title, identifier, url, labels, priority,
full description, and a "snapshot captured: <ISO ts>" line.

`tickets/` is deliberately NOT gitignored (the ticket bodies are non-secret), so
the snapshots are committed alongside the code that filed them and Phase 5 can wire
this into the workflow (regenerate snapshots whenever a ticket is filed/updated).

Usage:
  python3 scripts/snapshot_tickets.py GLO-8 GLO-9 GLO-10     # explicit ids
  python3 scripts/snapshot_tickets.py                        # default known set

Env:
  LINEAR_TEAM        team name (default in linear_mcp.py: "Global South Ai Safety")
  TICKETS_DIR        output dir (default: <repo>/tickets)
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linear_mcp as L  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
TICKETS_DIR = Path(os.environ.get("TICKETS_DIR", REPO_ROOT / "tickets"))

# Default ids to snapshot if none are passed (the tickets filed so far).
DEFAULT_IDS = ["GLO-8", "GLO-9"]


def _labels(issue: dict) -> list[str]:
    out: list[str] = []
    for x in issue.get("labels") or []:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            out.append(x.get("name") or x.get("id") or "")
    return [s for s in out if s]


def _priority(issue: dict) -> str:
    p = issue.get("priority")
    if isinstance(p, dict):
        name = p.get("name") or "?"
        val = p.get("value")
        return f"{name} ({val})" if val is not None else str(name)
    return str(p) if p is not None else "None"


def _team(issue: dict) -> str:
    t = issue.get("team")
    if isinstance(t, dict):
        return t.get("name") or t.get("id") or ""
    return str(t) if t is not None else ""


def fetch(ident: str) -> dict:
    full = L.tool("get_issue", {"id": ident})
    full = full.get("issue", full) if isinstance(full, dict) else full
    if not isinstance(full, dict) or not full.get("id"):
        raise RuntimeError(f"could not fetch issue {ident}: {full!r}")
    return full


def render(issue: dict) -> str:
    ident = issue.get("id") or issue.get("identifier") or "?"
    title = issue.get("title", "")
    url = issue.get("url", "")
    labels = _labels(issue)
    status = issue.get("status") or ""
    captured = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    desc = issue.get("description") or "*(no description)*"
    lines = [
        f"# {ident} — {title}",
        "",
        f"- **identifier:** {ident}",
        f"- **url:** {url}",
        f"- **team:** {_team(issue)}",
        f"- **status:** {status}",
        f"- **labels:** {', '.join(labels) if labels else '(none)'}",
        f"- **priority:** {_priority(issue)}",
        f"- **snapshot captured:** {captured}",
        "",
        "## Description",
        "",
        desc.rstrip(),
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ids = argv or DEFAULT_IDS
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    L.init()
    written: list[str] = []
    rc = 0
    for ident in ids:
        try:
            issue = fetch(ident)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL: {ident}: {e}", file=sys.stderr)
            rc = 1
            continue
        real_id = issue.get("id") or ident
        out = TICKETS_DIR / f"{real_id}.md"
        out.write_text(render(issue))
        written.append(str(out.relative_to(REPO_ROOT)))
        print(f"snapshot: {out.relative_to(REPO_ROOT)}  ({issue.get('title','')[:60]!r})")
    print(f"\nwrote {len(written)} snapshot(s) to {TICKETS_DIR.relative_to(REPO_ROOT)}/")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
