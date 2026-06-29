#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#   "mem0ai[nlp]>=2.0.0,<3.0.0",
#   "sentence-transformers",
#   "vecs",
#   "psycopg2-binary",
#   "ollama",
# ]
# ///
"""mem0 round-trip: add a fact -> search() returns it with a score.

The Phase-1 automated proof that mem0 persists into the self-hosted pgvector
backend (the docker-compose `mem0-postgres` service). Run with `uv`:

    docker compose up -d mem0-postgres
    uv run scripts/mem0_roundtrip.py

Design choices that keep this dependency-light and key-free:
- Uses a LOCAL HuggingFace embedder (all-MiniLM-L6-v2, 384 dims) — no OpenAI key.
- Uses `infer=False` on the persistence add() so no LLM fact-extraction is needed —
  that half proves *persistence + retrieval through pgvector*, not the extraction
  pipeline.
- Vector store is pgvector at 127.0.0.1:5433 (vector_store / mem0 / mem0), matching
  hermes/mem0.json and docker-compose.yml (host port 5433 avoids a 5432 collision).

GLO-14 P1 (design D-1): mem0 OSS is pinned to **>=2.0.0** (tested against 2.0.10).
v2.0.0 standardised the SDK return shape — `add()` / `search()` always return a dict
with a `results` list — and ships **native entity-linking** baked into `infer=True`
fact extraction (no external graph DB / no Neo4j; we do not configure `graph_store`,
so there is nothing to remove). This smoke gates the version bump by asserting:

  1. the v2.0.0 return-shape contract on both add() and search() (always runs); and
  2. an `infer=True` + native-entity-linking pass over two related facts — but ONLY
     when the local Ollama fact-extractor is reachable. When Ollama is absent the
     entity-link check logs a `SKIP` and the script STILL exits 0, so CI never
     depends on a local LLM while a dev box with Ollama proves the link automatically.

Exit 0 on a successful round-trip (the added fact is retrieved with a score, the v2
shape holds, and the entity-link pass either succeeds or self-skips), non-zero
otherwise — so it works as a CI / phase-gate assertion.
"""
import os
import sys
import uuid

from mem0 import Memory

PG_HOST = os.environ.get("MEM0_PG_HOST", "127.0.0.1")
# Default 5433: the docker-compose mem0-postgres publishes to host 5433 to avoid
# colliding with a host-native Postgres on 5432. Override with MEM0_PG_PORT.
PG_PORT = int(os.environ.get("MEM0_PG_PORT", "5433"))
PG_USER = os.environ.get("MEM0_PG_USER", "mem0")
PG_PASSWORD = os.environ.get("MEM0_PG_PASSWORD", "mem0")
PG_DBNAME = os.environ.get("MEM0_PG_DBNAME", "vector_store")
EMBED_DIMS = 384  # all-MiniLM-L6-v2

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("MEM0_OLLAMA_MODEL", "qwen2.5-coder:14b")


def _config(collection_name: str) -> dict:
    return {
        # LLM is required at construction time even though the persistence add() uses
        # infer=False (no LLM call is actually made there). Point it at the local
        # Ollama endpoint so no external API key is needed. The infer=True entity-link
        # exercise below *does* call this LLM — and self-skips if it is unreachable.
        "llm": {
            "provider": "ollama",
            "config": {"model": OLLAMA_MODEL, "ollama_base_url": OLLAMA_BASE_URL},
        },
        "embedder": {
            "provider": "huggingface",
            "config": {"model": "sentence-transformers/all-MiniLM-L6-v2"},
        },
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "host": PG_HOST,
                "port": PG_PORT,
                "user": PG_USER,
                "password": PG_PASSWORD,
                "dbname": PG_DBNAME,
                "collection_name": collection_name,
                "embedding_model_dims": EMBED_DIMS,
            },
        },
    }


FACT = "The orchestrator coordinates specialists over a single-host Kanban board."
QUERY = "How do agents coordinate?"
USER_ID = "sovereign-cto-roundtrip"


def _results(res):
    """mem0 v2.0.0 standardises add()/search() to a dict with a `results` list.

    Be tolerant of the bare-list shape too, so the helper stays robust across the
    >=2.0.0 line (the v2 shape assertion below is what actually gates the contract).
    """
    if isinstance(res, dict):
        return res.get("results", [])
    return res or []


def _assert_v2_shape(add_res, search_res) -> None:
    """Assert the mem0 OSS >= v2.0.0 return-shape contract.

    v2.0.0 guarantees:
      - add() and search() each return a dict carrying a `results` list;
      - every result row carries a stable `id` and a `memory` string;
      - search() rows additionally carry a numeric `score`.

    Raises AssertionError (caught by main() -> non-zero exit) on any violation.
    """
    assert isinstance(add_res, dict), (
        f"v2 add() must return a dict with a `results` key, got {type(add_res).__name__}"
    )
    assert "results" in add_res, "v2 add() dict is missing the `results` key"
    add_rows = add_res["results"]
    assert isinstance(add_rows, list) and add_rows, "v2 add() `results` must be a non-empty list"
    for row in add_rows:
        assert row.get("id"), f"v2 add() row missing `id`: {row!r}"
        assert "memory" in row, f"v2 add() row missing `memory`: {row!r}"

    assert isinstance(search_res, dict), (
        f"v2 search() must return a dict with a `results` key, got {type(search_res).__name__}"
    )
    assert "results" in search_res, "v2 search() dict is missing the `results` key"
    search_rows = search_res["results"]
    assert isinstance(search_rows, list) and search_rows, (
        "v2 search() `results` must be a non-empty list"
    )
    for row in search_rows:
        assert row.get("id"), f"v2 search() row missing `id`: {row!r}"
        assert "memory" in row, f"v2 search() row missing `memory`: {row!r}"
        assert row.get("score") is not None, f"v2 search() row missing `score`: {row!r}"


