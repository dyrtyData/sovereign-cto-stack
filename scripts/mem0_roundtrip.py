#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#   "mem0ai",
#   "sentence-transformers",
#   "vecs",
#   "psycopg2-binary",
#   "ollama",
# ]
# ///
"""mem0 round-trip: add a fact -> search() returns it with a score.

The Phase-1 automated proof that mem0 persists into the self-hosted pgvector
backend (the docker-compose `mem0-postgres` service). Run with `uv`:

    uv run scripts/mem0_roundtrip.py

Design choices that keep this dependency-light and key-free:
- Uses a LOCAL HuggingFace embedder (all-MiniLM-L6-v2, 384 dims) — no OpenAI key.
- Uses `infer=False` on add() so no LLM fact-extraction is needed — we are proving
  *persistence + retrieval through pgvector*, not the extraction pipeline.
- Vector store is pgvector at 127.0.0.1:5433 (vector_store / mem0 / mem0), matching
  hermes/mem0.json and docker-compose.yml (host port 5433 avoids a 5432 collision).

Exit 0 on a successful round-trip (the added fact is retrieved with a score),
non-zero otherwise — so it works as a CI / phase-gate assertion.
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

CONFIG = {
    # LLM is required at construction time even though we use infer=False (no LLM
    # call is actually made). Point it at the local Ollama endpoint so no external
    # API key is needed. Swap to openai by setting OPENAI_API_KEY + provider:openai.
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
            # Unique collection per run so re-runs don't depend on prior state.
            "collection_name": f"roundtrip_{uuid.uuid4().hex[:8]}",
            "embedding_model_dims": EMBED_DIMS,
        },
    },
}

FACT = "The orchestrator coordinates specialists over a single-host Kanban board."
QUERY = "How do agents coordinate?"
USER_ID = "sovereign-cto-roundtrip"


def main() -> int:
    mem = Memory.from_config(CONFIG)

    print(f"[add]    user_id={USER_ID!r} fact={FACT!r}")
    add_res = mem.add(FACT, user_id=USER_ID, infer=False)
    results = add_res.get("results", add_res) if isinstance(add_res, dict) else add_res
    if not results:
        print("FAIL: add() stored nothing.", file=sys.stderr)
        return 1
    print(f"[add]    stored {len(results)} memory row(s).")

    print(f"[search] query={QUERY!r}")
    search_res = mem.search(QUERY, filters={"user_id": USER_ID})
    hits = (
        search_res.get("results", search_res)
        if isinstance(search_res, dict)
        else search_res
    )
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

    print("PASS: mem0 round-trip succeeded (fact persisted to pgvector and retrieved with a score).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
