#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""assert_fullbuild_ticket.py — verify the comprehensive full-build epic (Phase 5).

Asserts that Linear `find`/`list_issues` returns the single full-build ticket (design Q1) and
that it carries the EXPECTED structure: all 5 phases as sections, the PRIORITIZED P1–P4 deferred
backlog (in order), and the remaining original deferred items. This is the Phase-5 validation
"Linear find_issues returns the full-build ticket with the expected sub-task/section structure."

Exit 0 on PASS, 1 on FAIL. Reads via scripts/linear_mcp.py (same MCP endpoint Hermes uses).

GLO-14 Phase 7 (closeout) extension: with `--next-epic` (the GLO-14-closeout-authored epic), the
structural-section checks are relaxed (the next epic is a roadmap, not the 5-phase build record) and
instead it asserts the body carries the ROLLED-FORWARD items the closeout must capture — Moderne,
the mem0 (OSS server + Next.js) dashboard, OpenHands — AND that the epic was snapshotted to
`tickets/<ID>.md` (AGENTS.md rule 7). The closeout epic is discovered by its distinctive title
prefix when no id is given.

Usage:
  python3 scripts/assert_fullbuild_ticket.py             # discover the [Full-Build] ticket
  python3 scripts/assert_fullbuild_ticket.py GLO-13       # a specific id
  python3 scripts/assert_fullbuild_ticket.py --next-epic  # the GLO-14-closeout-authored next epic
  python3 scripts/assert_fullbuild_ticket.py --next-epic GLO-20
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linear_mcp as L  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
TICKETS_DIR = REPO_ROOT / "tickets"

# Distinctive title prefix of the GLO-14-closeout-authored next epic.
CLOSEOUT_TITLE_PREFIX = "[Full-Build] Sovereign CTO Stack — next epic (GLO-14"


def _labels(issue: dict) -> list[str]:
    out = []
    for x in issue.get("labels") or []:
        out.append(x.get("name") if isinstance(x, dict) else x)
    return [s for s in out if s]


def _discover() -> str | None:
    # the bracketed query is fuzzy on this server; search the plain token and filter by prefix
    res = L.tool("list_issues", {"query": "Full-Build", "team": L.TEAM, "limit": 25})
    issues = res.get("issues", res) if isinstance(res, dict) else res
    for i in issues or []:
        if str(i.get("title", "")).startswith("[Full-Build]"):
            return i.get("id") or i.get("identifier")
    # fallback: scan the recent list
    res = L.tool("list_issues", {"team": L.TEAM, "limit": 50, "orderBy": "createdAt"})
    issues = res.get("issues", res) if isinstance(res, dict) else res
    for i in issues or []:
        if str(i.get("title", "")).startswith("[Full-Build]"):
            return i.get("id") or i.get("identifier")
    return None


def _discover_closeout() -> str | None:
    # the bracketed/fuzzy "Full-Build" search can lag the index for a just-filed ticket, so
    # also scan the recent createdAt list (same fallback pattern as _discover()).
    for params in (
        {"query": "Full-Build", "team": L.TEAM, "limit": 50},
        {"team": L.TEAM, "limit": 50, "orderBy": "createdAt"},
    ):
        res = L.tool("list_issues", params)
        issues = res.get("issues", res) if isinstance(res, dict) else res
        for i in issues or []:
            if str(i.get("title", "")).startswith(CLOSEOUT_TITLE_PREFIX):
                return i.get("id") or i.get("identifier")
    return None


def _snapshot_carries_rolled_forward(ident: str) -> tuple[bool, str]:
    """The closeout epic must be snapshotted to tickets/<ID>.md (rule 7) and the snapshot
    must itself carry the rolled-forward items (proves the persisted record is complete)."""
    snap = TICKETS_DIR / f"{ident}.md"
    if not snap.is_file():
        return False, f"snapshot {snap.relative_to(REPO_ROOT)} missing"
    body = snap.read_text()
    needed = ["Moderne", "OpenHands"]
    missing = [n for n in needed if n not in body]
    if missing:
        return False, f"snapshot present but missing {missing}"
    if "dashboard" not in body:
        return False, "snapshot present but missing the mem0 dashboard item"
    return True, f"snapshot {snap.relative_to(REPO_ROOT)} carries the rolled-forward items"


