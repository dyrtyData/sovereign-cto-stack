#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""render_service_graph.py — clean, legible service-level coupling visualization.

graphify-out/graph.html is graphify's raw file/symbol graph (hundreds of nodes) —
accurate but unusable as a demo surface. This renderer reads the *derived*
service-level topology (graphify-out/service-coupling.json, produced by
scripts/service_topology.py) and emits a clean, standalone, self-contained
visualization at graphify-out/service-graph.html:

  - ~11 service nodes (one per src/<service>/), not hundreds of symbols.
  - directed gRPC edges (arrows in the direction of the client -> backend call).
  - the two coupling hubs visually emphasized by outbound degree:
      * `frontend` (7 outbound) and `checkoutservice` (6) are largest, hottest
        color, and labeled with their degree; leaves are small and muted.

The output is a single HTML file (vis-network from CDN, data embedded inline) that
opens standalone in any browser — legible for a screen recording (Phase 4 records
this surface). No build step, no server.

Usage:
  python3 scripts/render_service_graph.py \
      --in graphify-out/service-coupling.json \
      --out graphify-out/service-graph.html
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

VIS_CDN = "https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"


def _node_style(svc: str, degree: int, max_degree: int) -> dict:
    """Size/color a node by its outbound gRPC degree (the coupling signal)."""
    is_hub = degree >= 4
    # size scales with degree; hubs get a big floor so they read as hubs.
    size = 18 + degree * 7
    # NOTE: shape "dot" renders the label on the (dark) canvas, not inside the
    # node — so label font must be LIGHT with a dark stroke outline for contrast.
    if is_hub:
        # hot hubs: frontend / checkout
        color = {"background": "#e8543f", "border": "#a8260f"}
        font = {"color": "#ffffff", "size": 22, "face": "monospace", "bold": True,
                "strokeWidth": 4, "strokeColor": "#0f1721"}
    elif degree > 0:
        # intermediate (e.g. recommendation -> productcatalog)
        color = {"background": "#f0b429", "border": "#b07a0a"}
        font = {"color": "#ffe1a8", "size": 16, "face": "monospace",
                "strokeWidth": 4, "strokeColor": "#0f1721"}
    else:
        # leaf services (pure backends)
        color = {"background": "#8aa0b6", "border": "#566b80"}
        font = {"color": "#cdd9e5", "size": 14, "face": "monospace",
                "strokeWidth": 4, "strokeColor": "#0f1721"}
    label = f"{svc}\n({degree} out)" if degree > 0 else svc
    return {
        "id": svc,
        "label": label,
        "value": size,
        "color": color,
        "font": font,
        "shape": "dot",
        "borderWidth": 3 if is_hub else 1,
    }


def build(coupling: dict) -> tuple[list[dict], list[dict]]:
    services = coupling.get("services", [])
    outbound = coupling.get("outbound", {})
    degree = coupling.get("outbound_degree", {})
    max_degree = max(degree.values(), default=0)

    nodes = [_node_style(s, degree.get(s, 0), max_degree) for s in services]

    edges = []
    for edge in coupling.get("edges", []):
        src, tgt = edge["source"], edge["target"]
        is_hub_edge = degree.get(src, 0) >= 4
        edges.append({
            "from": src,
            "to": tgt,
            "arrows": "to",
            "color": {"color": "#c0392b" if is_hub_edge else "#9fb3c8",
                      "opacity": 0.9 if is_hub_edge else 0.5},
            "width": 3 if is_hub_edge else 1,
            "smooth": {"type": "curvedCW", "roundness": 0.15},
        })
    return nodes, edges


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Online Boutique — service-level gRPC coupling</title>
<script src="{cdn}"></script>
<style>
  html, body {{ margin: 0; height: 100%; background: #0f1721; color: #e7eef6;
                font-family: -apple-system, Segoe UI, Roboto, sans-serif; }}
  #hdr {{ padding: 14px 20px 6px; }}
  #hdr h1 {{ margin: 0; font-size: 18px; }}
  #hdr p  {{ margin: 4px 0 0; font-size: 13px; color: #9fb3c8; }}
  #legend {{ font-size: 12px; color: #9fb3c8; padding: 0 20px 8px; }}
  #legend b {{ color: #e8543f; }}
  #net {{ width: 100%; height: calc(100% - 96px); }}
  .sw {{ display:inline-block; width:11px; height:11px; border-radius:50%;
         margin: 0 4px 0 12px; vertical-align: middle; }}
</style>
</head>
<body>
  <div id="hdr">
    <h1>Online Boutique — service-to-service gRPC coupling</h1>
    <p>{target} · node size &amp; color = outbound gRPC degree · arrows point client &rarr; backend</p>
  </div>
  <div id="legend">
    <span class="sw" style="background:#e8543f"></span><b>coupling hub</b> (&ge;4 outbound: frontend=7, checkoutservice=6)
    <span class="sw" style="background:#f0b429"></span>intermediate
    <span class="sw" style="background:#8aa0b6"></span>leaf backend (0 outbound)
  </div>
  <div id="net"></div>
<script>
  const nodes = new vis.DataSet({nodes});
  const edges = new vis.DataSet({edges});
  const container = document.getElementById('net');
  const options = {{
    physics: {{ stabilization: true, barnesHut: {{ gravitationalConstant: -9000,
               springLength: 180, springConstant: 0.03 }} }},
    interaction: {{ hover: true, tooltipDelay: 120 }},
    nodes: {{ scaling: {{ min: 18, max: 70 }}, shadow: true }},
    edges: {{ shadow: false }},
  }};
  new vis.Network(container, {{ nodes, edges }}, options);
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", required=True,
                    help="path to service-coupling.json")
    ap.add_argument("--out", required=True, help="output HTML path")
    args = ap.parse_args()

    inp = Path(args.inp)
    if not inp.is_file():
        print(f"render_service_graph: input not found: {inp} "
              f"(run scripts/run_graphify.sh first)")
        return 1
    coupling = json.loads(inp.read_text())
    nodes, edges = build(coupling)

    html = HTML.format(
        cdn=VIS_CDN,
        target=coupling.get("target", "Online Boutique"),
        nodes=json.dumps(nodes),
        edges=json.dumps(edges),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    deg = coupling.get("outbound_degree", {})
    print(f"render_service_graph: wrote {out}")
    print(f"  {len(nodes)} service nodes, {len(edges)} gRPC edges")
    print(f"  hubs: frontend={deg.get('frontend')}  checkoutservice={deg.get('checkoutservice')}")
    print(f"  open in a browser: open {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
