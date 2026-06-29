#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""linear_mcp.py — minimal Linear MCP (Streamable HTTP) client for verification.

Used by scripts/assert_brownfield_ticket.py to read tickets back from Linear over
the SAME MCP endpoint Hermes uses (https://mcp.linear.app/mcp), reusing the OAuth
token the user already approved (`hermes mcp install linear`). No secret is
committed — the token is read from the local, gitignored Hermes token cache.

Token lookup order (first that exists):
  1. $LINEAR_MCP_TOKEN                                  (env override)
  2. ~/.hermes/profiles/cto-architecture/mcp-tokens/linear.json
  3. ~/.hermes/mcp-tokens/linear.json

This is a verification utility, not part of the agent runtime (the agent reaches
Linear through Hermes' own MCP client). It exists so the Phase-3 automated check
can assert the filed ticket carries the [Brownfield] label, a concrete
src/<service>/ file, and a grounding citation — without a human in the loop.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

URL = os.environ.get("LINEAR_MCP_URL", "https://mcp.linear.app/mcp")
TEAM = os.environ.get("LINEAR_TEAM", "Global South Ai Safety")
# Linear project every Hermes-filed ticket belongs to, so issues land in the
# project board instead of loose in the backlog. save_issue resolves the name to an
# id (project id d1335da7-fec7-4eee-95ef-d94dde85cde5). Override via $LINEAR_PROJECT.
PROJECT = os.environ.get("LINEAR_PROJECT", "sovereign-cto-stack")

_TOKEN_PATHS = [
    Path.home() / ".hermes/profiles/cto-architecture/mcp-tokens/linear.json",
    Path.home() / ".hermes/mcp-tokens/linear.json",
]


def _access_token() -> str:
    env = os.environ.get("LINEAR_MCP_TOKEN")
    if env:
        return env
    for p in _TOKEN_PATHS:
        if p.is_file():
            return json.loads(p.read_text())["access_token"]
    raise RuntimeError(
        "no Linear OAuth token found — run `hermes mcp install linear` (interactive) "
        "or set LINEAR_MCP_TOKEN"
    )


_sid: dict[str, str | None] = {"v": None}
_id = {"n": 0}
_AT: dict[str, str | None] = {"v": None}


def _post(method: str, params=None, notify: bool = False):
    if _AT["v"] is None:
        _AT["v"] = _access_token()
    payload: dict = {"jsonrpc": "2.0", "method": method}
    if not notify:
        _id["n"] += 1
        payload["id"] = _id["n"]
    if params is not None:
        payload["params"] = params
    headers = {
        "Authorization": f"Bearer {_AT['v']}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-06-18",
    }
    if _sid["v"]:
        headers["Mcp-Session-Id"] = _sid["v"]
    req = urllib.request.Request(
        URL, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=90)
    sid = resp.headers.get("Mcp-Session-Id")
    if sid:
        _sid["v"] = sid
    body = resp.read().decode()
    if "text/event-stream" in resp.headers.get("Content-Type", ""):
        body = "\n".join(l[5:].strip() for l in body.splitlines() if l.startswith("data:"))
    if notify:
        return None
    objs = [json.loads(b) for b in body.splitlines() if b.strip()]
    return objs[-1] if objs else None


def init() -> None:
    _post(
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "verify", "version": "0"},
        },
    )
    _post("notifications/initialized", {}, notify=True)


def tool(name: str, args: dict):
    r = _post("tools/call", {"name": name, "arguments": args})
    try:
        return json.loads(r["result"]["content"][0]["text"])
    except Exception:  # noqa: BLE001
        return r
