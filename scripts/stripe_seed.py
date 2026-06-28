#!/usr/bin/env python3
"""stripe_seed.py — seed a Stripe TEST-mode sandbox with real customers /
subscriptions / invoices across ~3 monthly cohorts (some churned) so that
genuine MRR / churn / cohort metrics can be computed by stripe_client.py.

A fresh Stripe sandbox is empty, so there is no real MRR/churn to read. This
script creates real objects in Stripe test mode via the live REST API
(api.stripe.com/v1) — no third-party SDK, stdlib only — following the
scripts/linear_mcp.py reference-client pattern (key resolution -> urllib POST).

NO GRACEFUL DEGRADATION / NO FABRICATION:
- The key is read from $STRIPE_API_KEY (or .env). If absent, this FAILS loudly.
- TEST-KEY-ONLY GUARD: the key MUST start with `sk_test_` or `rk_test_`. If it
  looks like a LIVE key (`sk_live_`/`rk_live_`) the script REFUSES and stops —
  we never create real billing objects against a live account.

Idempotency: every object created here is tagged with metadata
`{"seed":"sovereign-cto-stack"}`. On re-run, if customers already carry that tag
the script SKIPS creation (it will not duplicate the cohort on repeated runs).

Usage:
  python3 scripts/stripe_seed.py            # seed (idempotent-ish)
  python3 scripts/stripe_seed.py --force    # seed even if a prior seed exists

Exit 0 on success, non-zero on any failure (no silent pass).
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Shared Stripe REST helpers (key resolution, TEST-key guard, request) live in
# stripe_client.py so the client and the seeder agree on exactly one code path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stripe_client as S  # noqa: E402

SEED_TAG = "sovereign-cto-stack"

# Three monthly price points (in cents) on a synthetic SaaS product. Real Stripe
# Price objects are created once and reused across cohorts.
PLANS = [
    ("Starter", 2900),    # $29/mo
    ("Team", 9900),       # $99/mo
    ("Business", 29900),  # $299/mo
]

# Cohort layout: (months_ago, n_customers, plan_index, n_to_cancel).
# Older cohorts have churned (canceled) subscriptions so churn is real.
COHORTS = [
    (2, 5, 0, 2),  # 2 months ago: 5 Starter, 2 later canceled
    (1, 4, 1, 1),  # 1 month ago: 4 Team, 1 later canceled
    (0, 3, 2, 0),  # this month: 3 Business, none canceled yet
]


def _already_seeded() -> bool:
    """True if any customer already carries the seed metadata tag.

    Paginates the full customer list (Stripe caps `limit` at 100 and signals more
    pages via `has_more`/`starting_after`). A single first-page scan would miss an
    existing tagged customer once the account holds >100 customers (repeated --force
    runs, a shared account), and silently duplicate the cohorts.
    """
    starting_after = None
    while True:
        params: dict = {"limit": 100}
        if starting_after:
            params["starting_after"] = starting_after
        res = S.api("GET", "/customers", params)
        data = res.get("data", [])
        for c in data:
            if (c.get("metadata") or {}).get("seed") == SEED_TAG:
                return True
        if not res.get("has_more") or not data:
            return False
        starting_after = data[-1]["id"]


def _ensure_price(name: str, amount: int) -> str:
    """Create-or-reuse a recurring monthly Price (idempotent via lookup_key)."""
    lookup = f"sovctostack_{name.lower()}_{amount}"
    existing = S.api("GET", "/prices", {"lookup_keys[]": lookup, "limit": 1})
    data = existing.get("data", [])
    if data:
        return data[0]["id"]
    price = S.api(
        "POST",
        "/prices",
        {
            "unit_amount": amount,
            "currency": "usd",
            "recurring[interval]": "month",
            "lookup_key": lookup,
            "transfer_lookup_key": "true",
            "product_data[name]": f"Sovereign CTO Stack — {name}",
            "metadata[seed]": SEED_TAG,
        },
    )
    return price["id"]


def _create_customer(email: str, cohort_label: str) -> str:
    cust = S.api(
        "POST",
        "/customers",
        {
            "email": email,
            "description": f"Seed customer ({cohort_label})",
            "metadata[seed]": SEED_TAG,
            "metadata[cohort]": cohort_label,
            # Stripe test-mode token for a card that always succeeds.
            "payment_method": "pm_card_visa",
            "invoice_settings[default_payment_method]": "pm_card_visa",
        },
    )
    return cust["id"]


def _create_subscription(customer_id: str, price_id: str, cohort_label: str) -> str:
    sub = S.api(
        "POST",
        "/subscriptions",
        {
            "customer": customer_id,
            "items[0][price]": price_id,
            "metadata[seed]": SEED_TAG,
            "metadata[cohort]": cohort_label,
        },
    )
    return sub["id"]


def _cohort_label(months_ago: int) -> str:
    now = datetime.now(timezone.utc)
    # naive month arithmetic, good enough for a cohort label
    month = now.month - months_ago
    year = now.year
    while month <= 0:
        month += 12
        year -= 1
    return f"{year}-{month:02d}"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="seed even if a prior seed tag is detected")
    args = ap.parse_args(argv)

    # Resolves the key AND enforces the TEST-key guard (refuses sk_live_).
    key = S.resolve_key()
    print(f"[seed] using Stripe key prefix: {key[:8]}… (test-mode enforced)")

    if not args.force and _already_seeded():
        print("[seed] sandbox already carries the 'sovereign-cto-stack' seed tag — "
              "skipping (use --force to add another cohort batch).")
        return 0

    price_ids = [_ensure_price(name, amt) for name, amt in PLANS]
    print(f"[seed] prices ready: {dict(zip([p[0] for p in PLANS], price_ids))}")

    total_subs = 0
    total_canceled = 0
    for months_ago, n_customers, plan_idx, n_cancel in COHORTS:
        label = _cohort_label(months_ago)
        price_id = price_ids[plan_idx]
        sub_ids: list[str] = []
        for i in range(n_customers):
            email = f"seed+{label}-{i}-{int(time.time())}@example.com"
            cid = _create_customer(email, label)
            sid = _create_subscription(cid, price_id, label)
            sub_ids.append(sid)
            total_subs += 1
        # cancel the churned subset of this cohort
        for sid in sub_ids[:n_cancel]:
            S.api("DELETE", f"/subscriptions/{sid}", {})
            total_canceled += 1
        print(f"[seed] cohort {label}: +{n_customers} subs "
              f"({PLANS[plan_idx][0]}), {n_cancel} canceled")

    print(f"[seed] DONE — created {total_subs} subscriptions "
          f"({total_canceled} canceled) across {len(COHORTS)} cohorts.")
    print("[seed] now run: python3 scripts/stripe_client.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
