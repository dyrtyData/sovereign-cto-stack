#!/usr/bin/env python3
"""assert_stripe_grounding.py — verify the Phase-3 Stripe-grounded AARRR brief.

Phase-3 (P2) load-bearing assertion (outline §"Automated Verification"): the
latest PMF brief's AARRR **Revenue & Retention** section is grounded in REAL
Stripe (test-mode) MRR / churn / cohort numbers from recordings/stripe_metrics.json
— not in web-scraped competitor-pricing assumptions.

Checks (all must pass):
  A. recordings/stripe_metrics.json exists, is valid, and was produced from
     Stripe test mode (source == "stripe_test_mode") with a positive MRR and a
     non-empty cohorts[] (i.e. real, not fabricated/zero data).
  B. The latest recordings/pmf_brief_*.md carries an AARRR Revenue & Retention
     section that cites stripe_metrics.json AND echoes the artifact's CONCRETE
     numbers (the integer MRR and the churn-rate percentage), proving it grounds
     in the real metrics rather than only assumption pricing.
  C. The brief emits the literal `Grounded in: stripe_metrics.json` citation line
     (the citation invariant the other gates rely on).

Exit 0 on PASS, 1 on FAIL. Exit 2 on harness error (artifact missing) so a
missing prerequisite is never a silent PASS.

Usage:
  python3 scripts/assert_stripe_grounding.py
  python3 scripts/assert_stripe_grounding.py --brief recordings/pmf_brief_run_<ts>.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_PATH = REPO_ROOT / "recordings" / "stripe_metrics.json"


def _latest_brief() -> Path | None:
    briefs = sorted(
        REPO_ROOT.glob("recordings/pmf_brief_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return briefs[0] if briefs else None


def _load_metrics() -> dict:
    if not METRICS_PATH.is_file():
        print(f"HARNESS ERROR: {METRICS_PATH.relative_to(REPO_ROOT)} not found — "
              "run `python3 scripts/stripe_client.py` (seed first with "
              "`python3 scripts/stripe_seed.py`).", file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(METRICS_PATH.read_text())
    except (ValueError, OSError) as e:
        print(f"HARNESS ERROR: cannot parse {METRICS_PATH}: {e}", file=sys.stderr)
        raise SystemExit(2)


def check_metrics(m: dict) -> bool:
    ok = True
    if m.get("source") != "stripe_test_mode":
        print(f"FAIL: metrics source is {m.get('source')!r}, expected 'stripe_test_mode'")
        ok = False
    else:
        print("PASS: metrics sourced from Stripe test mode")
    mrr = m.get("mrr")
    if isinstance(mrr, (int, float)) and mrr > 0:
        print(f"PASS: real MRR present (${mrr:,.2f}/mo)")
    else:
        print(f"FAIL: MRR missing or non-positive ({mrr!r}) — not real data")
        ok = False
    cohorts = m.get("cohorts") or []
    if cohorts:
        print(f"PASS: {len(cohorts)} cohort(s) present "
              f"({', '.join(c.get('cohort','?') for c in cohorts)})")
    else:
        print("FAIL: no cohorts[] in metrics")
        ok = False
    churn = (m.get("churn") or {}).get("rate")
    if isinstance(churn, (int, float)):
        print(f"PASS: churn rate present ({churn:.1%})")
    else:
        print(f"FAIL: churn rate missing ({churn!r})")
        ok = False
    return ok


def check_brief(brief: Path, m: dict) -> bool:
    print(f"brief artifact: {brief.relative_to(REPO_ROOT)}")
    if not brief.is_file():
        print("FAIL: brief artifact not found")
        return False
    text = brief.read_text(errors="ignore")
    low = text.lower()
    ok = True

    # C. literal citation line
    if re.search(r"grounded in:\s*stripe_metrics\.json", low):
        print("PASS: brief carries `Grounded in: stripe_metrics.json` citation")
    else:
        print("FAIL: no `Grounded in: stripe_metrics.json` citation line")
        ok = False

    # An AARRR Revenue/Retention section is named
    if re.search(r"revenue\s*&?\s*retention|aarrr", low):
        print("PASS: brief has an AARRR Revenue/Retention section")
    else:
        print("FAIL: no AARRR Revenue/Retention section heading in the brief")
        ok = False

    # B. the brief echoes the artifact's CONCRETE numbers (not just any pricing).
    mrr = m.get("mrr") or 0
    mrr_int = int(round(mrr))
    # accept "1281" or "1,281"
    mrr_pat = re.compile(rf"\b{mrr_int:,}\b|\b{mrr_int}\b")
    if mrr_pat.search(text):
        print(f"PASS: brief echoes the real MRR figure ({mrr_int})")
    else:
        print(f"FAIL: brief does not cite the real MRR figure ({mrr_int}) from "
              "stripe_metrics.json (Revenue grounded in assumptions, not Stripe)")
        ok = False

    churn_rate = (m.get("churn") or {}).get("rate") or 0
    churn_pct = round(churn_rate * 100)
    # accept "25%" or "25 %" or "0.25"
    if re.search(rf"\b{churn_pct}\s*%", text) or re.search(rf"\b{churn_rate}\b", text):
        print(f"PASS: brief echoes the real churn figure ({churn_pct}%)")
    else:
        print(f"FAIL: brief does not cite the real churn figure ({churn_pct}%) "
              "from stripe_metrics.json")
        ok = False

    return ok


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--brief", help="brief path (default: latest recordings/pmf_brief_*.md)")
    args = ap.parse_args(argv)

    m = _load_metrics()
    brief = Path(args.brief) if args.brief else _latest_brief()
    if brief is None:
        print("HARNESS ERROR: no PMF brief found (run scripts/pmf_kanban_run.sh)",
              file=sys.stderr)
        return 2

    print("--- A. Stripe metrics artifact is real test-mode data ---")
    a = check_metrics(m)
    print("--- B/C. brief Revenue/Retention grounded in Stripe metrics ---")
    b = check_brief(brief, m)

    print("RESULT:", "PASS" if (a and b) else "FAIL")
    return 0 if (a and b) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
