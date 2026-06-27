#!/usr/bin/env python3
"""assert_graph_topology.py — verify the known Online Boutique coupling topology.

Phase-3 automated check (outline §"Automated Verification"):
- graphify-out/graph.json exists and is a non-empty NetworkX export.
- graphify-out/service-coupling.json shows the known service-level topology:
  frontend = 7 outbound gRPC edges, checkoutservice = 6 (research §13).

Exit 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "graphify-out"
EXPECTED = {"frontend": 7, "checkoutservice": 6}


def main() -> int:
    ok = True

    graph = OUT / "graph.json"
    if not graph.is_file() or graph.stat().st_size == 0:
        print(f"FAIL: {graph} missing or empty")
        return 1
    g = json.loads(graph.read_text())
    n_nodes = len(g.get("nodes", []))
    n_edges = len(g.get("edges", g.get("links", [])))
    if n_nodes == 0:
        print("FAIL: graph.json has no nodes")
        ok = False
    print(f"graph.json: {n_nodes} nodes, {n_edges} edges")

    for extra in ("GRAPH_REPORT.md", "graph.html"):
        p = OUT / extra
        status = "ok" if (p.is_file() and p.stat().st_size > 0) else "MISSING"
        print(f"{extra}: {status}")
        if status == "MISSING":
            ok = False

    coupling = OUT / "service-coupling.json"
    if not coupling.is_file():
        print(f"FAIL: {coupling} missing (run scripts/run_graphify.sh)")
        return 1
    c = json.loads(coupling.read_text())
    degree = c.get("outbound_degree", {})
    for svc, want in EXPECTED.items():
        got = degree.get(svc)
        verdict = "PASS" if got == want else "FAIL"
        print(f"{verdict}: {svc} outbound gRPC edges = {got} (expected {want})")
        if got != want:
            ok = False

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
