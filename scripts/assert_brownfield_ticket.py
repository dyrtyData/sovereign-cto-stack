#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""assert_brownfield_ticket.py — verify the filed [Brownfield] Linear ticket.

Phase-3 automated check (outline §"Automated Verification"): read the newly
created ticket back over the Linear MCP and assert it is the grounded,
HumanLayer-ready artifact the loop is supposed to produce:

  1. a [Brownfield] ticket exists (title prefix) and carries the `Brownfield`
     LABEL (labelIds);
  2. its description references >= 1 concrete `src/<service>/` file;
  3. its description contains a RAG grounding citation — a "Grounded in:" line
     naming a corpus `*.md` source_file;
  4. (multi-angle grounding, FIX 1/2) it cites the UNION of the distinct sources a
     multi-angle audit returns — at minimum BOTH `managing-technical-debt.md` and
     `software-architecture.md` (the two top-ranked texts the original single-query
     pass missed), and >= 4 distinct `Grounded in:` source_files overall.

Exit 0 on PASS, 1 on FAIL. Reads tickets via scripts/linear_mcp.py (same MCP
endpoint Hermes uses; OAuth token from the gitignored Hermes token cache).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linear_mcp as L  # noqa: E402

SRC_FILE_RE = re.compile(r"src/[A-Za-z0-9_\-]+/[A-Za-z0-9_./\-]+")
GROUNDED_RE = re.compile(r"Grounded in:.*?[A-Za-z0-9_\-]+\.md", re.IGNORECASE | re.DOTALL)
# every distinct source_file cited on a "Grounded in:" line
GROUNDED_SRC_RE = re.compile(r"Grounded in:[^\n]*?([A-Za-z0-9_\-]+\.md)", re.IGNORECASE)
# the two top-ranked corpus texts the single-query pass missed (must be cited now)
REQUIRED_SOURCES = {"managing-technical-debt.md", "software-architecture.md"}
MIN_DISTINCT_SOURCES = 4


def _labels_of(issue: dict) -> list[str]:
    labels = issue.get("labels") or issue.get("labelIds") or []
    out = []
    for x in labels:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            out.append(x.get("name") or x.get("id") or "")
    return [s for s in out if s]


def main() -> int:
    L.init()
    res = L.tool("list_issues", {"query": "[Brownfield]", "team": L.TEAM, "limit": 25})
    issues = res.get("issues", res) if isinstance(res, dict) else res
    brownfield = [i for i in issues if str(i.get("title", "")).startswith("[Brownfield]")]
    if not brownfield:
        print("FAIL: no [Brownfield] ticket found in Linear")
        return 1

    # newest first; verify the most recent one fully (fetch full description)
    issue = brownfield[0]
    ident = issue.get("id") or issue.get("identifier")
    full = L.tool("get_issue", {"id": ident})
    full = full.get("issue", full) if isinstance(full, dict) else full
    title = full.get("title", "")
    desc = full.get("description", "") or ""
    labels = _labels_of(full)

    ok = True
    print(f"ticket: {ident} — {title}")

    if "[Brownfield]" in title:
        print("PASS: title carries [Brownfield] prefix")
    else:
        print("FAIL: title missing [Brownfield] prefix"); ok = False

    if any(l.lower() == "brownfield" for l in labels):
        print(f"PASS: Brownfield label attached (labels={labels})")
    else:
        print(f"FAIL: Brownfield label NOT attached (labels={labels})"); ok = False

    files = sorted(set(SRC_FILE_RE.findall(desc)))
    if files:
        print(f"PASS: references concrete src/<service>/ file(s): {files[:5]}")
    else:
        print("FAIL: no concrete src/<service>/ file referenced"); ok = False

    m = GROUNDED_RE.search(desc)
    if m:
        snippet = " ".join(m.group(0).split())[:160]
        print(f"PASS: grounding citation present -> {snippet!r}")
    else:
        print("FAIL: no RAG grounding citation ('Grounded in: ...*.md') in description"); ok = False

    # multi-angle grounding: cite the UNION, incl. the two top texts and >= MIN distinct
    grounded_sources = {s.lower() for s in GROUNDED_SRC_RE.findall(desc)}
    print(f"grounding sources cited ({len(grounded_sources)}): {sorted(grounded_sources)}")
    missing = REQUIRED_SOURCES - grounded_sources
    if not missing:
        print(f"PASS: required multi-angle sources cited ({sorted(REQUIRED_SOURCES)})")
    else:
        print(f"FAIL: missing required grounding source(s): {sorted(missing)}"); ok = False
    if len(grounded_sources) >= MIN_DISTINCT_SOURCES:
        print(f"PASS: cites >= {MIN_DISTINCT_SOURCES} distinct grounding sources "
              f"(multi-angle union, not single-query)")
    else:
        print(f"FAIL: only {len(grounded_sources)} distinct grounding source(s); "
              f"expected >= {MIN_DISTINCT_SOURCES} (multi-angle union)"); ok = False

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
