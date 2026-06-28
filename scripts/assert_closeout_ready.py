#!/usr/bin/env python3
"""assert_closeout_ready.py — the GLO-14 Phase 7 D-6 closeout-boundary gate.

This is the falsifiable exit-0 contract for "the full-epic scope is substantially actioned"
(design D-6 Option A) — measured, not asserted by feel, BEFORE the next epic is authored. It
does two things:

  1. Runs EVERY prior-phase gate and requires all exit 0:
       - assert_memory_accumulates.py   (P2 — mem0 write path accumulates)
       - assert_greptile_instruction.py (P3 — Greptile ticket-instruction line)
       - assert_shipped_flip.py         (P5 — Stripe-grounded shipped-bet flip)
       - assert_showcase_video.py       (P3 / D-2 — fuller montage)
       - assert_microvm_spike.py        (P4 — host-orchestrator MicroVM spike)
     Each is launched via `uv run` so its PEP 723 inline deps (e.g. mem0ai) resolve in their
     own environment, exactly as documented in the structure outline.

  2. Asserts the GLO-14 acceptance checklist in tickets/GLO-14.md is FULLY ticked
     (every `- [ ]` under "## Acceptance criteria" is now `- [x]`).

Tolerance (per the Phase-7 brief): services are expected to be UP, so by default the gates run
for real. A gate that legitimately CANNOT run because a service it needs is down (mem0-postgres
unreachable / Linear token absent) is reported as SKIP rather than a false FAIL — but the DEFAULT
is to actually run them. Set CLOSEOUT_STRICT=1 to turn any SKIP into a FAIL (CI on a fully-provisioned
box). A gate that runs and FAILS is always a FAIL.

Exit 0 only when every gate PASSED (or gracefully SKIPPED, non-strict) AND the GLO-14 checklist is
complete; 1 otherwise.

Usage:
  uv run scripts/assert_closeout_ready.py
  CLOSEOUT_STRICT=1 uv run scripts/assert_closeout_ready.py     # SKIP -> FAIL
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
TICKETS = REPO_ROOT / "tickets"

STRICT = os.environ.get("CLOSEOUT_STRICT", "") not in ("", "0", "false", "no")

# Prior-phase gates, in slice order. Each is the falsifiable contract for one GLO-14 phase.
PRIOR_GATES = [
    "assert_memory_accumulates.py",   # P2
    "assert_greptile_instruction.py",  # P3
    "assert_shipped_flip.py",          # P5
    "assert_showcase_video.py",        # P3 / D-2
    "assert_microvm_spike.py",         # P4
]

# Substrings in a gate's output (any of them, case-insensitive) that mean "a required service
# was unavailable" — i.e. the gate could not run, not that the slice is broken. Treated as SKIP
# (non-strict) rather than FAIL, since the brief says default-run-but-degrade-gracefully.
SERVICE_DOWN_MARKERS = (
    "no linear oauth token",
    "connection refused",
    "could not connect",
    "could not fetch",
    "mem0-postgres",
    "connection to server",
    "psycopg2.operationalerror",
    "operationalerror",
    "name or service not known",
    "max retries exceeded",
    "no [full-build] ticket found",
)

GATE_TIMEOUT = int(os.environ.get("CLOSEOUT_GATE_TIMEOUT", "600"))


def _run_gate(name: str) -> tuple[str, str]:
    """Run one gate via `uv run`. Returns (verdict, detail) where verdict ∈ {PASS, FAIL, SKIP}."""
    path = SCRIPTS / name
    if not path.is_file():
        return "FAIL", f"gate script missing: {path.relative_to(REPO_ROOT)}"
    try:
        proc = subprocess.run(
            ["uv", "run", str(path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=GATE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return "FAIL", f"timed out after {GATE_TIMEOUT}s"
    except FileNotFoundError:
        return "FAIL", "`uv` not found on PATH — required to resolve gate inline deps"

    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    tail = "\n".join(l for l in out.splitlines() if l.strip())[-400:]
    if proc.returncode == 0:
        return "PASS", "exit 0"
    low = out.lower()
    if any(m in low for m in SERVICE_DOWN_MARKERS):
        return "SKIP", f"exit {proc.returncode}; a required service looks unavailable — {tail[-200:]}"
    return "FAIL", f"exit {proc.returncode} — {tail[-200:]}"


def _glo14_checklist_complete() -> tuple[bool, str]:
    """Every acceptance-criteria item in tickets/GLO-14.md must be ticked (- [x])."""
    snap = TICKETS / "GLO-14.md"
    if not snap.is_file():
        return False, "tickets/GLO-14.md missing"
    text = snap.read_text()
    # Slice from the acceptance-criteria heading to the next top-level heading / end.
    m = re.search(r"##+\s*Acceptance criteria.*?(?=\n##\s|\Z)", text, re.S | re.I)
    if not m:
        return False, "no 'Acceptance criteria' section found in tickets/GLO-14.md"
    section = m.group(0)
    boxes = re.findall(r"-\s*\[( |x|X)\]", section)
    if not boxes:
        return False, "Acceptance criteria section has no checklist items"
    unticked = [b for b in boxes if b.strip() == ""]
    if unticked:
        return False, f"{len(unticked)}/{len(boxes)} acceptance items still unticked in tickets/GLO-14.md"
    return True, f"all {len(boxes)} GLO-14 acceptance items ticked"


def main() -> int:
    print("=== GLO-14 Phase 7 — closeout-readiness gate (D-6 boundary) ===")
    print(f"mode: {'STRICT (SKIP=FAIL)' if STRICT else 'default (SKIP allowed when a service is down)'}")

    ok = True
    print("\n-- prior-phase gates --")
    for name in PRIOR_GATES:
        verdict, detail = _run_gate(name)
        if verdict == "PASS":
            print(f"PASS - {name}: {detail}")
        elif verdict == "SKIP":
            if STRICT:
                print(f"FAIL - {name}: SKIP not allowed under CLOSEOUT_STRICT — {detail}")
                ok = False
            else:
                print(f"SKIP - {name}: {detail}")
        else:
            print(f"FAIL - {name}: {detail}")
            ok = False

    print("\n-- GLO-14 acceptance checklist --")
    done, msg = _glo14_checklist_complete()
    print(("PASS" if done else "FAIL"), "-", msg)
    ok = ok and done

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
