#!/usr/bin/env python3
"""assert_product_ticket.py — verify the filed [Product] opportunity ticket.

Phase-4 follow-up (TASK 2): after the PMF agent produces a market brief it must
close the loop into ONE market-informed product-gap opportunity, filed as a
HumanLayer-ready [Product] Linear ticket. This asserts that ticket exists and is
the grounded artifact the loop is supposed to produce:

  1. a [Product] ticket exists — carries the `Product` LABEL, or (fallback) the
     `[Product]` title prefix as the marker;
  2. its description references a CONCRETE CAPABILITY GAP — a "gap"/"capability"
     statement (the thing the product cannot do today that the market wants);
  3. it carries a MARKET URL — at least one `https://...` source from the web scrape;
  4. it carries a RAG GROUNDING citation — a "Grounded in: <something>.md" line
     naming a corpus source_file (multi-angle union; >= 1 real corpus *.md).

Exit 0 on PASS, 1 on FAIL. Reads tickets via scripts/linear_mcp.py (same MCP
endpoint Hermes uses; OAuth token from the gitignored Hermes token cache).

Usage:
  python3 scripts/assert_product_ticket.py             # newest [Product] ticket
  python3 scripts/assert_product_ticket.py GLO-12       # a specific id
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linear_mcp as L  # noqa: E402

URL_RE = re.compile(r"https://[^\s)\]]+")
GROUNDED_RE = re.compile(r"Grounded in:[^\n]*?([A-Za-z0-9_\-]+\.md)", re.IGNORECASE)
# a "concrete capability gap" reads as a gap/capability/cannot/missing statement
GAP_RE = re.compile(r"\b(gap|capability|cannot|can't|does not|doesn't|lacks?|missing|unable)\b",
                    re.IGNORECASE)
CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"


def _labels(issue: dict) -> list[str]:
    out: list[str] = []
    for x in issue.get("labels") or []:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            out.append(x.get("name") or x.get("id") or "")
    return [s for s in out if s]


def _corpus_sources() -> set[str]:
    if CORPUS_DIR.is_dir():
        return {p.name.lower() for p in CORPUS_DIR.glob("*.md")}
    return set()


def main(argv: list[str]) -> int:
    L.init()
    want_id = argv[0] if argv else None

    if want_id:
        full = L.tool("get_issue", {"id": want_id})
        full = full.get("issue", full) if isinstance(full, dict) else full
        if not isinstance(full, dict) or not full.get("id"):
            print(f"FAIL: could not fetch issue {want_id}")
            return 1
        issue = full
    else:
        res = L.tool("list_issues", {"query": "[Product]", "team": L.TEAM, "limit": 25})
        issues = res.get("issues", res) if isinstance(res, dict) else res
        product = [i for i in issues if str(i.get("title", "")).startswith("[Product]")]
        if not product:
            print("FAIL: no [Product] ticket found in Linear")
            return 1
        ident = product[0].get("id") or product[0].get("identifier")
        full = L.tool("get_issue", {"id": ident})
        issue = full.get("issue", full) if isinstance(full, dict) else full

    ident = issue.get("id") or issue.get("identifier")
    title = issue.get("title", "")
    desc = issue.get("description", "") or ""
    labels = _labels(issue)

    ok = True
    print(f"ticket: {ident} — {title}")
    print(f"url: {issue.get('url','')}")

    # 1. [Product] marker — label OR title prefix
    has_label = any(l.lower() == "product" for l in labels)
    has_prefix = "[Product]" in title
    if has_label:
        print(f"PASS: Product label attached (labels={labels})")
    elif has_prefix:
        print(f"PASS: [Product] title marker present (label not attached; labels={labels})")
    else:
        print(f"FAIL: no Product label and no [Product] title marker (labels={labels})")
        ok = False

    # 2. concrete capability gap
    if GAP_RE.search(desc):
        m = GAP_RE.search(desc)
        ctx = " ".join(desc[max(0, m.start() - 40):m.end() + 60].split())
        print(f"PASS: references a concrete capability gap -> …{ctx}…")
    else:
        print("FAIL: no capability-gap language (gap/capability/cannot/lacks/missing) in body")
        ok = False

    # 3. market URL
    urls = URL_RE.findall(desc)
    if urls:
        print(f"PASS: carries a market source URL -> {urls[0]}")
    else:
        print("FAIL: no market source URL (https://...) in the ticket body")
        ok = False

    # 4. RAG grounding citation (multi-angle union; >=1 real corpus *.md)
    grounded = {s.lower() for s in GROUNDED_RE.findall(desc)}
    if grounded:
        print(f"PASS: carries 'Grounded in:' citation(s) ({len(grounded)}): {sorted(grounded)}")
        corpus = _corpus_sources()
        if corpus:
            real = grounded & corpus
            if real:
                print(f"PASS: >= 1 citation maps to a real corpus text: {sorted(real)}")
            else:
                print(f"FAIL: none of the cited sources exist in corpus/ ({sorted(grounded)})")
                ok = False
        else:
            print("NOTE: corpus/ not present locally; accepting citation-string presence")
    else:
        print("FAIL: no RAG grounding citation ('Grounded in: ...*.md') in description")
        ok = False

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
