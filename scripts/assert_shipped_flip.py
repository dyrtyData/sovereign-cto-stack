#!/usr/bin/env python3
"""assert_shipped_flip.py — the GLO-14 P5 North Star gate (Stripe-grounded flip).

The falsifiable exit-0 contract for "a recorded, Stripe-grounded shipped-result flips
a `pmf_ledger.json` row `shipped: false -> true`" (design D-5 Option C). It proves the
North Star loop *closes* on a MEASURED real outcome, not a hand-set flag, scripted
(nothing eyeballed):

  1. SEED a `shipped_results.json` for ONE known bet — the ledger's rank-1 opportunity
     — with a metric whose value is read directly OUT of the real
     `recordings/stripe_metrics.json` (so the recorded outcome is, by construction, a
     real measured Stripe figure).
  2. RUN the deterministic joiner `pmf_shipped_results.flip_shipped`.
  3. ASSERT, against the resulting ledger:
       a. the target bet's `shipped` is now `true`;
       b. its `grounded_in` cites `stripe_metrics.json`;
       c. the recorded metric value EQUALS a value actually present in
          `stripe_metrics.json` (the MRR/churn cross-read — "measured real outcome");
       d. every UNRELATED opportunity stays `shipped: false` (the flip is surgical);
       e. all other ledger keys (question, scoring_model, prior_decisions_consulted,
          the unrelated opportunities' fields) are preserved byte-for-byte.

ISOLATION (mirrors `assert_memory_accumulates.py`'s throwaway collection). The gate
copies the REAL `pmf_ledger.json` into a throwaway temp dir and operates ONLY on that
copy — it never mutates the tracked `recordings/pmf_ledger.json` (which stays all-false)
or the tracked `recordings/stripe_metrics.json` (read-only). So the gate is deterministic,
repeatable, and leaves the working tree clean.

Exit 0 on PASS, 1 on assertion FAIL, 2 on harness error (a required input missing —
NEVER a silent pass; user constraint: no graceful degradation of a real failure).

Usage:
    uv run scripts/assert_shipped_flip.py
    python3 scripts/assert_shipped_flip.py
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

LEDGER_PATH = REPO_ROOT / "recordings" / "pmf_ledger.json"
STRIPE_METRICS_PATH = REPO_ROOT / "recordings" / "stripe_metrics.json"

import pmf_shipped_results as J  # noqa: E402  (after sys.path insert)


def _load(path: Path, what: str) -> dict:
    if not path.is_file():
        print(f"HARNESS ERROR: {what} missing at {path}. Run "
              "`NO_AGENT=1 bash scripts/pmf_kanban_run.sh` (ledger) / "
              "`python3 scripts/stripe_client.py` (stripe).", file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError) as e:
        print(f"HARNESS ERROR: cannot parse {what} at {path}: {e}", file=sys.stderr)
        raise SystemExit(2)


def main() -> int:
    ledger = _load(LEDGER_PATH, "pmf_ledger.json")
    stripe_metrics = _load(STRIPE_METRICS_PATH, "stripe_metrics.json")

    opps = ledger.get("opportunities") or []
    if len(opps) < 2:
        print(f"HARNESS ERROR: ledger needs >=2 opportunities to prove a surgical "
              f"flip (has {len(opps)}).", file=sys.stderr)
        return 2

    # The target bet = the rank-1 opportunity (identified by its stable title).
    target = next((o for o in opps if o.get("rank") == 1), opps[0])
    target_title = target.get("title")

    # A real measured value to ground the shipped-result in: take MRR straight out of
    # the real stripe_metrics.json (so the recorded outcome is, by construction, a value
    # that IS present in Stripe — the cross-read the gate then re-proves independently).
    real_values = J.stripe_metric_values(stripe_metrics)
    if "mrr" not in real_values:
        print("HARNESS ERROR: stripe_metrics.json has no MRR to ground the flip.",
              file=sys.stderr)
        return 2
    measured_metric = "mrr"
    measured_value = real_values["mrr"]

    ok = True
    with tempfile.TemporaryDirectory(prefix="shipflip_") as td:
        tmp = Path(td)
        tmp_ledger = tmp / "pmf_ledger.json"
        tmp_results = tmp / "shipped_results.json"
        # Isolated copy of the REAL ledger — we mutate ONLY this copy.
        tmp_ledger.write_text(json.dumps(ledger, indent=2) + "\n")
        before = copy.deepcopy(ledger)

        # 1. seed a shipped-result for the target bet, grounded in the real Stripe value.
        record = J.record_result(
            bet_id=target_title,
            metric=measured_metric,
            value=measured_value,
            results_path=tmp_results,
            stripe_metrics_path=STRIPE_METRICS_PATH,
        )
        print(f"[gate]  seeded shipped-result: bet={target_title!r} "
              f"{record['metric']}={record['value']} grounded_in={record['grounded_in']}")

        # 2. run the deterministic joiner on the isolated copy.
        flipped = J.flip_shipped(
            ledger_path=tmp_ledger,
            results_path=tmp_results,
            stripe_metrics_path=STRIPE_METRICS_PATH,
        )
        print(f"[gate]  flip_shipped returned {flipped}")
        after = json.loads(tmp_ledger.read_text())

    after_opps = after.get("opportunities") or []
    after_target = next((o for o in after_opps if o.get("title") == target_title), None)

    # a. target bet flipped to shipped:true
    if after_target and after_target.get("shipped") is True:
        print(f"PASS: target bet shipped flipped false->true ({target_title!r})")
    else:
        print(f"FAIL: target bet shipped is {after_target and after_target.get('shipped')!r}, "
              "expected true")
        ok = False
    if flipped != 1:
        print(f"FAIL: flip_shipped flipped {flipped} rows, expected exactly 1 "
              "(only the seeded bet)")
        ok = False
    else:
        print("PASS: flip_shipped flipped exactly 1 row")

    # b. grounded_in cites stripe_metrics.json
    gi = (after_target or {}).get("grounded_in") or []
    if J.STRIPE_REF in gi:
        print(f"PASS: target bet grounded_in cites {J.STRIPE_REF} ({gi})")
    else:
        print(f"FAIL: target bet grounded_in does NOT cite {J.STRIPE_REF} ({gi})")
        ok = False

    # c. the recorded metric value EQUALS a real stripe_metrics.json value (cross-read)
    sr = (after_target or {}).get("shipped_result") or {}
    recorded_value = sr.get("value")
    if J._value_in_stripe(recorded_value, stripe_metrics):
        print(f"PASS: recorded metric {sr.get('metric')}={recorded_value} equals a REAL "
              f"value present in {J.STRIPE_REF} (measured real outcome)")
    else:
        print(f"FAIL: recorded metric value {recorded_value!r} is NOT present in "
              f"{J.STRIPE_REF} — the flip would not be a measured outcome")
        ok = False

    # d. every UNRELATED opportunity stays shipped:false
    unrelated = [o for o in after_opps if o.get("title") != target_title]
    still_false = [o for o in unrelated if o.get("shipped") is False]
    if len(still_false) == len(unrelated) and unrelated:
        print(f"PASS: all {len(unrelated)} unrelated opportunities stayed shipped:false")
    else:
        flipped_others = [o.get("title") for o in unrelated if o.get("shipped") is not False]
        print(f"FAIL: unrelated opportunities changed shipped state: {flipped_others}")
        ok = False

    # e. all other ledger keys preserved (only opportunities[].shipped/grounded_in/
    #    shipped_result on the target may differ).
    preserved_keys = [k for k in before if k != "opportunities"]
    keys_ok = True
    for k in preserved_keys:
        if before.get(k) != after.get(k):
            print(f"FAIL: top-level ledger key {k!r} was modified by the flip")
            keys_ok = False
            ok = False
    if keys_ok:
        print(f"PASS: all top-level ledger keys preserved ({preserved_keys})")
    # unrelated opportunities preserved byte-for-byte
    before_unrelated = {o.get("title"): o for o in (before.get("opportunities") or [])
                        if o.get("title") != target_title}
    after_unrelated = {o.get("title"): o for o in unrelated}
    if before_unrelated == after_unrelated:
        print("PASS: unrelated opportunity rows preserved byte-for-byte")
    else:
        print("FAIL: an unrelated opportunity row was modified by the flip")
        ok = False

    # isolation: the REAL tracked ledger is untouched (still all-false)
    real_now = _load(LEDGER_PATH, "pmf_ledger.json")
    if any(o.get("shipped") is True for o in real_now.get("opportunities") or []):
        print("FAIL: the REAL recordings/pmf_ledger.json was mutated (isolation broken)")
        ok = False
    else:
        print("PASS: the real recordings/pmf_ledger.json is untouched (isolated temp copy)")

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
