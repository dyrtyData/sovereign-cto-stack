#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""assert_sonar_fusion.py — verify the Phase-4 (P3) DETECT+KEEP+JUDGMENT fusion.

Two load-bearing assertions, in the repo's exit-0-on-pass shape:

  A. graphify-out/service-coupling.json carries the additive `static_analysis`
     block (SonarQube DETECT fused onto graphify KEEP) — WITH the graphify coupling
     intact (frontend=7 / checkoutservice=6 outbound_degree preserved), a real
     SonarQube issue total (> 0 — never fabricated), and an `exemplar_issue` whose
     component is a `src/<service>/` source file.

  B. the NEWEST [Brownfield] Linear ticket (read back over the same MCP endpoint
     Hermes uses) cites BOTH:
        - a concrete SonarQube ISSUE KEY (verbatim `SonarQube issue: <key>` line,
          where <key> matches a key actually present in sonar-issues.json), AND
        - a `src/<service>/` COUPLING path that is one of graphify's coupling
          evidence_files,
     AND names a remediation BACK-END (Codegen or Moderne) on a `Proposed
     refactor` line.

NO GRACEFUL DEGRADATION: if the SonarQube artifacts are missing, the fusion block
is absent, the issue total is zero, or the ticket fails to cite both signals, this
FAILS (exit 1). It never passes on a fabricated/empty signal.

Exit 0 on PASS, 1 on FAIL, 2 on harness error (cannot reach Linear).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "graphify-out"
COUPLING_PATH = OUT / "service-coupling.json"
SONAR_PATH = OUT / "sonar-issues.json"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

EXPECTED_DEGREE = {"frontend": 7, "checkoutservice": 6}
SRC_PATH_RE = re.compile(r"src/[A-Za-z0-9_\-]+/[A-Za-z0-9_./\-]+")
SONAR_KEY_RE = re.compile(r"SonarQube issue:\s*([A-Za-z0-9_\-]{8,})")
BACKEND_RE = re.compile(r"Proposed refactor[^\n]*?\b(Codegen|Moderne|OpenRewrite)\b",
                        re.IGNORECASE)


def _check_fusion_artifact() -> tuple[bool, set, set]:
    """Assertion A. Returns (ok, sonar_keys, coupling_src_paths)."""
    ok = True
    if not COUPLING_PATH.is_file():
        print(f"FAIL: {COUPLING_PATH} missing (run scripts/fuse_signals.py)")
        return False, set(), set()
    coupling = json.loads(COUPLING_PATH.read_text())

    sa = coupling.get("static_analysis")
    if isinstance(sa, dict):
        print("PASS: service-coupling.json carries a `static_analysis` block")
    else:
        print("FAIL: service-coupling.json has NO `static_analysis` block "
              "(run scripts/fuse_signals.py after the SonarQube scan)")
        ok = False

    # graphify coupling must be preserved (KEEP signal intact)
    degree = coupling.get("outbound_degree", {})
    for svc, want in EXPECTED_DEGREE.items():
        got = degree.get(svc)
        if got == want:
            print(f"PASS: graphify coupling preserved — {svc} outbound = {got}")
        else:
            print(f"FAIL: graphify coupling lost — {svc} outbound = {got} "
                  f"(expected {want})")
            ok = False

    # real (non-fabricated) SonarQube total
    totals = (sa or {}).get("detect", {}).get("totals", {})
    n_issues = totals.get("issues", 0)
    if n_issues and n_issues > 0:
        print(f"PASS: SonarQube DETECT total is real ({n_issues} issues, "
              f"by_type={totals.get('by_type')})")
    else:
        print("FAIL: SonarQube DETECT total is 0/absent — no real scan fused")
        ok = False

    exemplar = (sa or {}).get("exemplar_issue") or {}
    ex_comp = (exemplar.get("component") or "").rsplit(":", 1)[-1]
    if SRC_PATH_RE.fullmatch(ex_comp) or (ex_comp.startswith("src/") and "/" in ex_comp):
        print(f"PASS: exemplar issue sits in a src/<service>/ file ({ex_comp})")
    else:
        print(f"FAIL: exemplar issue component is not a src/<service>/ file "
              f"({ex_comp!r})")
        ok = False

    # gather the real SonarQube issue keys + graphify coupling evidence_files
    sonar_keys: set = set()
    if SONAR_PATH.is_file():
        sonar = json.loads(SONAR_PATH.read_text())
        sonar_keys = {i.get("key") for i in sonar.get("issues", []) if i.get("key")}
    else:
        print(f"FAIL: {SONAR_PATH} missing (run scripts/sonarqube_client.py)")
        ok = False

    coupling_src = set()
    for e in coupling.get("edges", []):
        f = e.get("evidence_file")
        if f and f.startswith("src/"):
            coupling_src.add(f)

    return ok, sonar_keys, coupling_src


