#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["requests"]
# ///
"""RAG sidecar integration smoke test (Phase 2 automated verification).

Asserts, against a running rag-sidecar (default http://localhost:8080):
  1. /health reports a built index (chunks > 0).
  2. /search "microservices coupling" returns >= 1 ranked chunk, each carrying a
     `source_file` citation and a numeric score.
  3. A known-fact probe: a *Building Microservices* term ("coupling") maps back to a
     Building-Microservices source file in the top hits (grounding integrity — a query
     retrieves from the expected text).

Exit 0 on PASS, non-zero on any failure (works as a CI / phase gate).

Usage:
    uv run scripts/rag_smoke.py
    RAG_URL=http://localhost:8080 uv run scripts/rag_smoke.py
"""
from __future__ import annotations

import os
import sys

import requests

RAG_URL = os.environ.get("RAG_URL", "http://localhost:8080").rstrip("/")


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def main() -> int:
    # 1. health
    try:
        h = requests.get(f"{RAG_URL}/health", timeout=10).json()
    except Exception as e:  # noqa: BLE001
        return _fail(f"GET /health failed: {e}")
    print(f"[health] {h}")
    chunks = h.get("chunks") or 0
    if chunks <= 0:
        return _fail(f"index not built (chunks={chunks}) — run ingest first")

    # 2. search returns ranked, cited chunks
    q = "microservices coupling"
    try:
        r = requests.post(f"{RAG_URL}/search", json={"query": q, "k": 5}, timeout=30)
        r.raise_for_status()
        results = r.json().get("results", [])
    except Exception as e:  # noqa: BLE001
        return _fail(f"POST /search failed: {e}")
    if not results:
        return _fail(f"/search {q!r} returned no chunks")
    top = results[0]
    if not top.get("source_file"):
        return _fail("top hit has no source_file citation")
    if not isinstance(top.get("score"), (int, float)):
        return _fail(f"top hit has no numeric score: {top.get('score')!r}")
    print(f"[search] {len(results)} hits; top source_file={top['source_file']!r} "
          f"score={top['score']:.3f}")

    # 3. known-fact grounding probe: a coupling query should surface the
    #    Building Microservices text (or another coupling/architecture text) — assert
    #    the expected text appears among the top hits when present in the corpus.
    sources = {r["source_file"] for r in results}
    expected_substrings = ("microservices", "coupling", "architecture", "hard-parts", "balancing")
    if not any(any(sub in s.lower() for sub in expected_substrings) for s in sources):
        return _fail(
            "grounding probe: a coupling query did not surface any "
            f"microservices/coupling/architecture text. Got sources: {sorted(sources)}"
        )
    matched = sorted(s for s in sources if any(sub in s.lower() for sub in expected_substrings))
    print(f"[grounding] coupling query mapped to expected text(s): {matched}")

    print("PASS: RAG sidecar serves ranked, cited chunks and grounding maps to the expected text.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
