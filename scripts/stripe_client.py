#!/usr/bin/env python3
"""stripe_client.py — minimal stdlib Stripe REST client that computes REAL
test-mode MRR / churn / monthly cohorts and writes recordings/stripe_metrics.json.

Follows the scripts/linear_mcp.py reference-client pattern (key resolution -> a
single urllib request helper, no third-party SDK) and calls the LIVE Stripe API
(api.stripe.com/v1) in test mode. The PMF brief grounds its AARRR Revenue &
Retention cells against the JSON artifact this writes (design Q4 Option B).

NO GRACEFUL DEGRADATION / NO FABRICATION (explicit user constraint):
- The key is read from $STRIPE_API_KEY, else from ./.env. If absent, this script
  FAILS loudly — it never fabricates MRR/churn/cohort numbers.
- TEST-KEY-ONLY GUARD: the key MUST start with `sk_test_`/`rk_test_`. A live key
  (`sk_live_`/`rk_live_`) is REFUSED so we never touch a real account.
- The metrics are computed from the REAL objects Stripe returns. If the sandbox
  is empty (no active subscriptions), seed it first with scripts/stripe_seed.py.

Metrics written ({mrr, churn, cohorts:[...]}):
- mrr            : monthly recurring revenue (USD) summed over ACTIVE subscriptions,
                   normalizing yearly intervals to a monthly figure.
- active_subs    : count of active subscriptions.
- churn          : canceled / (active + canceled) over all seeded subscriptions
                   (a simple lifetime churn rate), plus the raw counts.
- cohorts[]      : per signup-month {cohort, active, canceled, mrr}.

Usage:
  python3 scripts/stripe_client.py            # writes recordings/stripe_metrics.json
  python3 scripts/stripe_client.py --print    # also dump the metrics to stdout

Exit 0 on success, non-zero on any failure (no silent pass).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
OUT_PATH = REPO_ROOT / "recordings" / "stripe_metrics.json"
API_BASE = os.environ.get("STRIPE_API_BASE", "https://api.stripe.com/v1")

_TEST_PREFIXES = ("sk_test_", "rk_test_")
_LIVE_PREFIXES = ("sk_live_", "rk_live_")


def _env_key() -> str | None:
    """STRIPE_API_KEY from the process env, else parsed from ./.env (gitignored)."""
    if os.environ.get("STRIPE_API_KEY"):
        return os.environ["STRIPE_API_KEY"]
    if ENV_FILE.is_file():
        for raw in ENV_FILE.read_text().splitlines():
            line = raw.strip()
            if line.startswith("STRIPE_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    return None


def resolve_key() -> str:
    """Return the Stripe key, enforcing the TEST-key-only guard.

    Raises (never returns a fabricated/empty value) when the key is missing or
    looks like a live key — the no-graceful-degradation contract.
    """
    key = _env_key()
    if not key:
        raise SystemExit(
            "FAIL: STRIPE_API_KEY not found (env or ./.env). The Stripe grounding "
            "requires a real Stripe TEST key (sk_test_…). This client does NOT "
            "fabricate MRR/churn — set STRIPE_API_KEY and retry."
        )
    if key.startswith(_LIVE_PREFIXES):
        raise SystemExit(
            "REFUSED: STRIPE_API_KEY looks like a LIVE key (sk_live_/rk_live_). "
            "This stack only ever touches Stripe TEST mode. Use a sk_test_ key."
        )
    if not key.startswith(_TEST_PREFIXES):
        raise SystemExit(
            f"REFUSED: STRIPE_API_KEY has an unexpected prefix ({key[:8]}…); "
            "expected a TEST key (sk_test_/rk_test_)."
        )
    return key


_KEY: dict[str, str | None] = {"v": None}


def api(method: str, path: str, params: dict | None = None) -> dict:
    """One urllib request against api.stripe.com/v1 (form-encoded, like the SDK).

    Raises on any non-2xx so failures are loud (no silent empty result).
    """
    if _KEY["v"] is None:
        _KEY["v"] = resolve_key()
    params = params or {}
    url = f"{API_BASE}{path}"
    data = None
    if method in ("GET", "DELETE") and params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    elif params:
        data = urllib.parse.urlencode(params, doseq=True).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_KEY['v']}")
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:  # noqa: PERF203
        body = e.read().decode(errors="ignore")
        raise SystemExit(
            f"FAIL: Stripe API {method} {path} -> HTTP {e.code}: {body[:300]}"
        ) from e


def _paginate(path: str, params: dict) -> list[dict]:
    """Walk Stripe cursor pagination, collecting every object."""
    out: list[dict] = []
    starting_after = None
    while True:
        p = dict(params)
        p["limit"] = 100
        if starting_after:
            p["starting_after"] = starting_after
        page = api("GET", path, p)
        data = page.get("data", [])
        out.extend(data)
        if not page.get("has_more") or not data:
            break
        starting_after = data[-1]["id"]
    return out


def _sub_monthly_amount(sub: dict) -> float:
    """Monthly USD for a subscription, normalizing yearly -> /12."""
    total = 0.0
    for item in (sub.get("items", {}) or {}).get("data", []):
        price = item.get("price") or {}
        unit = price.get("unit_amount") or 0
        qty = item.get("quantity") or 1
        recurring = price.get("recurring") or {}
        interval = recurring.get("interval", "month")
        count = recurring.get("interval_count", 1) or 1
        monthly = (unit * qty) / 100.0
        if interval == "year":
            monthly = monthly / (12 * count)
        elif interval == "week":
            monthly = monthly * (52 / 12) / count
        elif interval == "day":
            monthly = monthly * (365 / 12) / count
        elif interval == "month":
            monthly = monthly / count
        total += monthly
    return round(total, 2)


def _cohort_of(sub: dict) -> str:
    """Signup-month cohort label.

    Stripe stamps `created` at API-call time, so freshly-seeded subscriptions all
    share one creation month. When the subscription carries a `cohort` metadata
    tag (set by stripe_seed.py as the intended signup month, e.g. "2026-04"), we
    honor it so the cohort breakdown reflects the modeled monthly cohorts. We fall
    back to the real `created` month for any subscription without the tag.
    """
    tag = (sub.get("metadata") or {}).get("cohort")
    if tag:
        return tag
    created = sub.get("created")
    if not created:
        return "unknown"
    dt = datetime.fromtimestamp(created, tz=timezone.utc)
    return f"{dt.year}-{dt.month:02d}"


def compute_metrics() -> dict:
    """Read REAL Stripe test-mode subscriptions and compute MRR/churn/cohorts."""
    # status=all so we see canceled subs (needed for churn + cohort retention).
    subs = _paginate("/subscriptions", {"status": "all", "expand[]": "data.items.data.price"})
    if not subs:
        raise SystemExit(
            "FAIL: Stripe test mode has NO subscriptions — cannot compute real "
            "MRR/churn. Seed the sandbox first: python3 scripts/stripe_seed.py"
        )

    active = [s for s in subs if s.get("status") in ("active", "trialing", "past_due")]
    canceled = [s for s in subs if s.get("status") == "canceled"]

    mrr = round(sum(_sub_monthly_amount(s) for s in active), 2)
    n_active, n_canceled = len(active), len(canceled)
    denom = n_active + n_canceled
    churn_rate = round(n_canceled / denom, 4) if denom else 0.0

    cohort_acc: dict[str, dict] = defaultdict(
        lambda: {"active": 0, "canceled": 0, "mrr": 0.0}
    )
    for s in subs:
        c = cohort_acc[_cohort_of(s)]
        if s.get("status") == "canceled":
            c["canceled"] += 1
        else:
            c["active"] += 1
            c["mrr"] = round(c["mrr"] + _sub_monthly_amount(s), 2)

    cohorts = []
    for label in sorted(cohort_acc):
        c = cohort_acc[label]
        total = c["active"] + c["canceled"]
        cohorts.append({
            "cohort": label,
            "active": c["active"],
            "canceled": c["canceled"],
            "retention": round(c["active"] / total, 4) if total else 0.0,
            "mrr": round(c["mrr"], 2),
        })

    return {
        "source": "stripe_test_mode",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "currency": "usd",
        "mrr": mrr,
        "arr": round(mrr * 12, 2),
        "active_subs": n_active,
        "canceled_subs": n_canceled,
        "churn": {
            "rate": churn_rate,
            "active": n_active,
            "canceled": n_canceled,
            "basis": "lifetime canceled / (active + canceled) over seeded subscriptions",
        },
        "cohorts": cohorts,
    }


def load_metrics(path: Path | str = OUT_PATH) -> dict:
    """Read the already-computed recordings/stripe_metrics.json (no new Stripe call).

    The GLO-14 P5 North Star joiner GROUNDS a shipped-result against real Stripe data
    by reading the artifact this client wrote — it never re-hits the API or adds a new
    Stripe surface. Raises loudly if the artifact is missing (run this client first).
    """
    p = Path(path)
    if not p.is_file():
        raise SystemExit(
            f"FAIL: {p} not found — run `python3 scripts/stripe_client.py` first to "
            "compute real test-mode MRR/churn from the live Stripe API."
        )
    return json.loads(p.read_text())


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--print", dest="show", action="store_true",
                    help="also print the computed metrics to stdout")
    args = ap.parse_args(argv)

    key = resolve_key()
    print(f"[stripe] key prefix {key[:8]}… (test-mode); reading live api.stripe.com/v1")
    metrics = compute_metrics()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(metrics, indent=2) + "\n")
    os.replace(tmp, OUT_PATH)

    print(f"[stripe] wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"[stripe] MRR=${metrics['mrr']:,.2f}/mo  ARR=${metrics['arr']:,.2f}  "
          f"active={metrics['active_subs']}  churn={metrics['churn']['rate']:.1%}  "
          f"cohorts={len(metrics['cohorts'])}")
    if args.show:
        print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
