#!/usr/bin/env python3
"""assert_egress_policy.py — prove deny-by-default egress is ENFORCED (Phase 2 / P1).

The headline "sovereign"/safety gate. Deny-by-default egress is only meaningful if
you can demonstrate a DENIAL, so this gate's LOAD-BEARING assertion is the NEGATIVE
test (design Q3-sub, Option β):

  NEGATIVE (load-bearing): a CONNECT to a host that is NOT on the egress/policy.yaml
    allow-list, routed through the egress proxy, must be REFUSED. If that CONNECT
    succeeds, the gate FAILS — a proxy that blocks nothing is not deny-by-default.

  POSITIVE: a CONNECT to an allow-listed host (api.linear.app:443) through the same
    proxy must SUCCEED — proving the allow-list does not break legitimate egress
    (this is what lets the existing hero-loop gates keep reaching Linear with the
    proxy up).

The network OPA-CONNECT layer is independent of the Landlock filesystem layer, so
this assertion stays reliable even where Landlock `best_effort` silently degrades
on macOS (OpenShell #803 — docs/system-design-tradeoffs.md).

How it gets a proxy to test:
  1. If something is already listening on the proxy port (EGRESS_HOST_PORT, default
     8888), it tests that.
  2. Else, if Docker is available, it brings the compose `egress` profile up
     (`docker compose --profile egress up -d --build egress-proxy`) and tests the
     published port. (It leaves the service running unless EGRESS_TEARDOWN=1.)
  3. Else (no Docker), it starts egress/egress_proxy.py directly on the host as a
     subprocess against egress/policy.yaml and tests that — so the load-bearing
     assertion is still checkable in a CI box without Docker.

A successful CONNECT is detected by reading the proxy's HTTP response line: an
allow-listed target returns `200 Connection established`; a denied target returns
`403 egress-policy-deny`. The positive check additionally requires that the proxy
actually opened the upstream tunnel (the `200` line), not merely that the policy
*would* allow it.

Exit 0 on PASS, 1 on FAIL, 2 on harness error.

Usage:
  python3 scripts/assert_egress_policy.py
  EGRESS_HOST_PORT=8888 python3 scripts/assert_egress_policy.py
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY = REPO_ROOT / "egress" / "policy.yaml"
PROXY_SRC = REPO_ROOT / "egress" / "egress_proxy.py"

PROXY_HOST = os.environ.get("EGRESS_PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.environ.get("EGRESS_HOST_PORT", "8888"))

# A host that MUST NOT be on the allow-list (the negative target). Picked to be a
# stable, unrelated public host; the assertion is about the REFUSAL, never a real
# connection to it.
DENY_HOST = os.environ.get("EGRESS_DENY_HOST", "example.com")
DENY_PORT = 443
# An allow-listed host (the positive target) — must match egress/policy.yaml.
ALLOW_HOST = os.environ.get("EGRESS_ALLOW_HOST", "api.linear.app")
ALLOW_PORT = 443


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def _proxy_responsive(retries: int = 20, delay: float = 0.5) -> bool:
    """Probe the proxy with a real CONNECT until it returns an HTTP status line.

    A freshly-bound listener (or a Docker port-forward that just opened) can RST
    the first few connections before the accept loop is serving — `_port_open`
    returns true a beat before the proxy actually answers. We probe a host the
    proxy must DENY and wait until it replies with a `403` status line (rather
    than resetting), which proves the request/response path is live. This removes
    the startup race so the gate is reliable when it brings the proxy up itself.
    """
    for _ in range(retries):
        established, status = connect_via_proxy(DENY_HOST, DENY_PORT)
        if status.startswith("HTTP/"):
            return True
        time.sleep(delay)
    return False


def connect_via_proxy(target_host: str, target_port: int) -> tuple[bool, str]:
    """Send an HTTP CONNECT through the proxy. Return (tunnel_established, status_line)."""
    s = socket.socket()
    s.settimeout(20)
    try:
        s.connect((PROXY_HOST, PROXY_PORT))
        req = (
            f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
            f"Host: {target_host}:{target_port}\r\n\r\n"
        )
        s.sendall(req.encode())
        resp = b""
        while b"\r\n" not in resp and len(resp) < 1024:
            chunk = s.recv(1024)
            if not chunk:
                break
            resp += chunk
        status = resp.split(b"\r\n", 1)[0].decode(errors="replace")
        established = " 200 " in f" {status} " or status.endswith("200 Connection established")
        return established, status
    except OSError as e:
        return False, f"<socket error: {e}>"
    finally:
        s.close()


def _ensure_proxy() -> tuple[str, subprocess.Popen | None]:
    """Make a proxy reachable on PROXY_HOST:PROXY_PORT. Return (mode, host_proc)."""
    if _port_open(PROXY_HOST, PROXY_PORT):
        print(f"egress gate: proxy already listening on {PROXY_HOST}:{PROXY_PORT}")
        _proxy_responsive()
        return "preexisting", None

    docker = subprocess.run(
        ["docker", "compose", "version"], capture_output=True, cwd=REPO_ROOT
    )
    if docker.returncode == 0:
        print("egress gate: bringing up compose `egress` profile (egress-proxy)...")
        up = subprocess.run(
            ["docker", "compose", "--profile", "egress", "up", "-d", "--build", "egress-proxy"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if up.returncode != 0:
            print(up.stdout)
            print(up.stderr, file=sys.stderr)
            print("egress gate: compose up failed — falling back to host proxy")
        else:
            for _ in range(30):
                if _port_open(PROXY_HOST, PROXY_PORT) and _proxy_responsive():
                    print(f"egress gate: egress-proxy up on {PROXY_HOST}:{PROXY_PORT}")
                    return "compose", None
                time.sleep(1)
            print("egress gate: compose egress-proxy did not open port in time — host fallback")

    # Host fallback: run the stdlib proxy directly.
    print(f"egress gate: starting host proxy {PROXY_SRC.name} on :{PROXY_PORT}")
    env = {**os.environ, "EGRESS_POLICY": str(POLICY), "EGRESS_PORT": str(PROXY_PORT)}
    proc = subprocess.Popen(
        [sys.executable, str(PROXY_SRC)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    for _ in range(20):
        if _port_open(PROXY_HOST, PROXY_PORT) and _proxy_responsive():
            return "host", proc
        time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("egress gate: could not start any proxy to test")


def main() -> int:
    if not POLICY.is_file():
        print(f"FAIL: egress policy missing: {POLICY}")
        return 1

    try:
        mode, host_proc = _ensure_proxy()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    ok = True
    try:
        print(f"policy: {POLICY.relative_to(REPO_ROOT)}  (proxy mode: {mode})")

        # --- NEGATIVE (load-bearing): non-allow-listed CONNECT must be REFUSED ---
        neg_ok, neg_status = connect_via_proxy(DENY_HOST, DENY_PORT)
        if neg_ok:
            print(f"FAIL [negative]: CONNECT {DENY_HOST}:{DENY_PORT} was NOT refused "
                  f"(proxy said: {neg_status!r}) — deny-by-default is NOT enforced")
            ok = False
        else:
            print(f"PASS [negative]: CONNECT {DENY_HOST}:{DENY_PORT} REFUSED "
                  f"(proxy said: {neg_status!r}) — deny-by-default holds")

        # --- POSITIVE: allow-listed CONNECT must SUCCEED ---
        pos_ok, pos_status = connect_via_proxy(ALLOW_HOST, ALLOW_PORT)
        if pos_ok:
            print(f"PASS [positive]: CONNECT {ALLOW_HOST}:{ALLOW_PORT} ESTABLISHED "
                  f"(proxy said: {pos_status!r}) — allow-list does not break legitimate egress")
        else:
            print(f"FAIL [positive]: CONNECT {ALLOW_HOST}:{ALLOW_PORT} did NOT establish "
                  f"(proxy said: {pos_status!r}) — allow-listed egress is broken "
                  f"(or no outbound network to {ALLOW_HOST})")
            ok = False
    finally:
        if host_proc is not None:
            host_proc.terminate()
            try:
                host_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                host_proc.kill()
        if mode == "compose" and os.environ.get("EGRESS_TEARDOWN") == "1":
            subprocess.run(
                ["docker", "compose", "--profile", "egress", "down"],
                cwd=REPO_ROOT, capture_output=True,
            )

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
