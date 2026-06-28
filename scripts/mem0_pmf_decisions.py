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
"""mem0_pmf_decisions.py — consult prior product decisions before ranking PMF bets.

Phase-5 enhancement: BEFORE the PMF loop ranks/recommends opportunities it MUST
consult prior decisions so it does not re-propose an already-decided/rejected idea
and can cite past rationale. There are two real, local sources of prior decisions:

  1. **mem0** (self-hosted on pgvector, the docker-compose `mem0-postgres` service,
     local HuggingFace embedder — same backend as scripts/mem0_roundtrip.py). We
     idempotently SEED the prior product decisions that already live in git as
     tracked `tickets/[Product]` snapshots, then semantically `search()` them for
     the current PMF question. No fabrication: if the decisions cannot be persisted
     and retrieved, we FAIL loudly (the caller treats that as a hard error).
  2. **git history** — `git log` over the tracked `tickets/` decision record (git
     is the authoritative CTO decision log per the repo's design). We surface the
     [Product] tickets and the commits that filed them as the WHY behind past calls.

This script emits a single JSON object on stdout that the PMF brief renders into a
"Prior decisions consulted" section:

    {
      "mem0": {"backend": "pgvector", "query": "...", "hits": [
          {"decision_id": "GLO-12", "memory": "...", "score": 0.83}, ...]},
      "git": {"product_tickets": [{"id":"GLO-12","title":"...","commit":"..."}],
              "log": ["<sha> <subject>", ...]}
    }

Exit 0 on a successful consult (mem0 round-trips AND git history is read),
non-zero on any hard failure (NO graceful degradation — a missing/dead mem0
backend is a FAIL, not a silent skip).

Usage:
    uv run scripts/mem0_pmf_decisions.py "<pmf question>"
    uv run scripts/mem0_pmf_decisions.py            # uses the default PMF question
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from mem0 import Memory

REPO_ROOT = Path(__file__).resolve().parent.parent
TICKETS_DIR = REPO_ROOT / "tickets"

PG_HOST = os.environ.get("MEM0_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("MEM0_PG_PORT", "5433"))
PG_USER = os.environ.get("MEM0_PG_USER", "mem0")
PG_PASSWORD = os.environ.get("MEM0_PG_PASSWORD", "mem0")
PG_DBNAME = os.environ.get("MEM0_PG_DBNAME", "vector_store")
EMBED_DIMS = 384  # all-MiniLM-L6-v2

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("MEM0_OLLAMA_MODEL", "qwen2.5-coder:14b")

# Stable collection so re-runs read the same persisted decision memory (idempotent
# seed below keeps it from growing unboundedly).
COLLECTION = os.environ.get("MEM0_PMF_COLLECTION", "pmf_decisions")
USER_ID = os.environ.get("MEM0_PMF_USER", "sovereign-cto-pmf")

CONFIG = {
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
            "collection_name": COLLECTION,
            "embedding_model_dims": EMBED_DIMS,
        },
    },
}

DEFAULT_QUESTION = (
    "Is there product-market fit for an autonomous AI tech-debt auditor for "
    "Series-A engineering teams?"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def _product_tickets() -> list[dict]:
    """Read prior [Product] decisions from the tracked tickets/ decision record."""
    out: list[dict] = []
    if not TICKETS_DIR.is_dir():
        return out
    for p in sorted(TICKETS_DIR.glob("GLO-*.md")):
        text = p.read_text(errors="ignore")
        first = text.splitlines()[0] if text.strip() else ""
        if "[Product]" not in first:
            continue
        ident = p.stem
        title = first.lstrip("# ").strip()
        # the gap statement is the heart of the decision
        gap = ""
        m = re.search(r"##\s*The gap[^\n]*\n+(.+?)(?:\n##|\Z)", text, re.S | re.I)
        if m:
            gap = " ".join(m.group(1).split())[:400]
        # which commit filed/snapshotted this ticket
        try:
            commit = _git("log", "-1", "--format=%h %s", "--", f"tickets/{ident}.md")
        except subprocess.CalledProcessError:
            commit = ""
        out.append({"id": ident, "title": title, "gap": gap, "commit": commit})
    return out


def _seed(mem: Memory, tickets: list[dict]) -> None:
    """Idempotently seed each prior [Product] decision into mem0.

    Idempotency: we tag every seeded memory with the ticket id in metadata and
    skip seeding a decision id that already round-trips. infer=False so no LLM
    fact-extraction is needed (we persist the decision verbatim).
    """
    for t in tickets:
        decision_id = t["id"]
        fact = (
            f"PRIOR PRODUCT DECISION {decision_id}: {t['title']}. "
            f"Capability gap already decided: {t['gap']}"
        )
        # has this decision already been seeded? (semantic + id-tagged check)
        existing = mem.search(decision_id, filters={"user_id": USER_ID})
        hits = existing.get("results", existing) if isinstance(existing, dict) else existing
        already = any(
            (h.get("metadata") or {}).get("decision_id") == decision_id for h in (hits or [])
        )
        if already:
            continue
        mem.add(
            fact,
            user_id=USER_ID,
            infer=False,
            metadata={"decision_id": decision_id, "kind": "product_decision"},
        )


def main() -> int:
    question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION

    tickets = _product_tickets()
    # git history snippet (authoritative decision log) — always available
    try:
        log_lines = _git(
            "log", "--oneline", "-i", "--grep", "product",
        ).splitlines()
    except subprocess.CalledProcessError:
        log_lines = []
    # also the tickets/ change log specifically
    try:
        tickets_log = _git(
            "log", "--oneline", "-5", "--", "tickets/",
        ).splitlines()
    except subprocess.CalledProcessError:
        tickets_log = []

    mem = Memory.from_config(CONFIG)
    _seed(mem, tickets)

    search_res = mem.search(question, filters={"user_id": USER_ID})
    raw_hits = (
        search_res.get("results", search_res) if isinstance(search_res, dict) else search_res
    )
    hits = []
    for h in (raw_hits or []):
        md = h.get("metadata") or {}
        hits.append({
            "decision_id": md.get("decision_id"),
            "memory": h.get("memory") or h.get("text") or "",
            "score": h.get("score"),
        })

    if not hits and tickets:
        # We seeded decisions but retrieval returned nothing — that is a real
        # backend failure, not "no prior decisions". FAIL loudly.
        print("FAIL: prior product decisions exist in tickets/ but mem0 search "
              "returned no hits — the pgvector backend is not persisting/retrieving.",
              file=sys.stderr)
        return 1

    result = {
        "mem0": {
            "backend": "pgvector",
            "collection": COLLECTION,
            "user_id": USER_ID,
            "query": question,
            "hits": hits,
        },
        "git": {
            "product_tickets": tickets,
            "log": log_lines[:10],
            "tickets_log": tickets_log,
        },
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
