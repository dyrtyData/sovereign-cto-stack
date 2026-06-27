#!/usr/bin/env python3
"""assert_egress_policy.py — prove deny-by-default egress is ENFORCED (Phase 2 / P1).

The headline "sovereign"/safety gate. Deny-by-default egress is only meaningful if
you can demonstrate a DENIAL, so this gate's LOAD-BEARING assertion is the NEGATIVE
test (design Q3-sub, Option β):

  NEGATIVE (load-bearing): a CONNECT to a host that is NOT on the egress/policy.yaml
    allow-list, made from INSIDE a real NVIDIA OpenShell sandbox confined by that
    policy, must be REFUSED. If that CONNECT succeeds, the gate FAILS — a sandbox
    that blocks nothing is not deny-by-default.

  POSITIVE: a CONNECT to an allow-listed host (api.linear.app:443) from inside the
    same sandbox must SUCCEED — proving the allow-list does not break legitimate
    egress (this is what lets the existing hero-loop gates keep reaching Linear).

The network OPA-CONNECT layer is independent of the Landlock filesystem layer, so
this assertion stays reliable even where Landlock `best_effort` silently degrades
on macOS (OpenShell #803 — docs/system-design-tradeoffs.md).

How it is enforced (NOT a mock proxy):
  OpenShell builds the egress/ Dockerfile, creates a `--no-keep` sandbox confined by
  egress/policy.yaml, and runs the curl probes INSIDE it. The sandbox supervisor
  (PID 1) auto-injects HTTPS_PROXY and routes every outbound TLS CONNECT through the
  gateway's OPA proxy (https://127.0.0.1:17670, a local launchd service). An
  allow-listed CONNECT is tunnelled (curl -> http 200); any other CONNECT is refused
  (`curl: (56) CONNECT tunnel failed, response 403`).

Detection: both probes run in ONE sandbox command and print machine-parseable
markers (`NEG_CODE=<http> NEG_EXIT=<n>` / `POS_CODE=<http> POS_EXIT=<n>`). The
negative target must report curl exit 56 (CONNECT tunnel failed / 403); the positive
target must report curl exit 0 and an HTTP 200.

Requires: `openshell` on PATH with a Connected gateway (`openshell status`) and a
running Docker daemon (OpenShell builds + runs the sandbox image through it). If
OpenShell is unavailable the gate exits 2 (harness error) rather than silently
passing — a deny-by-default claim that can't be exercised must not be reported PASS.

Exit 0 on PASS, 1 on FAIL, 2 on harness error.

Usage:
  python3 scripts/assert_egress_policy.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY = REPO_ROOT / "egress" / "policy.yaml"
EGRESS_DIR = REPO_ROOT / "egress"

# A host that MUST NOT be on the allow-list (the negative target). Picked to be a
# stable, unrelated public host; the assertion is about the REFUSAL, never a real
# connection to it.
DENY_HOST = os.environ.get("EGRESS_DENY_HOST", "example.com")
# An allow-listed host (the positive target) — must match egress/policy.yaml.
ALLOW_HOST = os.environ.get("EGRESS_ALLOW_HOST", "api.linear.app")

# OpenShell sandbox create can take a while on first build; allow a generous budget.
SANDBOX_TIMEOUT = int(os.environ.get("EGRESS_SANDBOX_TIMEOUT", "300"))

# The probe runs both CONNECTs inside the confined sandbox and prints parseable
# markers. curl exit 56 == "CONNECT tunnel failed" (the OPA 403 refusal).
PROBE = (
    'echo "=NEG=";'
    f' curl -sS -o /dev/null -w "NEG_CODE=%{{http_code}}" --max-time 20 https://{DENY_HOST} 2>/dev/null;'
    ' echo " NEG_EXIT=$?";'
    ' echo "=POS=";'
    f' curl -sS -o /dev/null -w "POS_CODE=%{{http_code}}" --max-time 20 https://{ALLOW_HOST} 2>/dev/null;'
    ' echo " POS_EXIT=$?"'
)


def _openshell_available() -> tuple[bool, str]:
    if shutil.which("openshell") is None:
        return False, "`openshell` not on PATH"
    status = subprocess.run(
        ["openshell", "status"], capture_output=True, text=True
    )
    if status.returncode != 0:
        return False, "`openshell status` failed (no gateway?)"
    if "Connected" not in status.stdout:
        return False, f"OpenShell gateway not Connected:\n{status.stdout.strip()}"
    return True, status.stdout.strip()


def _run_sandbox_probe() -> str:
    """Build + run the confined sandbox and return its combined stdout/stderr."""
    cmd = [
        "openshell", "sandbox", "create",
        "--no-keep",
        "--policy", str(POLICY),
        "--from", str(EGRESS_DIR),
        "--no-tty",
        "--", "sh", "-c", PROBE,
    ]
    print("egress gate: creating confined OpenShell sandbox "
          f"(--policy {POLICY.relative_to(REPO_ROOT)} --from egress/)...")
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=SANDBOX_TIMEOUT
    )
    return (proc.stdout or "") + (proc.stderr or "")


def _parse(out: str) -> tuple[int | None, int | None, int | None, int | None]:
    """Extract (neg_code, neg_exit, pos_code, pos_exit) from the probe output."""
    def _i(pat: str) -> int | None:
        m = re.search(pat, out)
        return int(m.group(1)) if m else None

    return (
        _i(r"NEG_CODE=(\d+)"),
        _i(r"NEG_EXIT=(\d+)"),
        _i(r"POS_CODE=(\d+)"),
        _i(r"POS_EXIT=(\d+)"),
    )


def main() -> int:
    if not POLICY.is_file():
        print(f"FAIL: egress policy missing: {POLICY}")
        return 1

    ok, detail = _openshell_available()
    if not ok:
        print(f"ERROR: cannot exercise deny-by-default egress: {detail}", file=sys.stderr)
        print("       (install OpenShell + start its gateway, or run where Docker+OpenShell exist)",
              file=sys.stderr)
        return 2

    try:
        out = _run_sandbox_probe()
    except subprocess.TimeoutExpired:
        print(f"ERROR: OpenShell sandbox did not finish within {SANDBOX_TIMEOUT}s", file=sys.stderr)
        return 2

    neg_code, neg_exit, pos_code, pos_exit = _parse(out)
    if neg_exit is None or pos_exit is None:
        print("ERROR: could not parse probe markers from sandbox output:", file=sys.stderr)
        print(out, file=sys.stderr)
        return 2

    print(f"policy: {POLICY.relative_to(REPO_ROOT)}  (enforced by real OpenShell sandbox)")

    result_ok = True

    # --- NEGATIVE (load-bearing): non-allow-listed CONNECT must be REFUSED ---
    # curl exit 56 == "CONNECT tunnel failed" (the OPA 403). Any successful tunnel
    # (exit 0 / a 2xx) means deny-by-default is NOT enforced.
    neg_refused = neg_exit != 0 and not (neg_code and 200 <= neg_code < 400)
    if neg_refused:
        print(f"PASS [negative]: CONNECT to {DENY_HOST} REFUSED "
              f"(curl exit {neg_exit}, http {neg_code}) — deny-by-default holds")
    else:
        print(f"FAIL [negative]: CONNECT to {DENY_HOST} was NOT refused "
              f"(curl exit {neg_exit}, http {neg_code}) — deny-by-default is NOT enforced")
        result_ok = False

    # --- POSITIVE: allow-listed CONNECT must SUCCEED ---
    pos_ok = pos_exit == 0 and bool(pos_code) and 200 <= pos_code < 400
    if pos_ok:
        print(f"PASS [positive]: CONNECT to {ALLOW_HOST} ESTABLISHED "
              f"(curl exit {pos_exit}, http {pos_code}) — allow-list does not break legitimate egress")
    else:
        print(f"FAIL [positive]: CONNECT to {ALLOW_HOST} did NOT establish "
              f"(curl exit {pos_exit}, http {pos_code}) — allow-listed egress is broken "
              f"(or no outbound network to {ALLOW_HOST})")
        result_ok = False

    print("RESULT:", "PASS" if result_ok else "FAIL")
    return 0 if result_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