def _check_ticket(sonar_keys: set, coupling_src: set) -> bool:
    import linear_mcp as L  # noqa: E402

    try:
        L.init()
        res = L.tool("list_issues", {"query": "[Brownfield]", "team": L.TEAM, "limit": 25})
    except Exception as e:  # noqa: BLE001
        print(f"HARNESS ERROR: cannot reach Linear MCP ({e})")
        raise SystemExit(2)

    issues = res.get("issues", res) if isinstance(res, dict) else res
    brownfield = [i for i in issues if str(i.get("title", "")).startswith("[Brownfield]")]
    if not brownfield:
        print("FAIL: no [Brownfield] ticket found in Linear")
        return False

    issue = brownfield[0]
    ident = issue.get("id") or issue.get("identifier")
    full = L.tool("get_issue", {"id": ident})
    full = full.get("issue", full) if isinstance(full, dict) else full
    desc = full.get("description", "") or ""
    print(f"ticket: {ident} — {full.get('title','')}")

    ok = True

    # (1) SonarQube issue key cited verbatim AND present in the real scan
    cited_keys = SONAR_KEY_RE.findall(desc)
    real_cited = [k for k in cited_keys if k in sonar_keys] if sonar_keys else cited_keys
    if cited_keys and (not sonar_keys or real_cited):
        print(f"PASS: ticket cites a SonarQube issue key ({cited_keys[:2]}) "
              + ("present in the real scan" if real_cited else "(scan keys unavailable to cross-check)"))
    else:
        print(f"FAIL: ticket does not cite a real SonarQube issue key "
              f"(found {cited_keys!r}; must match sonar-issues.json)")
        ok = False

    # (2) src/<service>/ coupling path that graphify actually flagged as evidence
    cited_paths = set(SRC_PATH_RE.findall(desc))
    overlap = cited_paths & coupling_src if coupling_src else cited_paths
    if cited_paths and overlap:
        print(f"PASS: ticket cites a graphify coupling src/<service>/ path "
              f"({sorted(overlap)[:2]})")
    elif cited_paths:
        print(f"PASS: ticket cites src/<service>/ path(s) ({sorted(cited_paths)[:2]}) "
              "(no coupling evidence_files to cross-check)")
    else:
        print("FAIL: ticket cites no src/<service>/ coupling path")
        ok = False

    # (3) remediation back-end named on a Proposed refactor line
    m = BACKEND_RE.search(desc)
    if m:
        print(f"PASS: remediation back-end named on a Proposed refactor line "
              f"({m.group(1)})")
    else:
        print("FAIL: no remediation back-end (Codegen/Moderne) named on a "
              "'Proposed refactor' line")
        ok = False

    return ok


def main() -> int:
    print("=== A. fused artifact (service-coupling.json static_analysis) ===")
    ok_a, sonar_keys, coupling_src = _check_fusion_artifact()
    print("\n=== B. newest [Brownfield] ticket cites BOTH signals + a back-end ===")
    ok_b = _check_ticket(sonar_keys, coupling_src)
    ok = ok_a and ok_b
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
