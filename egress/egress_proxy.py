#!/usr/bin/env python3
"""egress_proxy.py — deny-by-default HTTP CONNECT proxy gated by egress/policy.yaml.

Phase 2 (P1). The runtime half of the sovereign-egress story: a forward proxy that
only tunnels HTTP CONNECT requests whose `host:port` is named in the reviewable
allow-list (egress/policy.yaml). Every other CONNECT is REFUSED with
`403 egress-policy-deny`. This is the enforcement point the gate
(scripts/assert_egress_policy.py) drives: a non-allow-listed CONNECT must be
refused (the load-bearing negative test) while api.linear.app:443 must succeed.

Design notes:
  - stdlib only (no third-party deps), mirroring the repo's reference-client
    pattern (scripts/linear_mcp.py) so a clean clone runs it with nothing to
    install. The image (egress/Dockerfile) is `python:3.12-slim`.
  - It tunnels TLS opaquely (CONNECT only) — it never terminates TLS, so it sees
    only the host:port from the CONNECT line, exactly the granularity policy.yaml
    declares. Plain GET/POST proxying is intentionally NOT supported; the
    sub-tools talk HTTPS, and a CONNECT-only proxy keeps the allow-list the single
    enforcement surface.
  - The policy file is parsed by a tiny purpose-built YAML reader (POLICY_YAML is
    a flat host/port/enforcement structure) so we need no PyYAML in the image.

Env:
  EGRESS_POLICY   path to policy.yaml (default /etc/egress/policy.yaml)
  EGRESS_PORT     listen port (default 8888)

Usage (host smoke):
  EGRESS_POLICY=egress/policy.yaml EGRESS_PORT=8888 python3 egress/egress_proxy.py
  curl -x http://127.0.0.1:8888 https://api.linear.app   # allowed (tunnels)
  curl -x http://127.0.0.1:8888 https://example.com       # refused (403)
"""
from __future__ import annotations

import os
import re
import select
import socket
import sys
import threading
from pathlib import Path

DEFAULT_POLICY = "/etc/egress/policy.yaml"
DEFAULT_PORT = 8888
BUFSIZE = 65536


def load_allowlist(policy_path: Path) -> set[tuple[str, int]]:
    """Parse policy.yaml into a set of allowed (host, port) pairs.

    Only endpoints with `enforcement: enforce` under `network_policies` are
    admitted. Deny-by-default: anything not returned here is refused.

    The parser is deliberately minimal — it tracks the current `host:`/`port:`/
    `enforcement:` of each endpoint block (a `- host:` list item) and emits the
    pair when the block closes or a new one starts. No external YAML dependency.
    """
    allow: set[tuple[str, int]] = set()
    if not policy_path.is_file():
        raise FileNotFoundError(f"egress policy not found: {policy_path}")

    in_network = False
    cur: dict[str, object] = {}

    def flush() -> None:
        host = cur.get("host")
        port = cur.get("port")
        enf = cur.get("enforcement", "enforce")  # default to enforce if omitted
        if host and port and enf == "enforce":
            allow.add((str(host), int(port)))  # type: ignore[arg-type]

    for raw in policy_path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        # Top-level section switch.
        if indent == 0 and stripped.endswith(":"):
            in_network = stripped == "network_policies:"
            continue
        if not in_network:
            continue

        # A new endpoint list item begins ("- host: ...").
        m = re.match(r"-\s*host:\s*(\S+)", stripped)
        if m:
            flush()
            cur = {"host": m.group(1)}
            continue
        m = re.match(r"host:\s*(\S+)", stripped)
        if m and stripped.startswith("host:"):
            cur["host"] = m.group(1)
            continue
        m = re.match(r"port:\s*(\d+)", stripped)
        if m:
            cur["port"] = int(m.group(1))
            continue
        m = re.match(r"enforcement:\s*(\S+)", stripped)
        if m:
            cur["enforcement"] = m.group(1)
            continue
    flush()
    return allow


CONNECT_RE = re.compile(rb"^CONNECT\s+([^:\s]+):(\d+)\s+HTTP/1\.[01]", re.IGNORECASE)


def _pipe(a: socket.socket, b: socket.socket) -> None:
    """Bidirectionally splice two sockets until one side closes."""
    socks = [a, b]
    try:
        while True:
            r, _, x = select.select(socks, [], socks, 60)
            if x or not r:
                break
            for s in r:
                data = s.recv(BUFSIZE)
                if not data:
                    return
                (b if s is a else a).sendall(data)
    except OSError:
        return


class Proxy:
    def __init__(self, allow: set[tuple[str, int]], port: int) -> None:
        self.allow = allow
        self.port = port

    def serve(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.port))
        srv.listen(128)
        allowed = sorted(f"{h}:{p}" for h, p in self.allow)
        print(f"egress-proxy: deny-by-default CONNECT proxy on :{self.port}", flush=True)
        print(f"egress-proxy: {len(allowed)} allow-listed endpoint(s): {allowed}", flush=True)
        while True:
            client, addr = srv.accept()
            threading.Thread(target=self._handle, args=(client, addr), daemon=True).start()

    def _handle(self, client: socket.socket, addr) -> None:
        try:
            client.settimeout(30)
            req = b""
            while b"\r\n\r\n" not in req and len(req) < 8192:
                chunk = client.recv(BUFSIZE)
                if not chunk:
                    return
                req += chunk
            m = CONNECT_RE.match(req)
            if not m:
                # Deny-by-default also covers non-CONNECT verbs: this proxy only
                # tunnels HTTPS. A plain GET/POST proxy request is refused.
                client.sendall(
                    b"HTTP/1.1 405 egress-connect-only\r\nConnection: close\r\n\r\n"
                    b"egress-proxy: only HTTP CONNECT (HTTPS tunnelling) is supported\n"
                )
                return
            host = m.group(1).decode()
            port = int(m.group(2))

            if (host, port) not in self.allow:
                msg = f"egress-proxy: DENY CONNECT {host}:{port} (not allow-listed)"
                print(msg, flush=True)
                client.sendall(
                    b"HTTP/1.1 403 egress-policy-deny\r\nConnection: close\r\n\r\n"
                    + msg.encode()
                    + b"\n"
                )
                return

            # Allow-listed: open the upstream tunnel and splice.
            try:
                upstream = socket.create_connection((host, port), timeout=15)
            except OSError as e:
                client.sendall(
                    b"HTTP/1.1 502 egress-upstream-unreachable\r\nConnection: close\r\n\r\n"
                    + f"egress-proxy: upstream {host}:{port} unreachable: {e}\n".encode()
                )
                return
            print(f"egress-proxy: ALLOW CONNECT {host}:{port}", flush=True)
            client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            client.settimeout(None)
            _pipe(client, upstream)
            upstream.close()
        except OSError:
            return
        finally:
            try:
                client.close()
            except OSError:
                pass


def main(argv: list[str]) -> int:
    policy_path = Path(os.environ.get("EGRESS_POLICY", DEFAULT_POLICY))
    port = int(os.environ.get("EGRESS_PORT", str(DEFAULT_PORT)))
    try:
        allow = load_allowlist(policy_path)
    except FileNotFoundError as e:
        print(f"egress-proxy: {e}", file=sys.stderr)
        return 2
    if not allow:
        print(
            f"egress-proxy: refusing to start — no enforce endpoints in {policy_path}",
            file=sys.stderr,
        )
        return 2
    Proxy(allow, port).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
