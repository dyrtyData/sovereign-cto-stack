#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""service_topology.py — derive the service-level coupling graph of Online Boutique.

The graphify AST graph is file/symbol-level; the tech-debt audit's headline
signal is *service-to-service* coupling: how many distinct gRPC backends each
service opens a client connection to. That topology is encoded in the source as
gRPC client wiring — each `*_SERVICE_ADDR` env var a service reads and then
dials (`mustConnGRPC` / `grpc.Dial` / `grpc.NewClient`) is one outbound edge to
the named backend service.

This is deterministic (no LLM, no network): we scan each src/<service>/ tree for
the `<NAME>_SERVICE_ADDR` references that are actually turned into a gRPC client
connection, map the env-var name to the target service, and count outbound edges
per service. Telemetry exporters (COLLECTOR_SERVICE_ADDR) are excluded — they are
not hipstershop business services.

Ground truth (research §13): frontend = 7 outbound gRPC edges, checkoutservice = 6.

Output: graphify-out/service-coupling.json
    {
      "services": ["frontend", "checkoutservice", ...],
      "outbound": { "frontend": ["productcatalogservice", ...], ... },
      "outbound_degree": { "frontend": 7, "checkoutservice": 6, ... },
      "edges": [ {"source": "frontend", "target": "cartservice",
                  "relation": "grpc", "evidence_file": "src/frontend/main.go"} ],
      "hubs": [ {"service": "frontend", "outbound_degree": 7}, ... ]
    }
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Map a *_SERVICE_ADDR env-var prefix to the canonical src/<service> directory.
# Restricted to the nine services defined in protos/demo.proto (the single shared
# gRPC contract): CartService, RecommendationService, ProductCatalogService,
# ShippingService, CurrencyService, PaymentService, EmailService, CheckoutService,
# AdService. These are the gRPC-coupling backends — a *_SERVICE_ADDR a service
# dials is one outbound gRPC edge to its target. (research §13)
ENV_TO_SERVICE = {
    "PRODUCT_CATALOG": "productcatalogservice",
    "CURRENCY": "currencyservice",
    "CART": "cartservice",
    "RECOMMENDATION": "recommendationservice",
    "SHIPPING": "shippingservice",
    "CHECKOUT": "checkoutservice",
    "AD": "adservice",
    "PAYMENT": "paymentservice",
    "EMAIL": "emailservice",
}
# Endpoints that are NOT gRPC business-service coupling edges, so they do not
# count toward outbound gRPC degree:
#   COLLECTOR        — OpenTelemetry trace exporter (telemetry, not a service)
#   SHOPPING_ASSISTANT — the newer shoppingassistantservice is REST/Flask
#                        (Gemini + AlloyDB), NOT in demo.proto's gRPC contract
#                        (research §13), so frontend's edge to it is not a gRPC edge.
EXCLUDE_ENV = {"COLLECTOR", "SHOPPING_ASSISTANT"}

# Match `<NAME>_SERVICE_ADDR` (Go/Python/C#/Node/Java all use this convention).
ADDR_RE = re.compile(r"\b([A-Z][A-Z0-9_]*?)_SERVICE_ADDR\b")
# A reference is a real outbound gRPC edge only if the service also dials it.
# These connection idioms appear across the polyglot services.
CONN_HINTS = (
    "mustConnGRPC",
    "grpc.Dial",
    "grpc.NewClient",
    "insecure_channel",       # python grpc
    "GrpcChannel",            # C#
    "ManagedChannelBuilder",  # java
    "createClient",           # node @grpc/grpc-js
    "credentials.createInsecure",
)

CODE_GLOBS = ("*.go", "*.py", "*.cs", "*.js", "*.ts", "*.java")


def _service_dirs(src: Path) -> list[Path]:
    return sorted(p for p in src.iterdir() if p.is_dir())


def _read_code(svc_dir: Path) -> str:
    parts: list[str] = []
    for pat in CODE_GLOBS:
        for f in svc_dir.rglob(pat):
            try:
                parts.append(f.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    return "\n".join(parts)


def _evidence_file(svc_dir: Path) -> str:
    """A representative source file that wires the gRPC clients (for the ticket)."""
    for cand in ("main.go", "main.py", "server.js", "index.js"):
        hits = list(svc_dir.rglob(cand))
        if hits:
            return str(hits[0])
    # fall back to the first code file that mentions a connection hint
    for pat in CODE_GLOBS:
        for f in svc_dir.rglob(pat):
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(h in txt for h in CONN_HINTS) and "_SERVICE_ADDR" in txt:
                return str(f)
    return str(svc_dir)


def derive(src: Path) -> dict:
    services = [d.name for d in _service_dirs(src)]
    outbound: dict[str, list[str]] = {}
    edges: list[dict] = []

    for svc_dir in _service_dirs(src):
        svc = svc_dir.name
        code = _read_code(svc_dir)
        if not code:
            continue
        # Only treat this service as a gRPC client if it has connection idioms.
        dials = any(h in code for h in CONN_HINTS)
        targets: list[str] = []
        seen: set[str] = set()
        for m in ADDR_RE.finditer(code):
            prefix = m.group(1)
            if prefix in EXCLUDE_ENV:
                continue
            target = ENV_TO_SERVICE.get(prefix)
            if not target or target == svc or target in seen:
                continue
            if not dials:
                continue
            seen.add(target)
            targets.append(target)
        if targets:
            ev = _evidence_file(svc_dir)
            try:
                ev_rel = str(Path(ev).relative_to(src.parent))
            except ValueError:
                ev_rel = ev
            outbound[svc] = sorted(targets)
            for t in sorted(targets):
                edges.append(
                    {"source": svc, "target": t, "relation": "grpc",
                     "evidence_file": ev_rel}
                )

    outbound_degree = {s: len(t) for s, t in outbound.items()}
    hubs = sorted(
        ({"service": s, "outbound_degree": d} for s, d in outbound_degree.items()),
        key=lambda x: x["outbound_degree"],
        reverse=True,
    )
    return {
        "target": "GoogleCloudPlatform/microservices-demo (Online Boutique)",
        "services": services,
        "outbound": outbound,
        "outbound_degree": outbound_degree,
        "edges": edges,
        "hubs": hubs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, help="path to the cloned src/ tree")
    ap.add_argument("--out", required=True, help="output JSON path")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    if not src.is_dir():
        print(f"service_topology: src not found: {src}")
        return 1

    data = derive(src)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")

    deg = data["outbound_degree"]
    print(f"service_topology: wrote {out}")
    print(f"  services: {len(data['services'])}, coupling edges: {len(data['edges'])}")
    for h in data["hubs"][:4]:
        print(f"  hub: {h['service']} -> {h['outbound_degree']} outbound gRPC edges")
    # surface the two known hubs explicitly for quick eyeballing
    print(f"  frontend={deg.get('frontend')}  checkoutservice={deg.get('checkoutservice')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
