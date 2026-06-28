#!/usr/bin/env python3
"""assert_microvm_spike.py — the GLO-14 P4 MicroVM-spike gate (TOLERANT, design Q9 Option A).

This is the falsifiable exit-0 contract for the host-orchestrator MicroVM confinement
SPIKE. Acceptance criterion #4 is "scoped OR built" — so the load-bearing thing this gate
proves is that the spike was genuinely RUN and DOCUMENTED, not that a VM booted. A spike
that honestly records "the vm driver did not boot on this host" is a PASS; the deliverable
is the captured evidence + the dated go/no-go, per Q9.

Two ALWAYS-checked invariants (the spike was run + the decision was recorded):
  1. a spike log exists at recordings/microvm_spike_*.log (the scripted ATTEMPT ran and
     captured evidence — VM_DRIVER_PRESENT / VM_DRIVER_BOOTED markers present); and
  2. docs/system-design-tradeoffs.md carries a DATED go/no-go section for the spike
     (a "go/no-go" line + an ISO date + all four documented macOS limitations named).

Then, the per-bug behaviour matching — but TOLERANT. The structure outline asks: *when the
VM reaches boot*, also run deterministic per-bug probes and assert each behaves as
documented; each probe SELF-SKIPS (logged SKIP, still exit 0) if the VM did not get far
enough. So:
  - .local mDNS non-traversal  — a CONNECT to a host .local mDNS name from INSIDE the guest
    must FAIL (the guest cannot resolve host mDNS). Requires an in-guest shell.
  - Landlock best_effort no-op  — the guest reports Landlock running best_effort / degraded
    (it is a Linux LSM that no-ops on the XNU host kernel). Requires an in-guest shell.
  - virtio-fs case-sensitivity  — a case-collision check over a shared virtio-fs mount
    resolves as the doc records. Requires a shared mount in a booted guest.

A "reached boot" here means the spike actually ran an IN-GUEST workload we can probe. The
spike (microvm_spike.sh) deliberately stops at proving the vm DRIVER layer binds (Q9 defers
the fragile full-guest reconfigure), so on this host these three probes SKIP — which is the
documented, graceful-degradation path. If a future spike DOES run an in-guest workload and
emits the probe markers, this gate asserts each matches the doc.

Exit 0 on PASS (incl. all-probes-SKIP), 1 only if an ALWAYS-checked invariant is missing or
a REACHED probe contradicts the documented behaviour. Never 2 — a spike has no "harness
error": absent tooling is itself a recorded outcome.

Usage:
  uv run scripts/assert_microvm_spike.py
  MICROVM_SPIKE_LOG=recordings/microvm_spike_20260628_175000.log \
    uv run scripts/assert_microvm_spike.py     # pin a specific log
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RECORDINGS = REPO_ROOT / "recordings"
TRADEOFFS = REPO_ROOT / "docs" / "system-design-tradeoffs.md"

# The four macOS limitations the doc MUST name (substring match, case-insensitive). These
# are the spike's whole point — a go/no-go that doesn't name them is not grounded.
REQUIRED_LIMITATIONS = {
    "Landlock best_effort no-op on XNU": ("landlock", "best_effort"),
    "mDNS .local non-traversal": (".local",),
    "no CUDA on Apple Silicon": ("cuda",),
    "case-sensitive-APFS virtio-fs": ("virtio-fs", "case"),
}


def _find_spike_log() -> Path | None:
    pinned = os.environ.get("MICROVM_SPIKE_LOG")
    if pinned:
        p = Path(pinned)
        return p if p.is_absolute() else (REPO_ROOT / pinned)
    candidates = sorted(RECORDINGS.glob("microvm_spike_*.log"))
    return candidates[-1] if candidates else None


def _marker(text: str, key: str) -> str | None:
    """Return the value of a `KEY=value` marker line, or None."""
    m = re.search(rf"^{re.escape(key)}=(\S+)\s*$", text, re.MULTILINE)
    return m.group(1) if m else None


def _check_log(log: Path) -> tuple[bool, str, str]:
    """Validate the spike log. Returns (ok, vm_present, vm_booted)."""
    text = log.read_text(encoding="utf-8", errors="replace")
    ok = True

    if "host-orchestrator MicroVM confinement SPIKE" not in text:
        print(f"FAIL - {log.name} does not look like a microvm spike log "
              "(missing the spike banner)")
        ok = False

    present = _marker(text, "VM_DRIVER_PRESENT")
    booted = _marker(text, "VM_DRIVER_BOOTED")
    if present is None:
        print("FAIL - spike log missing the VM_DRIVER_PRESENT marker")
        ok = False
    if booted is None:
        print("FAIL - spike log missing the VM_DRIVER_BOOTED marker")
        ok = False

    if ok:
        print(f"PASS - spike evidence present: {log.relative_to(REPO_ROOT)}")
        print(f"       VM_DRIVER_PRESENT={present}  VM_DRIVER_BOOTED={booted}")
    return ok, (present or "no"), (booted or "no")


def _check_tradeoffs() -> bool:
    """Assert the tradeoffs doc carries a DATED go/no-go section naming all 4 limitations."""
    if not TRADEOFFS.is_file():
        print(f"FAIL - tradeoffs doc missing: {TRADEOFFS}")
        return False
    text = TRADEOFFS.read_text(encoding="utf-8", errors="replace")
    low = text.lower()
    ok = True

    # A go/no-go decision must be present and dated. We scope the date check to the
    # neighbourhood of a go/no-go mention so a stray date elsewhere can't satisfy it.
    gng = re.search(r"go\s*/?\s*no[\s-]*go", low)
    if not gng:
        print("FAIL - tradeoffs doc has no go/no-go decision for the MicroVM spike")
        ok = False
    else:
        window = text[max(0, gng.start() - 1500): gng.end() + 1500]
        if re.search(r"\b20\d{2}-\d{2}-\d{2}\b", window):
            print("PASS - tradeoffs doc carries a DATED go/no-go section for the spike")
        else:
            print("FAIL - the go/no-go section carries no ISO date (must be dated)")
            ok = False

    missing = [name for name, needles in REQUIRED_LIMITATIONS.items()
               if not all(n.lower() in low for n in needles)]
    if missing:
        print("FAIL - tradeoffs doc does not document all four macOS limitations; "
              f"missing: {missing}")
        ok = False
    else:
        print("PASS - all four documented macOS limitations named in the tradeoffs doc")
    return ok


def _probe(name: str, reached: bool, log_text: str, marker: str,
           expect: str) -> bool:
    """Run one per-bug probe, TOLERANT.

    `reached` = did the spike run an in-guest workload we can probe? If not -> SKIP.
    If reached, look for `<marker>=<value>` in the log and assert it `expect`s.
    Returns True (PASS or SKIP) / False only on a REACHED contradiction.
    """
    if not reached:
        print(f"SKIP - probe [{name}]: VM did not reach an in-guest workload on this host "
              "(the spike proved the driver layer binds, then stopped per Q9) — "
              "documented graceful degradation.")
        return True
    val = _marker(log_text, marker)
    if val is None:
        print(f"SKIP - probe [{name}]: in-guest marker {marker} not emitted "
              "(workload did not reach this probe).")
        return True
    if val.lower() == expect.lower():
        print(f"PASS - probe [{name}]: observed {marker}={val} (matches documented behaviour).")
        return True
    print(f"FAIL - probe [{name}]: observed {marker}={val}, expected {expect} "
          "(reached the probe but behaviour did NOT match the doc).")
    return False


def main() -> int:
    print("=== GLO-14 P4 — MicroVM spike gate (tolerant; Q9 Option A) ===")

    log = _find_spike_log()
    if log is None or not log.is_file():
        print("FAIL - no spike log found (recordings/microvm_spike_*.log). "
              "Run: bash scripts/microvm_spike.sh")
        print("RESULT: FAIL")
        return 1

    log_ok, _present, booted = _check_log(log)
    doc_ok = _check_tradeoffs()
    log_text = log.read_text(encoding="utf-8", errors="replace")

    # "Reached boot" for the per-bug probes means the spike ran an IN-GUEST workload we can
    # inspect. The current spike stops at the driver-binds layer (booted == "yes" but no
    # in-guest workload), so the probes SKIP. A future fuller spike would emit the in-guest
    # markers (PROBE_MDNS / PROBE_LANDLOCK / PROBE_VIRTIOFS) and flip `reached` true.
    in_guest_ran = _marker(log_text, "VM_GUEST_WORKLOAD") == "yes"
    reached = (booted.lower() == "yes") and in_guest_ran
    if booted.lower() == "yes" and not in_guest_ran:
        print("NOTE - the vm driver BOOTED (bound its gRPC socket) but the spike did not "
              "run an in-guest workload (Q9 defers the fragile full-guest reconfigure); "
              "the three per-bug probes therefore SKIP, as designed.")

    probes_ok = True
    probes_ok &= _probe(".local mDNS non-traversal", reached, log_text,
                        "PROBE_MDNS", "fail")        # CONNECT to host .local must FAIL
    probes_ok &= _probe("Landlock best_effort no-op", reached, log_text,
                        "PROBE_LANDLOCK", "best_effort")
    probes_ok &= _probe("virtio-fs case-sensitivity", reached, log_text,
                        "PROBE_VIRTIOFS", "case_sensitive")

    ok = log_ok and doc_ok and probes_ok
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
