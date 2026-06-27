#!/usr/bin/env python3
"""assert_fullbuild_ticket.py — verify the comprehensive full-build epic (Phase 5).

Asserts that Linear `find`/`list_issues` returns the single full-build ticket (design Q1) and
that it carries the EXPECTED structure: all 5 phases as sections, the PRIORITIZED P1–P4 deferred
backlog (in order), and the remaining original deferred items. This is the Phase-5 validation
"Linear find_issues returns the full-build ticket with the expected sub-task/section structure."

Exit 0 on PASS, 1 on FAIL. Reads via scripts/linear_mcp.py (same MCP endpoint Hermes uses).

Usage:
  python3 scripts/assert_fullbuild_ticket.py            # discover the [Full-Build] ticket
  python3 scripts/assert_fullbuild_ticket.py GLO-13      # a specific id
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linear_mcp as L  # noqa: E402


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


def main(argv: list[str]) -> int:
    L.init()
    ident = argv[0] if argv else _discover()
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
    print(f"ticket: {issue.get('id')} — {issue.get('title','')[:60]}")
    print(f"url: {issue.get('url','')}")
    print(f"labels: {labels}")

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
