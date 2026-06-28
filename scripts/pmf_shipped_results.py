#!/usr/bin/env python3
"""pmf_shipped_results.py — close the PMF North Star loop (GLO-14 P5 / design D-5 Option C).

Every opportunity the PMF loop ranks into `recordings/pmf_ledger.json` is born
`shipped: false`. The North Star metric is `opportunities_shipped`, so until a row
flips `false -> true` the loop never *closes* — it proposes forever and never learns
which bets actually shipped. This module closes that loop with a small, deterministic,
Stripe-GROUNDED joiner so "shipped" means a *measured real outcome*, not a manual flag.

Two pieces (the `fuse_signals.py` additive/atomic pattern):

  1. A SHIPPED-RESULT RECORD — `recordings/shipped_results.json` — one entry per
     shipped bet: the bet id it shipped, the measured metric (e.g. `mrr`/`churn`)
     and its value, and the Stripe grounding ref (`stripe_metrics.json`). This is
     the human/agent input: "we shipped bet X and here is the metric we measured."

  2. A DETERMINISTIC JOINER — `flip_shipped(ledger, results, stripe_metrics) -> int`
     — joins the shipped-result records onto the ledger by **bet id**, flips each
     matching opportunity's `shipped` from `false -> true`, and stamps its
     `grounded_in` with `"stripe_metrics.json"` (idempotently — never duplicated).
     It writes the ledger back ATOMICALLY (`os.replace`) and NEVER clobbers any other
     ledger key (mirrors `fuse_signals.py:147-152`: read whole doc, mutate only the
     target rows, write the whole doc back). Returns the number of rows flipped.

GROUNDED, not asserted. A shipped-result is only honored when its recorded metric
VALUE actually matches a value present in `recordings/stripe_metrics.json` (the real
test-mode MRR/churn/cohort figures `scripts/stripe_client.py` computes from the live
Stripe API). A record whose metric does not match real Stripe data is REFUSED — we do
not flip a North Star row on a fabricated outcome (the no-fabrication contract that
runs through `stripe_client.py` and `assert_pmf_ranked.py`).

Bet id. The ledger opportunities are identified by their stable RICE `title`; the bet
id is the title (or, equivalently, the integer `rank`). `shipped_results.json` keys on
`bet_id`, and the joiner accepts either the exact title or the `rank` so a recorded
result is unambiguous.

Usage:
  # record a shipped result for a bet (metric must match real stripe_metrics.json)
  python3 scripts/pmf_shipped_results.py record \
      --bet "<opportunity title or rank>" --metric mrr --value 1281.0
  # flip every recorded shipped result onto the ledger (atomic, grounded)
  python3 scripts/pmf_shipped_results.py flip
  python3 scripts/pmf_shipped_results.py flip --print

Exit 0 on success, non-zero on any failure (a metric that does not match real Stripe
data FAILS loudly — no silent pass, no fabricated flip).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RECORDINGS = REPO_ROOT / "recordings"
LEDGER_PATH = RECORDINGS / "pmf_ledger.json"
RESULTS_PATH = RECORDINGS / "shipped_results.json"
STRIPE_METRICS_PATH = RECORDINGS / "stripe_metrics.json"

STRIPE_REF = "stripe_metrics.json"

# Floating-point tolerance for the "metric equals a real Stripe value" cross-read.
_EPS = 1e-6


def _load_json(path: Path, what: str) -> dict:
    if not Path(path).is_file():
        raise SystemExit(f"FAIL: {what} missing at {path}.")
    try:
        return json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"FAIL: {what} at {path} is not valid JSON: {e}") from e


def _atomic_write_json(path: Path, doc) -> None:
    """Write `doc` as pretty JSON via a temp file + os.replace (fuse_signals.py pattern)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2) + "\n")
    os.replace(tmp, path)


