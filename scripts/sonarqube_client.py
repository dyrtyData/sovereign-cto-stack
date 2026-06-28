#!/usr/bin/env python3
"""sonarqube_client.py — minimal stdlib SonarQube Web API client that pulls REAL
issues + measures from a running SonarQube Community server and writes
graphify-out/sonar-issues.json.

Follows the scripts/linear_mcp.py / scripts/stripe_client.py reference-client
pattern (token resolution -> one urllib request helper, no third-party SDK) and
calls the LIVE SonarQube Web API:

  GET /api/issues/search       (params: componentKeys, types, ps, p, facets, ...)
  GET /api/measures/component  (params: component, metricKeys=ncloc,code_smells,...)

DETECT source for the tech-debt loop. graphify is KEPT for cross-service coupling
(SonarQube has no coupling metric); scripts/fuse_signals.py merges what this writes
onto graphify-out/service-coupling.json under an additive `static_analysis` key.

NO GRACEFUL DEGRADATION / NO FABRICATION (explicit user constraint):
- The Bearer token is read from $SONAR_TOKEN, else ./.sonar-token, else
  ~/.hermes/sonar-token. If absent, this script FAILS loudly.
- If SonarQube is unreachable, or the project has not been scanned (zero issues
  AND zero measures), this script FAILS loudly — it NEVER fabricates issues.

Usage:
  python3 scripts/sonarqube_client.py                  # writes graphify-out/sonar-issues.json
  python3 scripts/sonarqube_client.py --print          # also dump to stdout
  python3 scripts/sonarqube_client.py --project KEY     # override project key

Exit 0 on success, non-zero on any failure (no silent pass).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "graphify-out" / "sonar-issues.json"
API_BASE = os.environ.get("SONAR_URL", "http://localhost:9000").rstrip("/")
DEFAULT_PROJECT = os.environ.get("SONAR_PROJECT", "online-boutique")

# Measures worth surfacing for the tech-debt judgment layer.
METRIC_KEYS = [
    "ncloc", "code_smells", "bugs", "vulnerabilities",
    "complexity", "cognitive_complexity", "coverage",
    "duplicated_lines_density", "sqale_index", "reliability_rating",
    "security_rating", "sqale_rating",
]

_TOKEN_PATHS = [
    REPO_ROOT / ".sonar-token",
    Path.home() / ".hermes" / "sonar-token",
]


def resolve_token() -> str:
    """SonarQube user/analysis token from $SONAR_TOKEN, else a gitignored file.

    Never returns an empty/fabricated value — raises on absence (no-degradation).
    """
    env = os.environ.get("SONAR_TOKEN")
    if env:
        return env.strip()
    for p in _TOKEN_PATHS:
        if p.is_file():
            tok = p.read_text().strip()
            if tok:
                return tok
    raise SystemExit(
        "FAIL: no SonarQube token found ($SONAR_TOKEN, ./.sonar-token, or "
        "~/.hermes/sonar-token). Mint one against the running server "
        "(admin/admin first login) — this client does NOT fabricate issues."
    )


_TOK: dict[str, str | None] = {"v": None}


def api(path: str, params: dict | None = None) -> dict:
    """One GET against the SonarQube Web API. Bearer-token auth.

    SonarQube accepts the token either as a Bearer token (>= 10.0) or as HTTP
    Basic with the token as the username and an empty password. We send Bearer
    and fall back to Basic on a 401 so this works across Community versions.
    Raises (loud) on any other non-2xx — never returns a silent empty result.
    """
    if _TOK["v"] is None:
        _TOK["v"] = resolve_token()
    token = _TOK["v"]
    url = f"{API_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"

    def _do(auth_header: str) -> dict:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", auth_header)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())

    try:
        return _do(f"Bearer {token}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # Basic auth fallback: token as username, empty password.
            basic = base64.b64encode(f"{token}:".encode()).decode()
            try:
                return _do(f"Basic {basic}")
            except urllib.error.HTTPError as e2:
                body = e2.read().decode(errors="ignore")
                raise SystemExit(
                    f"FAIL: SonarQube GET {path} -> HTTP {e2.code}: {body[:300]} "
                    "(token rejected — re-mint against the running server)"
                ) from e2
        body = e.read().decode(errors="ignore")
        raise SystemExit(
            f"FAIL: SonarQube GET {path} -> HTTP {e.code}: {body[:300]}"
        ) from e
    except urllib.error.URLError as e:
        raise SystemExit(
            f"FAIL: SonarQube unreachable at {API_BASE} ({e.reason}). Start it: "
            "docker compose --profile sonar up -d sonarqube — NO graceful "
            "degradation, the gate must FAIL when the server is down."
        ) from e


def fetch_issues(project: str) -> list[dict]:
    """Walk /api/issues/search pagination, collecting every OPEN issue."""
    out: list[dict] = []
    page = 1
    while True:
        res = api(
            "/api/issues/search",
            {
                "componentKeys": project,
                "statuses": "OPEN,CONFIRMED,REOPENED",
                "ps": 500,
                "p": page,
                "additionalFields": "rules",
            },
        )
        issues = res.get("issues", [])
        out.extend(issues)
        paging = res.get("paging", {})
        total = paging.get("total", len(out))
        if len(out) >= total or not issues:
            break
        page += 1
        if page > 40:  # safety bound
            break
    return out


def fetch_measures(project: str) -> dict:
    res = api(
        "/api/measures/component",
        {"component": project, "metricKeys": ",".join(METRIC_KEYS)},
    )
    comp = res.get("component", {})
    measures = {}
    for m in comp.get("measures", []):
        measures[m["metric"]] = m.get("value", m.get("bestValue"))
    return measures


def _service_of(component: str) -> str | None:
    """Map a SonarQube component key (…:src/<service>/…) to a service name so the
    fusion step can line issues up against the graphify coupling hubs."""
    # component looks like "online-boutique:src/frontend/main.go"
    path = component.split(":", 1)[-1]
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "src":
        return parts[1]
    return None


def build_payload(project: str) -> dict:
    issues = fetch_issues(project)
    measures = fetch_measures(project)

    if not issues and not measures:
        raise SystemExit(
            f"FAIL: SonarQube project {project!r} has NO issues AND NO measures — "
            "it has not been scanned. Run sonar-scanner against "
            "workspaces/microservices-demo/ first. This client does NOT fabricate."
        )

    # Compact each issue + annotate the owning service for the fusion step.
    compact = []
    by_service: Counter = Counter()
    by_severity: Counter = Counter()
    by_type: Counter = Counter()
    for i in issues:
        comp = i.get("component", "")
        svc = _service_of(comp)
        sev = i.get("severity", "")
        typ = i.get("type", "")
        if svc:
            by_service[svc] += 1
        if sev:
            by_severity[sev] += 1
        if typ:
            by_type[typ] += 1
        compact.append({
            "key": i.get("key"),
            "rule": i.get("rule"),
            "severity": sev,
            "type": typ,
            "component": comp,
            "service": svc,
            "line": i.get("line"),
            "message": i.get("message", ""),
            "effort": i.get("effort"),
        })

    return {
        "source": "sonarqube_community",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "server": API_BASE,
        "project": project,
        "totals": {
            "issues": len(compact),
            "by_severity": dict(by_severity),
            "by_type": dict(by_type),
            "by_service": dict(by_service),
        },
        "measures": measures,
        "issues": compact,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default=DEFAULT_PROJECT, help="SonarQube project key")
    ap.add_argument("--print", dest="show", action="store_true",
                    help="also print the payload to stdout")
    args = ap.parse_args(argv)

    print(f"[sonar] server {API_BASE}  project {args.project!r} — reading live Web API")
    payload = build_payload(args.project)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(tmp, OUT_PATH)

    t = payload["totals"]
    print(f"[sonar] wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"[sonar] issues={t['issues']}  by_type={t['by_type']}  "
          f"by_severity={t['by_severity']}")
    print(f"[sonar] top services by issue count: "
          f"{dict(Counter(t['by_service']).most_common(5))}")
    print(f"[sonar] measures: ncloc={payload['measures'].get('ncloc')} "
          f"code_smells={payload['measures'].get('code_smells')} "
          f"bugs={payload['measures'].get('bugs')} "
          f"complexity={payload['measures'].get('complexity')}")
    if args.show:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