def _next_epic_checks(desc: str, labels: list[str], ident: str) -> dict:
    """Closeout (GLO-14 Phase 7): the next epic is a roadmap — assert it ROLLS FORWARD the
    deferred items and was snapshotted to tickets/, rather than the 5-phase build structure."""
    snap_ok, snap_msg = _snapshot_carries_rolled_forward(ident)
    return {
        "rolls forward Moderne/OpenRewrite (no account; OSS-pilot option preserved)":
            "Moderne" in desc and ("OpenRewrite" in desc),
        "rolls forward the mem0 OSS server + Next.js dashboard":
            "dashboard" in desc and ("Next.js" in desc or "mem0 OSS server" in desc),
        "rolls forward OpenHands via Portal/LiteLLM":
            "OpenHands" in desc and "LiteLLM" in desc,
        "captures the Greptile global out-of-repo prerequisite":
            "Greptile" in desc and "out-of-repo" in desc.replace("out of repo", "out-of-repo"),
        "captures the live-profile skill-deploy discovery":
            "skill-deploy" in desc or "live-profile" in desc.lower(),
        "captures the duplicate-finding dedupe discovery":
            "dedupe" in desc.lower() or "duplicate" in desc.lower(),
        "Part D recurrence (author the next epic) preserved":
            "Part D" in desc and "next full-build epic" in desc,
        "Full-Build label attached": any((l or "").lower() == "full-build" for l in labels),
        f"snapshotted to tickets/ ({snap_msg})": snap_ok,
    }


def main(argv: list[str]) -> int:
    next_epic = False
    rest: list[str] = []
    for a in argv:
        if a in ("--next-epic", "--next", "--closeout-epic", "--closeout"):
            next_epic = True
        else:
            rest.append(a)

    L.init()
    if next_epic:
        ident = rest[0] if rest else _discover_closeout()
        if not ident:
            print("FAIL: no GLO-14-closeout next epic found via list_issues "
                  "(file it first: scripts/file_fullbuild_ticket.py --closeout-epic)")
            return 1
    else:
        ident = rest[0] if rest else _discover()
    if not ident:
        print("FAIL: no [Full-Build] ticket found via list_issues")
        return 1

    full = L.tool("get_issue", {"id": ident})
    issue = full.get("issue", full) if isinstance(full, dict) else full
    if not isinstance(issue, dict) or not issue.get("id"):
        print(f"FAIL: could not fetch {ident}")
        return 1

    desc = issue.get("description", "") or ""
    labels = _labels(issue)
    title = str(issue.get("title", ""))
    snap_ident = issue.get("identifier") or issue.get("id") or ident
    print(f"ticket: {issue.get('id')} — {title[:60]}")
    print(f"url: {issue.get('url','')}")
    print(f"labels: {labels}")

    if next_epic:
        checks = _next_epic_checks(desc, labels, snap_ident)
        checks = {"title is the [Full-Build] next epic": title.startswith("[Full-Build]"),
                  **checks}
        ok = True
        for k, v in checks.items():
            print(("PASS" if v else "FAIL"), "-", k)
            ok = ok and v
        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    checks = {
        "title is the [Full-Build] epic": str(issue.get("title", "")).startswith("[Full-Build]"),
        "all 5 phases as sections (Phase 0–5)": all(f"Phase {n}" in desc for n in range(0, 6)),
        "P1 — egress hardening (NemoClaw/OpenShell + policy.yaml)":
            "P1 — NemoClaw" in desc and "policy.yaml" in desc,
        "P2 — Stripe (PMF revenue grounding + billing tech-debt)":
            "P2 — Stripe" in desc and "MRR" in desc,
        "P3 — SonarQube + graphify(KEEP) → Hermes judgment → Codegen/Moderne":
            all(s in desc for s in ["P3 — SonarQube", "graphify (KEEP IT)", "JUDGMENT",
                                    "Codegen", "Moderne"]),
        "P3 notes GLO-12 independently proposed the gap": "GLO-12" in desc,
        "P4 — PMF full version, RICE/ICE ranked": "P4 — PMF" in desc and "RICE/ICE" in desc,
        "remaining deferred items (mem0 dashboard / OpenHands / 2nd account / video)":
            all(s in desc for s in ["Next.js dashboard", "OpenHands", "Second-account",
                                    "authenticity"]),
        "Full-Build label attached": any((l or "").lower() == "full-build" for l in labels),
    }

    ok = True
    for k, v in checks.items():
        print(("PASS" if v else "FAIL"), "-", k)
        ok = ok and v

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