def stripe_metric_values(stripe_metrics: dict) -> dict[str, float]:
    """The set of REAL metric values present in stripe_metrics.json, by metric name.

    These are the only values a shipped-result is allowed to claim it measured — the
    grounding cross-read. We surface the top-level scalars plus the churn rate and the
    per-cohort MRR/retention so a bet can ground in MRR, churn, or a cohort figure.
    """
    out: dict[str, float] = {}
    for k in ("mrr", "arr"):
        v = stripe_metrics.get(k)
        if isinstance(v, (int, float)):
            out[k] = float(v)
    churn = stripe_metrics.get("churn") or {}
    if isinstance(churn.get("rate"), (int, float)):
        out["churn"] = float(churn["rate"])
    if isinstance(stripe_metrics.get("active_subs"), (int, float)):
        out["active_subs"] = float(stripe_metrics["active_subs"])
    # per-cohort values (cohort_<label>_mrr / _retention) — also real Stripe figures.
    for c in stripe_metrics.get("cohorts", []) or []:
        label = c.get("cohort", "?")
        if isinstance(c.get("mrr"), (int, float)):
            out[f"cohort_{label}_mrr"] = float(c["mrr"])
        if isinstance(c.get("retention"), (int, float)):
            out[f"cohort_{label}_retention"] = float(c["retention"])
    return out


