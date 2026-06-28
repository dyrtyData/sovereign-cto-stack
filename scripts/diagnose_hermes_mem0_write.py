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
"""diagnose_hermes_mem0_write.py — Q3 bonus probe (NON-GATING diagnostic).

Design Q3 settled that a deterministic Python helper (mem0_record_decision.py) is
the LOAD-BEARING write path, because passive capture is unavailable for our
architecture (inference routes through the Nous Portal, not mem0's proxy). It also
left ONE empirical question to answer during implementation rather than as an open
question: **does the closed-source `hermes-agent` binary write into the `memories`
collection on its own**, via the `hermes/mem0.json` config it loads, when a loop
runs WITHOUT our deterministic helper?

This script answers it empirically and prints a machine-readable verdict. It is a
DIAGNOSTIC, never a pass/fail gate — the deterministic helper stays load-bearing
regardless of the result. It:

  1. snapshots the row count of the live `memories` collection (Hermes' own
     collection, user_id "sovereign-cto");
  2. runs ONE short hero loop with MEM0_RECORD_DECISION_DISABLE=1 (so OUR write is
     skipped and any new rows can only have come from the Hermes binary itself);
  3. re-counts and reports the delta and a verdict.

Verdicts (printed as a one-line JSON object, always exit 0):
  - NATIVE_WRITE_OBSERVED : new rows appeared with the helper disabled -> the binary
    writes mem0 on its own (a bonus; our helper is still the guaranteed mechanism).
  - NO_NATIVE_WRITE       : the loop ran but produced no new rows -> the binary does
    NOT write `memories` on its own; the deterministic helper is REQUIRED (confirms Q3).
  - INCONCLUSIVE          : the loop could not be run far enough (no hermes binary,
    no graphify input, run errored/timed out, or the backend was unreachable) to
    decide — the deterministic helper remains load-bearing either way.

Usage:
    docker compose up -d mem0-postgres
    uv run scripts/diagnose_hermes_mem0_write.py
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent

# The LIVE collection the Hermes binary is configured to use (hermes/mem0.json).
PG = {
    "host": os.environ.get("MEM0_PG_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MEM0_PG_PORT", "5433")),
    "user": os.environ.get("MEM0_PG_USER", "mem0"),
    "password": os.environ.get("MEM0_PG_PASSWORD", "mem0"),
    "dbname": os.environ.get("MEM0_PG_DBNAME", "vector_store"),
}
COLLECTION = os.environ.get("MEM0_MEMORIES_COLLECTION", "memories")
USER_ID = os.environ.get("MEM0_MEMORIES_USER", "sovereign-cto")
EMBED_DIMS = 384
HERO_TIMEOUT = int(os.environ.get("DIAG_HERO_TIMEOUT", "150"))


def _verdict(verdict: str, **extra) -> int:
    print(json.dumps({"verdict": verdict, "collection": COLLECTION,
                      "user_id": USER_ID, **extra}))
    return 0


def _count() -> int | None:
    """Count rows for USER_ID in the live `memories` collection (None on error)."""
    try:
        from mem0 import Memory
    except Exception:
        return None
    cfg = {
        "llm": {"provider": "ollama",
                "config": {"model": os.environ.get("MEM0_OLLAMA_MODEL", "qwen2.5-coder:14b"),
                           "ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")}},
        "embedder": {"provider": "huggingface",
                     "config": {"model": "sentence-transformers/all-MiniLM-L6-v2"}},
        "vector_store": {"provider": "pgvector",
                         "config": {**PG, "collection_name": COLLECTION,
                                    "embedding_model_dims": EMBED_DIMS}},
    }
    try:
        mem = Memory.from_config(cfg)
        res = mem.get_all(filters={"user_id": USER_ID}, top_k=500)
        rows = res.get("results", []) if isinstance(res, dict) else (res or [])
        return len(rows)
    except Exception as e:
        logging.getLogger("diagnose").warning("count failed: %s", e)
        return None


def main() -> int:
    # Bring the backend up (best-effort) and snapshot the baseline count.
    subprocess.run(["docker", "compose", "up", "-d", "mem0-postgres"],
                   cwd=str(REPO_ROOT), capture_output=True)
    before = _count()
    if before is None:
        return _verdict("INCONCLUSIVE",
                        reason="mem0 pgvector backend unreachable (docker compose up -d mem0-postgres)")
    print(f"[diag] baseline `{COLLECTION}` rows for {USER_ID!r}: {before}", file=sys.stderr)

    # Prerequisites for a real hero loop run with the binary in charge.
    hermes = os.environ.get("HERMES", "hermes")
    if shutil.which(hermes) is None:
        return _verdict("INCONCLUSIVE", reason="hermes binary not on PATH",
                        baseline_rows=before)
    if not (REPO_ROOT / "graphify-out" / "service-graph.html").is_file():
        return _verdict("INCONCLUSIVE",
                        reason="graphify-out/service-graph.html missing — run scripts/run_graphify.sh first",
                        baseline_rows=before)

    # Run ONE hero loop with OUR deterministic write DISABLED, so any new `memories`
    # rows are attributable ONLY to the Hermes binary's own mem0.json behaviour.
    env = dict(os.environ)
    env["MEM0_RECORD_DECISION_DISABLE"] = "1"
    env["RECORD_SECONDS"] = str(HERO_TIMEOUT)
    print("[diag] running ONE hero loop with the deterministic helper DISABLED "
          "(probe: does hermes-agent write `memories` natively?)", file=sys.stderr)
    try:
        proc = subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / "record_run.sh"), "hero"],
            cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
            timeout=HERO_TIMEOUT + 120,
        )
        ran = True
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        ran = False
        rc = None
    except Exception as e:
        return _verdict("INCONCLUSIVE", reason=f"loop launch failed: {e}",
                        baseline_rows=before)

    time.sleep(2)
    after = _count()
    if after is None:
        return _verdict("INCONCLUSIVE", reason="post-run count failed",
                        baseline_rows=before)
    delta = after - before
    print(f"[diag] post-run `{COLLECTION}` rows: {after} (delta {delta:+d}), "
          f"loop ran={ran} rc={rc}", file=sys.stderr)

    if delta > 0:
        return _verdict("NATIVE_WRITE_OBSERVED", baseline_rows=before,
                        post_rows=after, delta=delta, loop_ran=ran, loop_rc=rc,
                        note=("hermes-agent appears to write `memories` on its own via "
                              "mem0.json; the deterministic helper remains load-bearing "
                              "(guaranteed every run)."))
    if ran and rc is not None:
        return _verdict("NO_NATIVE_WRITE", baseline_rows=before, post_rows=after,
                        delta=delta, loop_ran=ran, loop_rc=rc,
                        note=("the loop ran with our helper disabled and `memories` did "
                              "NOT grow — the binary does not write mem0 natively; the "
                              "deterministic helper is REQUIRED (confirms design Q3)."))
    return _verdict("INCONCLUSIVE", baseline_rows=before, post_rows=after,
                    delta=delta, loop_ran=ran, loop_rc=rc,
                    reason="loop did not complete far enough to decide")


if __name__ == "__main__":
    raise SystemExit(main())
