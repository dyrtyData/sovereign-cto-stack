#!/usr/bin/env python3
"""assert_greptile_instruction.py — verify the standing Greptile review line is filed + snapshotted.

GLO-14 P2 gate (outline Phase 3, design D-3/D-4). The ONLY in-repo Greptile deliverable
is a standing instruction line appended to EVERY filed ticket body — telling whoever picks
the ticket up to run a Greptile PR review (`/greptile`) before requesting merge — plus this
gate that reads it back. There is no in-repo Greptile code, MCP, webhook, or triage; the
CLI / Claude Code skill / `/greptile` command live globally in `~/.claude`, OUTSIDE this repo.

This gate mirrors `assert_brownfield_ticket.py`: it reads the newest filed ticket back over
the SAME Linear MCP endpoint Hermes uses (scripts/linear_mcp.py, OAuth token from the
gitignored Hermes token cache) AND reads the tracked `tickets/<ID>.md` snapshot, asserting
BOTH carry the instruction line. Asserting both proves the line survives the full path:
agent files it into Linear -> snapshot_tickets.py persists it into git.

Exit 0 on PASS, 1 on FAIL.

Usage:
  python3 scripts/assert_greptile_instruction.py            # newest [Brownfield]/[Product]/[Full-Build] ticket
  python3 scripts/assert_greptile_instruction.py GLO-16     # a specific identifier
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linear_mcp as L  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
TICKETS_DIR = REPO_ROOT / "tickets"

# The canonical standing line. We match tolerantly on its load-bearing shape (run Greptile on
# the PR via /greptile and address the findings) so trivial whitespace/wording-around does not
# break the gate, while still requiring the operative instruction.
GREPTILE_RE = re.compile(
    r"run\s+greptile\b.*\(/greptile\).*address\s+the\s+findings",
    re.IGNORECASE | re.DOTALL,
)
# the prefixes the filing skills / epic filer attach to filed tickets
TITLE_PREFIXES = ("[Brownfield]", "[Product]", "[Full-Build]")


def _has_line(text: str) -> bool:
    return bool(GREPTILE_RE.search(text or ""))


def _is_dead(i: dict) -> bool:
    """True if the issue is canceled/duplicate/archived — a ticket that no longer
    represents live, actionable work and must not be the gate's default target
    (e.g. probe-noise duplicates we canceled rather than hard-deleted)."""
    if i.get("archivedAt") or i.get("canceledAt"):
        return True
    state = i.get("statusType") or i.get("status") or i.get("state") or ""
    if isinstance(state, dict):
        state = state.get("type") or state.get("name") or ""
    return str(state).strip().lower() in {"canceled", "cancelled", "duplicate"}


def _newest_filed_identifier() -> str | None:
    """Return the identifier of the most recently created LIVE filed ticket, any kind
    (canceled/duplicate/archived tickets are excluded)."""
    candidates: list[dict] = []
    for query in ("[Brownfield]", "[Product]", "Full-Build"):
        res = L.tool("list_issues", {"query": query, "team": L.TEAM, "limit": 25})
        issues = res.get("issues", res) if isinstance(res, dict) else res
        for i in issues or []:
            if str(i.get("title", "")).startswith(TITLE_PREFIXES) and not _is_dead(i):
                candidates.append(i)
    if not candidates:
        return None
    # de-dupe by identifier, preferring a createdAt sort when available; the MCP returns
    # newest-first per query, so the first-seen order is a sane fallback.
    seen: dict[str, dict] = {}
    for i in candidates:
        ident = i.get("identifier") or i.get("id")
        if ident and ident not in seen:
            seen[ident] = i

    def _key(i: dict):
        return str(i.get("createdAt") or i.get("updatedAt") or "")

    ranked = sorted(seen.values(), key=_key, reverse=True)
    top = ranked[0]
    return top.get("identifier") or top.get("id")


def _snapshot_path(ident: str) -> Path | None:
    """Find the tickets/<ID>.md snapshot. `ident` may be the human id (GLO-16) or a UUID;
    the snapshot file is named by whatever snapshot_tickets.py wrote."""
    direct = TICKETS_DIR / f"{ident}.md"
    if direct.is_file():
        return direct
    # fall back: scan snapshots whose `identifier:` front-matter matches
    if TICKETS_DIR.is_dir():
        for p in sorted(TICKETS_DIR.glob("*.md")):
            head = p.read_text(errors="ignore")[:400]
            if re.search(rf"\*\*identifier:\*\*\s*{re.escape(ident)}\b", head):
                return p
    return None


def main(argv: list[str]) -> int:
    L.init()
    want_id = argv[0] if argv else None

    ident = want_id or _newest_filed_identifier()
    if not ident:
        print("FAIL: no [Brownfield]/[Product]/[Full-Build] ticket found in Linear")
        return 1

    full = L.tool("get_issue", {"id": ident})
    full = full.get("issue", full) if isinstance(full, dict) else full
    if not isinstance(full, dict) or not full.get("id"):
        print(f"FAIL: could not fetch issue {ident}")
        return 1

    real_id = full.get("identifier") or full.get("id") or ident
    title = full.get("title", "")
    desc = full.get("description", "") or ""

    ok = True
    print(f"ticket: {real_id} — {title}")
    print(f"url: {full.get('url', '')}")

    # 1. live Linear ticket body carries the standing instruction line
    if _has_line(desc):
        print("PASS: live Linear ticket body carries the Greptile review instruction line")
    else:
        print("FAIL: live Linear ticket body is MISSING the Greptile review instruction line")
        ok = False

    # 2. the tracked tickets/<ID>.md snapshot carries it too
    snap = _snapshot_path(real_id)
    if snap is None:
        print(f"FAIL: no tickets/<ID>.md snapshot found for {real_id} "
              f"(run scripts/snapshot_tickets.py {real_id})")
        ok = False
    else:
        snap_text = snap.read_text(errors="ignore")
        rel = snap.relative_to(REPO_ROOT)
        if _has_line(snap_text):
            print(f"PASS: snapshot {rel} carries the Greptile review instruction line")
        else:
            print(f"FAIL: snapshot {rel} is MISSING the Greptile review instruction line")
            ok = False

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
