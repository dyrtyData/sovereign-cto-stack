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
"""assert_memory_view_grows.py — the GLO-14 P3 / D-2 memory-view gate (exit-0-on-pass).

The read-only memory card (`render_memory_card.py`) is the DEMO surface that
"visibly shows more rows" after a run. This gate SCRIPTS that visual claim so it
is falsifiable, not eyeballed:

  1. render the memory card with `--baseline` (the BEFORE snapshot of the
     collection's row ids + count, written to a JSON the card emits);
  2. run a loop (the deterministic `mem0_record_decision.record_decision` writer —
     the same write path the agent loops use, so this exercises the real wiring);
  3. render the memory card again `--against` that baseline (the AFTER view) and
     assert the parsed AFTER row count STRICTLY GREW vs. the BEFORE count, AND that
     the AFTER card actually highlights the new row(s) (`new_rows > 0`).

Runs against an ISOLATED, ephemeral collection (a fresh `memview_<uuid>` namespace
via the MEM0_MEMORIES_COLLECTION / _USER overrides the writer + card honor) so it is
deterministic and never pollutes the live `memories` collection — same isolation
philosophy as `assert_memory_accumulates.py`. The writer self-skips to `infer=False`
when Ollama is down, so this gate stays green in CI without a local LLM.

Exit 0 on PASS, 1 on assertion FAIL, 2 on harness error (dead pgvector — NEVER a
silent pass).

Usage:
    docker compose up -d mem0-postgres
    uv run scripts/assert_memory_view_grows.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Isolate this gate into a throwaway collection/user (mirrors
# assert_memory_accumulates.py) so it never collides with or pollutes the live
# `memories` collection. The writer AND the card read these same env vars.
_NS = uuid.uuid4().hex[:8]
os.environ["MEM0_MEMORIES_COLLECTION"] = f"memview_{_NS}"
os.environ["MEM0_MEMORIES_USER"] = f"sovereign-cto-memview-{_NS}"

import mem0_record_decision as W  # noqa: E402  (after env override)
import render_memory_card as V  # noqa: E402


RUN = {
    "profile": "cto-architecture",
    "run_id": f"memview-run-{_NS}",
    "ticket_id": f"GLO-MEMVIEW-{_NS}",
    "kind": "brownfield_decision",
    "grounding_question": "Which surface should the read-only memory view prove grew this run?",
    "ticket_title": "[Brownfield] Memory-view growth witness",
    "grounded_summary": (
        f"MEMVIEW-WITNESS-{_NS}: the deterministic write path appends this decision "
        "to the unified memories collection so the read-only card shows one more row."
    ),
    "grounded_in": ["building-microservices.md"],
}


def _render(out: Path, *, baseline: Path | None = None, against: Path | None = None) -> dict:
    argv: list[str] = ["--out", str(out)]
    if baseline:
        argv += ["--baseline", str(baseline)]
    if against:
        argv += ["--against", str(against)]
    # render_memory_card.main prints a one-line JSON receipt; capture it.
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = V.main(argv)
    line = (buf.getvalue().strip().splitlines() or ["{}"])[-1]
    try:
        receipt = json.loads(line)
    except Exception:  # noqa: BLE001
        receipt = {}
    receipt["_rc"] = rc
    return receipt


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="memview_gate_"))
    baseline_json = work / "before.json"
    before_html = work / "memory_before.html"
    after_html = work / "memory_after.html"

    # --- BEFORE: snapshot the (empty, isolated) collection --------------------
    print(f"[gate]  isolated collection={os.environ['MEM0_MEMORIES_COLLECTION']!r}")
    print("--- before: render the memory card + write the baseline ---")
    before = _render(before_html, baseline=baseline_json)
    if before.get("unreachable"):
        print("HARNESS ERROR: mem0 pgvector backend unreachable — bring it up: "
              "docker compose up -d mem0-postgres", file=sys.stderr)
        return 2
    if not before_html.is_file() or before_html.stat().st_size == 0:
        print("HARNESS ERROR: before-card not written (render failed).", file=sys.stderr)
        return 2
    before_count = int(before.get("rows", -1))
    print(f"[before] rows={before_count}  card={before_html.name} "
          f"({before_html.stat().st_size} bytes)")

    # --- LOOP: the deterministic write path appends one decision --------------
    print("--- loop: record one decision via the real write path ---")
    try:
        receipt = W.record_decision(**RUN)
    except Exception as e:  # noqa: BLE001
        print(f"HARNESS ERROR: writer failed ({e}).", file=sys.stderr)
        return 2
    print(f"[loop]   receipt={receipt}")
    time.sleep(1)  # let the insert commit before we re-read

    # --- AFTER: render against the baseline -----------------------------------
    print("--- after: render the memory card against the baseline ---")
    after = _render(after_html, against=baseline_json)
    if not after_html.is_file() or after_html.stat().st_size == 0:
        print("HARNESS ERROR: after-card not written (render failed).", file=sys.stderr)
        return 2
    after_count = int(after.get("rows", -1))
    new_rows = int(after.get("new_rows", 0))
    print(f"[after]  rows={after_count}  new_rows={new_rows}  card={after_html.name} "
          f"({after_html.stat().st_size} bytes)")

    ok = True
    if after_count > before_count:
        print(f"PASS: the memory view grew {before_count} -> {after_count} rows "
              "(visibly more rows after the loop)")
    else:
        print(f"FAIL: the memory view did NOT grow ({before_count} -> {after_count})")
        ok = False

    if new_rows > 0:
        print(f"PASS: the after-card highlights {new_rows} NEW row(s) since the baseline")
    else:
        print("FAIL: the after-card highlighted no NEW rows (the diff did not register)")
        ok = False

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