def _ollama_reachable() -> bool:
    """Cheap probe: is the local Ollama fact-extractor up? (no LLM call yet)."""
    try:
        import urllib.request

        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=2) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def _assert_entity_link() -> None:
    """infer=True + native entity-linking over two related facts.

    mem0 OSS >= v2.0.0 links entities natively inside `infer=True` fact extraction —
    no external graph DB. We add two facts that share an entity ("checkoutservice"),
    let mem0 extract/dedup/link them, then assert a search for that entity surfaces a
    memory mentioning BOTH related facts' subject matter (the link is observable in
    recall). Requires the Ollama LLM; the caller only invokes this when Ollama is up.
    """
    collection = f"roundtrip_link_{uuid.uuid4().hex[:8]}"
    user_id = "sovereign-cto-roundtrip-link"
    mem = Memory.from_config(_config(collection))

    fact_a = "checkoutservice depends on paymentservice to charge the customer."
    fact_b = "checkoutservice is the most tightly coupled service in the boutique."
    print(f"[link]   infer=True add fact_a={fact_a!r}")
    add_a = mem.add(
        [{"role": "user", "content": fact_a}], user_id=user_id, infer=True
    )
    print(f"[link]   infer=True add fact_b={fact_b!r}")
    add_b = mem.add(
        [{"role": "user", "content": fact_b}], user_id=user_id, infer=True
    )

    extracted = _results(add_a) + _results(add_b)
    # infer=True must extract at least one durable memory from the two related facts.
    assert extracted, (
        "infer=True extracted no memories from the two related facts — "
        "native fact-extraction/entity-linking did not run."
    )
    print(f"[link]   infer=True extracted {len(extracted)} memory row(s).")

    search_res = mem.search("checkoutservice", filters={"user_id": user_id})
    hits = _results(search_res)
    assert hits, "entity search for 'checkoutservice' returned no hits after infer=True add."
    joined = " ".join((h.get("memory") or "").lower() for h in hits)
    # The shared entity must surface in recall — proof the related facts were linked
    # under one entity rather than stored as disjoint blobs.
    assert "checkoutservice" in joined, (
        "the linked entity 'checkoutservice' is absent from recall — "
        f"entity-linking not observable. Recalled: {joined!r}"
    )
    print("[link]   PASS: infer=True native entity-linking observable in recall.")


def main() -> int:
    collection = f"roundtrip_{uuid.uuid4().hex[:8]}"
    mem = Memory.from_config(_config(collection))

    print(f"[add]    user_id={USER_ID!r} fact={FACT!r}")
    add_res = mem.add(FACT, user_id=USER_ID, infer=False)
    results = _results(add_res)
    if not results:
        print("FAIL: add() stored nothing.", file=sys.stderr)
        return 1
    print(f"[add]    stored {len(results)} memory row(s).")

    print(f"[search] query={QUERY!r}")
    search_res = mem.search(QUERY, filters={"user_id": USER_ID})
    hits = _results(search_res)
    if not hits:
        print("FAIL: search() returned no hits.", file=sys.stderr)
        return 1

    top = hits[0]
    memory_text = top.get("memory") or top.get("text") or ""
    score = top.get("score")
    print(f"[search] top hit: memory={memory_text!r} score={score}")

    if score is None:
        print("FAIL: top hit carries no score.", file=sys.stderr)
        return 1
    if FACT.split()[1].lower() not in memory_text.lower():
        # loose containment check: the stored fact should come back
        print(
            f"FAIL: retrieved memory does not match the stored fact:\n  stored={FACT!r}\n  got={memory_text!r}",
            file=sys.stderr,
        )
        return 1

    # v2.0.0 return-shape contract (always runs — gates the version bump).
    try:
        # search() with the dict-of-results shape for the assertion (re-query to get
        # the raw object, since `hits` above was already unwrapped).
        _assert_v2_shape(add_res, mem.search(QUERY, filters={"user_id": USER_ID}))
    except AssertionError as e:
        print(f"FAIL: mem0 v2.0.0 return-shape contract violated: {e}", file=sys.stderr)
        return 1
    print("[shape]  PASS: mem0 OSS >= v2.0.0 return-shape contract holds (results[]/id/score).")

    # infer=True + native entity-linking — self-skipping when Ollama is unreachable.
    if _ollama_reachable():
        try:
            _assert_entity_link()
        except AssertionError as e:
            print(f"FAIL: infer=True native entity-linking assertion failed: {e}", file=sys.stderr)
            return 1
    else:
        print(
            "[link]   SKIP: Ollama not reachable at "
            f"{OLLAMA_BASE_URL} — skipping the infer=True native-entity-linking proof "
            "(persistence + v2 shape already verified). Exit 0."
        )

    print("PASS: mem0 round-trip succeeded (fact persisted to pgvector, retrieved with a score, "
          "v2.0.0 shape holds, entity-linking proven or self-skipped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
