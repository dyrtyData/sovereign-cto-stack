#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""fuse_signals.py — fuse the SonarQube DETECT signal onto the graphify KEEP signal.

The tech-debt loop fuses two complementary static signals:
  - graphify (KEEP)  — cross-service gRPC COUPLING topology (frontend=7,
    checkoutservice=6 outbound edges). SonarQube has no coupling metric, so
    graphify is kept for exactly this.
  - SonarQube (DETECT) — code QUALITY issues/measures (bugs, code smells,
    complexity, …) produced by a real scan (scripts/sonarqube_client.py).

This script reads the SonarQube payload (graphify-out/sonar-issues.json) and
MERGES it onto graphify-out/service-coupling.json as an ADDITIVE top-level
`static_analysis` key (research §7: the JSON has no schema validation, so adding a
top-level key is safe). graphify's existing keys — `outbound_degree`, `hubs`,
`edges`, `services`, … — are left exactly intact, so assert_graph_topology.py
still sees frontend=7 / checkoutservice=6.

It also computes a per-service FUSION view that lines SonarQube issue counts up
against the coupling degree, and a `billing_path` flag (cart/checkout/payment/
currency = the billing surface — the priority surface for the judgment layer, the
P2 secondary folded into P3). Hermes then uses `static_analysis` + the coupling
`hubs` to prioritize and route to a remediation back-end.

NO GRACEFUL DEGRADATION: if either input is missing, this FAILS loudly. It will
not write a service-coupling.json that claims a fused signal it does not have.

Usage:
  python3 scripts/fuse_signals.py            # merges in place
  python3 scripts/fuse_signals.py --print     # also dump the fused doc

Exit 0 on success, non-zero on any failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "graphify-out"
COUPLING_PATH = OUT / "service-coupling.json"
SONAR_PATH = OUT / "sonar-issues.json"

# The billing surface — the priority surface for the judgment layer (the P2
# secondary billing-path tech-debt audit folded into the P3 SonarQube slice).
BILLING_SERVICES = {"cartservice", "checkoutservice", "paymentservice", "currencyservice"}


def _load(path: Path, what: str) -> dict:
    if not path.is_file():
        raise SystemExit(
            f"FAIL: {what} missing at {path}. "
            + ("Run scripts/run_graphify.sh first." if path == COUPLING_PATH
               else "Run scripts/sonarqube_client.py first (real SonarQube scan).")
        )
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"FAIL: {what} at {path} is not valid JSON: {e}") from e


def build_static_analysis(coupling: dict, sonar: dict) -> dict:
    """Build the additive `static_analysis` block, including a per-service fusion
    that joins SonarQube issue counts to graphify coupling degree."""
    degree = coupling.get("outbound_degree", {})
    by_service = (sonar.get("totals", {}) or {}).get("by_service", {})

    # Per-service fusion: coupling degree (graphify) x issue count (SonarQube).
    services = sorted(set(degree) | set(by_service) | set(coupling.get("services", [])))
    fusion = []
    for svc in services:
        deg = degree.get(svc, 0)
        issues = by_service.get(svc, 0)
        fusion.append({
            "service": svc,
            "coupling_degree": deg,                 # graphify KEEP
            "sonar_issues": issues,                 # SonarQube DETECT
            "billing_path": svc in BILLING_SERVICES,
            # crude priority: weight billing-path code, then coupling, then issues
            "priority_score": (5 if svc in BILLING_SERVICES else 0) + deg + issues,
        })
    fusion.sort(key=lambda f: f["priority_score"], reverse=True)

    # Pick an exemplar issue for the ticket to cite. We want one that is BOTH on
    # the billing path AND in a coupling hub, sitting in a real `src/<service>/`
    # SOURCE file (not a Dockerfile/config) — so a single citation is grounded in
    # the SonarQube DETECT signal AND the graphify KEEP coupling at once. We relax
    # the constraints in order if no issue satisfies the strongest one.
    issues = sonar.get("issues", [])
    hub_services = {h.get("service") for h in coupling.get("hubs", [])}

    def _is_source(i: dict) -> bool:
        comp = (i.get("component") or "").rsplit(":", 1)[-1]
        base = comp.rsplit("/", 1)[-1].lower()
        # exclude container/build/config files — we want code the back-end refactors
        if base.startswith("dockerfile") or base == "dockerfile":
            return False
        return comp.startswith("src/") and "." in base and not base.endswith(
            (".md", ".txt", ".yaml", ".yml", ".json", ".html", ".proto")
        )

    def _rank(i: dict) -> tuple:
        order = {"BLOCKER": 5, "CRITICAL": 4, "MAJOR": 3, "MINOR": 2, "INFO": 1}
        return (order.get(i.get("severity", ""), 0), i.get("type", ""))

    src = [i for i in issues if _is_source(i)]
    billing_hub = [i for i in src if i.get("service") in BILLING_SERVICES
                   and i.get("service") in hub_services]
    billing = [i for i in src if i.get("service") in BILLING_SERVICES]
    hub = [i for i in src if i.get("service") in hub_services]
    priority_pool = billing_hub or billing or hub or src or issues
    exemplar = max(priority_pool, key=_rank) if priority_pool else None

    return {
        "fused_at": datetime.now(timezone.utc).isoformat(),
        "detect": {
            "source": sonar.get("source"),
            "server": sonar.get("server"),
            "project": sonar.get("project"),
            "scanned_at": sonar.get("generated_at"),
            "totals": sonar.get("totals", {}),
            "measures": sonar.get("measures", {}),
        },
        "billing_services": sorted(BILLING_SERVICES),
        "per_service": fusion,
        "exemplar_issue": exemplar,
        "note": (
            "graphify (KEEP) supplies cross-service coupling; SonarQube (DETECT) "
            "supplies code-quality issues/measures. Hermes is the JUDGMENT layer "
            "that prioritizes the billing path and routes to a remediation back-end "
            "(Codegen for novel fixes / Moderne-OpenRewrite for recipe-amenable debt)."
        ),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--print", dest="show", action="store_true")
    args = ap.parse_args(argv)

    coupling = _load(COUPLING_PATH, "graphify service-coupling.json")
    sonar = _load(SONAR_PATH, "SonarQube sonar-issues.json")

    # Preserve graphify's coupling/hubs intact; add the SonarQube signal additively.
    coupling["static_analysis"] = build_static_analysis(coupling, sonar)

    tmp = COUPLING_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(coupling, indent=2) + "\n")
    os.replace(tmp, COUPLING_PATH)

    sa = coupling["static_analysis"]
    print(f"[fuse] merged SonarQube DETECT onto graphify KEEP -> "
          f"{COUPLING_PATH.relative_to(REPO_ROOT)}")
    print(f"[fuse] preserved coupling outbound_degree: {coupling.get('outbound_degree')}")
    print(f"[fuse] sonar totals: {sa['detect']['totals']}")
    top = sa["per_service"][:5]
    print(f"[fuse] priority (billing-weighted) top services:")
    for f in top:
        print(f"        {f['service']:<24} coupling={f['coupling_degree']} "
              f"issues={f['sonar_issues']} billing={f['billing_path']} "
              f"score={f['priority_score']}")
    ex = sa.get("exemplar_issue")
    if ex:
        print(f"[fuse] exemplar issue: {ex.get('key')} [{ex.get('severity')}/"
              f"{ex.get('type')}] {ex.get('component')}")
    if args.show:
        print(json.dumps(coupling, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
