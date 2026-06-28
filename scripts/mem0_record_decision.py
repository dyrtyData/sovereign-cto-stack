#!/usr/bin/env python3
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
"""mem0_record_decision.py — close the mem0 write path (GLO-14 P1).

The load-bearing GLO-14 slice. The two agent loops (`record_run.sh` hero +
`pmf_kanban_run.sh`) already GROUND themselves via `query_cto_knowledge` and
*read* prior decisions, but nothing ever *wrote* a new decision back into the
unified `memories` collection — so mem0 never accumulated run-over-run. This
helper inserts the deterministic "record this decision" write at the single
canonical position research pins in BOTH loops: AFTER `save_issue` returns a
ticket id and BEFORE `snapshot_after_run.sh` runs.

Design decisions carried (docs/system-design-tradeoffs.md "GLO-14 P2"):
  - Q2: write the unified `memories` collection (`user_id="sovereign-cto"`), the
    same collection the PMF consult now READS — so recall is real, not theater.
  - Q3: a DETERMINISTIC Python helper is load-bearing. Passive capture is
    unavailable for our architecture (inference routes through the Nous Portal,
    not mem0's proxy), so an explicit `add()` is the only guaranteed mechanism.
  - Q4: use mem0's intended `infer=True` extraction so the LLM pulls salient
    facts, dedups, resolves conflicts, and (>= v2.0.0) entity-links natively —
    this is "use mem0 the way it's designed." Git stays the deterministic record;
    mem0 is the recall complement.

Self-skip philosophy (mirrors `mem0_roundtrip.py`): `infer=True` needs the local
Ollama fact-extractor. When Ollama is unreachable we DEGRADE to `infer=False`
(the raw turn is still persisted, so the `memories` collection still accumulates
and the gate stays green) and log the downgrade — exactly like the round-trip's
self-skipping entity-link proof. The write NEVER silently no-ops: a row always
lands, tagged `source:"agent_run"` + `decision_id` for the accumulation gate.

spaCy lemmatization (GLO-14 P2 add-on): the `mem0ai[nlp]` extra pulls spaCy so
mem0's v2.0.0 hybrid LEXICAL index (`gin to_tsvector(... text_lemmatized)`) uses
real lemmas instead of falling back to a simpler tokenizer. The `en_core_web_sm`
model is loaded lazily by mem0; if it is missing we attempt a one-time download
and otherwise degrade with a logged note (we never let a missing model hard-fail
the write — same Ollama-style self-skip philosophy).

Usage (library):
    from mem0_record_decision import record_decision
    record_decision(profile="cto-architecture", run_id="run_<ts>",
                    ticket_id="GLO-NN", kind="brownfield_decision",
                    grounding_question="...", grounded_summary="...",
                    grounded_in=["building-microservices.md"])

Usage (CLI — used by the loops):
    uv run scripts/mem0_record_decision.py \
        --profile cto-architecture --run-id run_<ts> --ticket-id GLO-NN \
        --kind brownfield_decision \
        --grounding-question "..." --ticket-title "[Brownfield] ..." \
        --grounded-summary "..." --grounded-in building-microservices.md \
        --grounded-in software-architecture.md

Emits a one-line JSON receipt on stdout: {"recorded":true,"decision_id":"GLO-NN",
"collection":"memories","infer":true,"rows":N}. Exit 0 on a successful write,
non-zero only on a hard backend failure (a dead pgvector is a real error).
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys

# Make spaCy / mem0's lemma loader chatty enough that the "spaCy lemma model
# loaded" (or the degraded warning) is visible in the run logs — the GLO-14 P2
# add-on asks us to verify the "Failed to load spaCy lemma model" warning is gone.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PG_HOST = os.environ.get("MEM0_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("MEM0_PG_PORT", "5433"))
PG_USER = os.environ.get("MEM0_PG_USER", "mem0")
PG_PASSWORD = os.environ.get("MEM0_PG_PASSWORD", "mem0")
PG_DBNAME = os.environ.get("MEM0_PG_DBNAME", "vector_store")
EMBED_DIMS = 384  # all-MiniLM-L6-v2

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("MEM0_OLLAMA_MODEL", "qwen2.5-coder:14b")

# The UNIFIED collection (design Q2). Both this writer and the repointed PMF
# consult READ/WRITE this single collection, with a stable user_id so recall is
# real. Overridable for the gate's isolated runs.
COLLECTION = os.environ.get("MEM0_MEMORIES_COLLECTION", "memories")
USER_ID = os.environ.get("MEM0_MEMORIES_USER", "sovereign-cto")


def _config() -> dict:
    return {
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


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _results(res):
    if isinstance(res, dict):
        return res.get("results", [])
    return res or []


def _ollama_reachable() -> bool:
    """Cheap probe: is the local Ollama fact-extractor up? (no LLM call yet)."""
    try:
        import urllib.request

        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=2) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def _warm_spacy_lemma() -> bool:
    """Proactively load (and, if needed, download) mem0's spaCy lemma model.

    mem0 OSS >= v2.0.0 builds a hybrid LEXICAL index on `text_lemmatized`; the
    lemmatizer wants spaCy's `en_core_web_sm`. Calling mem0's own loader here
    surfaces the "spaCy lemma model loaded" log (or the degraded warning) BEFORE
    the write, and triggers the one-time `en_core_web_sm` download if the model
    is absent. We never hard-fail on a missing model — we degrade and log, the
    same self-skip philosophy as the Ollama path.

    Returns True if a real spaCy lemma model is loaded, False if we degraded.
    """
    try:
        from mem0.utils.spacy_models import get_nlp_lemma
    except Exception as e:  # mem0 too old / nlp extra missing
        logging.getLogger("mem0_record_decision").warning(
            "spaCy lemma loader unavailable (%s) — mem0 will fall back to its "
            "simple tokenizer for the lexical index (recall slightly reduced, "
            "write still proceeds).", e,
        )
        return False
    try:
        nlp = get_nlp_lemma()
    except Exception as e:
        logging.getLogger("mem0_record_decision").warning(
            "spaCy lemma model could not be loaded/downloaded (%s) — degrading "
            "to mem0's simple tokenizer (write still proceeds).", e,
        )
        return False
    if nlp is None:
        logging.getLogger("mem0_record_decision").warning(
            "spaCy lemma model is None — degrading to mem0's simple tokenizer "
            "(write still proceeds; install model: python -m spacy download "
            "en_core_web_sm)."
        )
        return False
    logging.getLogger("mem0_record_decision").info(
        "spaCy lemma model ready — mem0's hybrid lexical index uses real lemmas."
    )
    return True


def record_decision(
    *,
    profile: str,
    run_id: str,
    ticket_id: str,
    kind: str,
    grounding_question: str,
    grounded_summary: str,
    ticket_title: str = "",
    grounded_in: list[str] | None = None,
) -> dict:
    """Write the just-filed decision into the unified `memories` collection.

    Feeds mem0 the FULL agent turn (the grounding question as the user turn, the
    filed ticket title + grounded summary as the assistant turn) and lets mem0
    extract/dedup/entity-link it via `infer=True` (degrading to `infer=False`
    when Ollama is down). Tags `metadata.decision_id` + `source:"agent_run"` so
    `assert_memory_accumulates.py` can prove the count grew and recall surfaces
    THIS run's decision id.

    Returns a receipt dict (also printed by the CLI).
    """
    from mem0 import Memory

    grounded_in = grounded_in or []
    # Warm spaCy's lemmatizer first so the lexical-index path uses real lemmas
    # (and the "Failed to load spaCy lemma model" warning is cleared when the
    # model is present). Non-fatal.
    spacy_ok = _warm_spacy_lemma()

    mem = Memory.from_config(_config())

    assistant_content = grounded_summary
    if ticket_title:
        assistant_content = f"{ticket_title}\n{grounded_summary}"

    messages = [
        {"role": "user", "content": grounding_question},
        {"role": "assistant", "content": assistant_content},
    ]
    metadata = {
        "decision_id": ticket_id,
        "kind": kind,
        "ticket_id": ticket_id,
        "grounded_in": grounded_in,
        "source": "agent_run",
        "profile": profile,
        "run_id": run_id,
        "ts": _now_iso(),
    }

    use_infer = _ollama_reachable()
    log = logging.getLogger("mem0_record_decision")
    if use_infer:
        log.info(
            "infer=True (mem0's intended extraction/dedup/entity-linking) — "
            "Ollama reachable at %s.", OLLAMA_BASE_URL,
        )
    else:
        log.warning(
            "Ollama unreachable at %s — degrading to infer=False so the raw "
            "decision turn is still persisted (the memories collection still "
            "accumulates; recall extraction is skipped this run).",
            OLLAMA_BASE_URL,
        )

    # mem0 entity ids (user_id/agent_id/run_id) are first-class kwargs.
    add_res = mem.add(
        messages,
        user_id=USER_ID,
        agent_id=profile,
        run_id=run_id,
        infer=use_infer,
        metadata=metadata,
    )
    rows = _results(add_res)

    receipt = {
        "recorded": bool(rows),
        "decision_id": ticket_id,
        "collection": COLLECTION,
        "user_id": USER_ID,
        "infer": use_infer,
        "spacy_lemma": spacy_ok,
        "rows": len(rows),
    }
    return receipt


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", required=True, help="Hermes profile / agent_id")
    ap.add_argument("--run-id", required=True, help="this run's id (run_<ts>)")
    ap.add_argument("--ticket-id", required=True, help="filed ticket id (GLO-NN) == decision_id")
    ap.add_argument("--kind", default="agent_decision",
                    help="decision kind (e.g. brownfield_decision, product_decision)")
    ap.add_argument("--grounding-question", required=True,
                    help="the user-turn grounding question driving the decision")
    ap.add_argument("--ticket-title", default="", help="the filed ticket title (assistant turn)")
    ap.add_argument("--grounded-summary", required=True,
                    help="the assistant-turn decision summary (the WHY)")
    ap.add_argument("--grounded-in", action="append", default=[],
                    help="a cited corpus source_file (repeatable)")
    args = ap.parse_args(argv)

    try:
        receipt = record_decision(
            profile=args.profile,
            run_id=args.run_id,
            ticket_id=args.ticket_id,
            kind=args.kind,
            grounding_question=args.grounding_question,
            grounded_summary=args.grounded_summary,
            ticket_title=args.ticket_title,
            grounded_in=args.grounded_in,
        )
    except Exception as e:
        print(f"FAIL: mem0 decision write failed (backend error): {e}", file=sys.stderr)
        return 1

    print(json.dumps(receipt))
    if not receipt["recorded"]:
        # infer=True can legitimately extract zero NEW facts if the turn dedups
        # against an existing memory — but with infer=False a row must land. Only
        # treat a no-row infer=False write as a hard failure.
        if not receipt["infer"]:
            print("FAIL: infer=False write stored no rows (pgvector not persisting).",
                  file=sys.stderr)
            return 1
        print("NOTE: infer=True extracted no NEW rows this turn (likely deduped "
              "against an existing memory) — not a failure.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