def _value_in_stripe(value: float, stripe_metrics: dict) -> bool:
    """True iff `value` equals ANY real value present in stripe_metrics.json.

    The grounding proof: a recorded shipped-result metric must be a value Stripe
    actually returned, not a hand-typed number. We compare against the full value-set
    (not just the named metric) so the check is "this is a real measured Stripe figure".
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return any(abs(v - real) <= _EPS for real in stripe_metric_values(stripe_metrics).values())


def _matches_bet(opp: dict, bet_id) -> bool:
    """Does opportunity `opp` correspond to the recorded `bet_id`?

    Accepts the exact opportunity title OR the integer rank (either is unambiguous for
    a single ledger), so a recorded result can name the bet however the operator knows it.
    """
    if isinstance(bet_id, int) or (isinstance(bet_id, str) and bet_id.isdigit()):
        return opp.get("rank") == int(bet_id)
    return opp.get("title") == bet_id


def load_results(results_path: Path = RESULTS_PATH) -> dict:
    if not Path(results_path).is_file():
        return {"generated_at": None, "results": []}
    return _load_json(results_path, "shipped_results.json")


def record_result(
    *,
    bet_id,
    metric: str,
    value: float,
    results_path: Path = RESULTS_PATH,
    stripe_metrics_path: Path = STRIPE_METRICS_PATH,
) -> dict:
    """Append/replace a shipped-result for `bet_id`, GROUNDED in real Stripe data.

    Refuses (raises) if the recorded metric value is not a value actually present in
    stripe_metrics.json — we never record a North Star outcome on a fabricated number.
    Writes shipped_results.json atomically. Returns the stored record.
    """
    stripe_metrics = _load_json(stripe_metrics_path, "stripe_metrics.json")
    if not _value_in_stripe(value, stripe_metrics):
        real = stripe_metric_values(stripe_metrics)
        raise SystemExit(
            f"REFUSED: shipped-result metric {metric}={value} is NOT a value present "
            f"in {Path(stripe_metrics_path).name} (real values: {real}). The North Star "
            "flip must be grounded in a MEASURED Stripe outcome — not a fabricated number."
        )
    doc = load_results(results_path)
    record = {
        "bet_id": bet_id,
        "metric": metric,
        "value": float(value),
        "grounded_in": STRIPE_REF,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    # replace any prior record for the same bet (idempotent re-record)
    results = [r for r in doc.get("results", []) if r.get("bet_id") != bet_id]
    results.append(record)
    doc["results"] = results
    doc["generated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_write_json(results_path, doc)
    return record


def flip_shipped(
    ledger_path: Path = LEDGER_PATH,
    results_path: Path = RESULTS_PATH,
    stripe_metrics_path: Path = STRIPE_METRICS_PATH,
) -> int:
    """Join shipped-results onto the ledger; flip matching rows false->true. Returns flips.

    Deterministic + additive + atomic (the fuse_signals.py pattern):
      - read the WHOLE ledger doc;
      - for every recorded shipped-result whose metric VALUE matches a real
        stripe_metrics.json value, find its opportunity by bet id and, if currently
        `shipped: false`, set `shipped: true` and append STRIPE_REF to `grounded_in`
        (only if absent — idempotent);
      - never touch any other ledger key or any unrelated opportunity;
      - write the WHOLE doc back atomically via os.replace.

    A recorded result whose metric does NOT match real Stripe data is REFUSED (raises)
    — we do not flip a North Star row on a fabricated outcome.
    """
    ledger = _load_json(ledger_path, "pmf_ledger.json")
    results_doc = load_results(results_path)
    results = results_doc.get("results", [])
    if not results:
        return 0
    stripe_metrics = _load_json(stripe_metrics_path, "stripe_metrics.json")

    opportunities = ledger.get("opportunities") or []
    flipped = 0
    for res in results:
        bet_id = res.get("bet_id")
        value = res.get("value")
        if not _value_in_stripe(value, stripe_metrics):
            raise SystemExit(
                f"REFUSED: recorded shipped-result for bet {bet_id!r} claims "
                f"{res.get('metric')}={value}, which is NOT present in "
                f"{Path(stripe_metrics_path).name}. Re-run scripts/stripe_client.py "
                "or fix the record — the flip must be grounded in real Stripe data."
            )
        for opp in opportunities:
            if not _matches_bet(opp, bet_id):
                continue
            if opp.get("shipped") is True:
                # already shipped — keep it idempotent (still ensure the grounding ref)
                gi = opp.setdefault("grounded_in", [])
                if STRIPE_REF not in gi:
                    gi.append(STRIPE_REF)
                continue
            opp["shipped"] = True
            gi = opp.setdefault("grounded_in", [])
            if STRIPE_REF not in gi:
                gi.append(STRIPE_REF)
            # stamp the measured outcome additively (does not disturb other keys / gates)
            opp["shipped_result"] = {
                "metric": res.get("metric"),
                "value": value,
                "grounded_in": STRIPE_REF,
                "flipped_at": datetime.now(timezone.utc).isoformat(),
            }
            flipped += 1

    if flipped:
        _atomic_write_json(ledger_path, ledger)
    return flipped


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="record a shipped-result for a bet (Stripe-grounded)")
    rec.add_argument("--bet", required=True, help="bet id: the opportunity title OR its rank")
    rec.add_argument("--metric", required=True, help="measured metric name (e.g. mrr, churn)")
    rec.add_argument("--value", required=True, type=float, help="measured value (must match real Stripe data)")
    rec.add_argument("--results", default=str(RESULTS_PATH))
    rec.add_argument("--stripe-metrics", default=str(STRIPE_METRICS_PATH))

    fl = sub.add_parser("flip", help="flip every recorded shipped-result onto the ledger (atomic)")
    fl.add_argument("--ledger", default=str(LEDGER_PATH))
    fl.add_argument("--results", default=str(RESULTS_PATH))
    fl.add_argument("--stripe-metrics", default=str(STRIPE_METRICS_PATH))
    fl.add_argument("--print", dest="show", action="store_true", help="dump the flipped ledger")

    args = ap.parse_args(argv)

    if args.cmd == "record":
        bet_id = int(args.bet) if args.bet.isdigit() else args.bet
        record = record_result(
            bet_id=bet_id,
            metric=args.metric,
            value=args.value,
            results_path=Path(args.results),
            stripe_metrics_path=Path(args.stripe_metrics),
        )
        print(f"[shipped] recorded {record['metric']}={record['value']} for bet "
              f"{record['bet_id']!r}, grounded in {record['grounded_in']}")
        return 0

    # flip
    n = flip_shipped(
        ledger_path=Path(args.ledger),
        results_path=Path(args.results),
        stripe_metrics_path=Path(args.stripe_metrics),
    )
    print(f"[shipped] flipped {n} ledger row(s) shipped false->true "
          f"(grounded in {STRIPE_REF}, atomic write)")
    if args.show and Path(args.ledger).is_file():
        print(Path(args.ledger).read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
