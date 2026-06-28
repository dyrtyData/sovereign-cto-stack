#!/usr/bin/env python3
"""assert_pmf_ranked.py — verify the Phase-5 full PMF loop (RICE/ICE-ranked + feedback).

Phase-5 (P4) load-bearing assertions (outline §"Automated Verification" + the
user-requested prior-decisions enhancement). The full PMF loop must:

  A. RANK ≥2 opportunities — recordings/pmf_ledger.json carries ≥2 opportunities,
     each with a NUMERIC RICE/ICE score, ranked DESCENDING (rank 1 = highest score),
     each carrying a `shipped` feedback field and a grounding union that includes a
     real corpus *.md AND stripe_metrics.json.
  B. The latest recordings/pmf_brief_*.md echoes the same ≥2 ranked, scored
     opportunities (each with a numeric score) AND each opportunity line is grounded
     in the corpus + Stripe union (Grounded in: … *.md and stripe_metrics.json).
  C. PRIOR DECISIONS CONSULTED — the brief has a non-empty "Prior decisions consulted"
     section referencing mem0 and/or git history, AND the ledger records the
     prior-decisions consult (mem0_hits and/or git). This is the enhancement: the loop
     must consult prior decisions before ranking so it does not re-propose blindly.

Exit 0 on PASS, 1 on FAIL. Exit 2 on harness error (a required input missing) — a
missing prerequisite is NEVER a silent PASS (user constraint: no graceful degradation).

Usage:
  python3 scripts/assert_pmf_ranked.py
  python3 scripts/assert_pmf_ranked.py --brief recordings/pmf_brief_run_<ts>.md \
      --ledger recordings/pmf_ledger.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / "recordings" / "pmf_ledger.json"
CORPUS_DIR = REPO_ROOT / "corpus"

GROUNDED_RE = re.compile(r"Grounded in:[^\n]*?([A-Za-z0-9_\-]+\.md)", re.IGNORECASE)
NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _latest_brief() -> Path | None:
    briefs = sorted(
        REPO_ROOT.glob("recordings/pmf_brief_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return briefs[0] if briefs else None


def _corpus_sources() -> set[str]:
    if CORPUS_DIR.is_dir():
        return {p.name.lower() for p in CORPUS_DIR.glob("*.md")}
    return set()


def _load_ledger(path: Path) -> dict:
    if not path.is_file():
        print(f"HARNESS ERROR: {path} not found — run `NO_AGENT=1 bash "
              "scripts/pmf_kanban_run.sh` to produce the ranked ledger.",
              file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError) as e:
        print(f"HARNESS ERROR: cannot parse {path}: {e}", file=sys.stderr)
        raise SystemExit(2)


def check_ledger(L: dict) -> bool:
    ok = True
    opps = L.get("opportunities") or []
    if len(opps) >= 2:
        print(f"PASS: ledger carries {len(opps)} opportunities (>=2)")
    else:
        print(f"FAIL: ledger has {len(opps)} opportunities, need >=2")
        ok = False

    model = L.get("scoring_model", "")
    if model.upper() in ("RICE", "ICE"):
        print(f"PASS: scoring model declared: {model}")
    else:
        print(f"FAIL: scoring_model is {model!r}, expected RICE or ICE")
        ok = False

    # numeric scores + ranked descending
    scores = []
    score_key = None
    for o in opps:
        sk = "rice_score" if "rice_score" in o else ("ice_score" if "ice_score" in o else None)
        if sk is None:
            print(f"FAIL: opportunity rank {o.get('rank')} has no rice_score/ice_score")
            ok = False
            continue
        score_key = sk
        s = o[sk]
        if not isinstance(s, (int, float)):
            print(f"FAIL: opportunity rank {o.get('rank')} score is non-numeric ({s!r})")
            ok = False
        else:
            scores.append(s)
    if scores and scores == sorted(scores, reverse=True):
        print(f"PASS: opportunities ranked by {score_key} descending: {scores}")
    elif scores:
        print(f"FAIL: opportunities NOT ranked descending by score: {scores}")
        ok = False

    corpus = _corpus_sources()
    # per-opportunity grounding union (corpus + stripe) + shipped feedback field
    for o in opps:
        rank = o.get("rank")
        gi = [g.lower() for g in (o.get("grounded_in") or [])]
        has_stripe = any("stripe_metrics.json" in g for g in gi)
        md_cites = [g for g in gi if g.endswith(".md")]
        real_corpus = (set(md_cites) & corpus) if corpus else set(md_cites)
        if has_stripe and md_cites and (real_corpus or not corpus):
            print(f"PASS: rank {rank} grounded in corpus+Stripe union "
                  f"({md_cites} + stripe_metrics.json)")
        else:
            print(f"FAIL: rank {rank} grounding union incomplete "
                  f"(corpus .md={md_cites}, stripe={has_stripe})")
            ok = False
        if "shipped" in o:
            print(f"PASS: rank {rank} carries a shipped feedback field "
                  f"(shipped={o['shipped']})")
        else:
            print(f"FAIL: rank {rank} has no shipped feedback field")
            ok = False
    return ok


def check_prior_decisions_ledger(L: dict) -> bool:
    pdc = L.get("prior_decisions_consulted") or {}
    mem0_hits = pdc.get("mem0_hits")
    git = pdc.get("git") or pdc.get("already_decided_ids")
    if mem0_hits is not None or git:
        print(f"PASS: ledger records prior-decisions consult "
              f"(mem0_hits={len(mem0_hits) if mem0_hits is not None else 'n/a'}, "
              f"git={'yes' if git else 'no'})")
        return True
    print("FAIL: ledger has no prior_decisions_consulted (mem0/git) record")
    return False


def check_brief(brief: Path) -> bool:
    print(f"brief artifact: {brief.relative_to(REPO_ROOT)}")
    if not brief.is_file():
        print("FAIL: brief artifact not found")
        return False
    text = brief.read_text(errors="ignore")
    low = text.lower()
    ok = True

    # Ranked opportunities section with >=2 numeric scores
    m = re.search(r"##\s*ranked opportunities.*?(?=\n##\s|\Z)", text, re.S | re.I)
    if not m:
        print("FAIL: no '## Ranked opportunities' section in the brief")
        return False
    section = m.group(0)
    # count RICE/ICE scored lines (rank entries carry a numeric score)
    scored = re.findall(r"\b(?:RICE|ICE)\s*\d+(?:\.\d+)?", section, re.I)
    if len(scored) >= 2:
        print(f"PASS: brief Ranked-opportunities section shows {len(scored)} "
              f"scored opportunities (>=2): {scored}")
    else:
        print(f"FAIL: brief shows {len(scored)} RICE/ICE-scored opportunities, need >=2")
        ok = False
    if "stripe_metrics.json" in section.lower():
        print("PASS: ranked opportunities grounded in stripe_metrics.json")
    else:
        print("FAIL: ranked opportunities not grounded in stripe_metrics.json")
        ok = False
    if GROUNDED_RE.search(section):
        print("PASS: ranked opportunities carry corpus 'Grounded in: …*.md' lines")
    else:
        print("FAIL: ranked opportunities carry no corpus 'Grounded in:' citation")
        ok = False

    # C. Prior decisions consulted section, non-empty, referencing mem0 and/or git
    pm = re.search(r"##\s*prior decisions consulted.*?(?=\n##\s|\Z)", text, re.S | re.I)
    if not pm:
        print("FAIL: no '## Prior decisions consulted' section in the brief")
        return False
    psec = pm.group(0)
    body = re.sub(r"^##\s*prior decisions consulted\s*", "", psec, flags=re.I).strip()
    if not body or len(body) < 20:
        print("FAIL: 'Prior decisions consulted' section is empty")
        ok = False
    elif ("mem0" in psec.lower()) or ("git" in psec.lower()):
        refs = []
        if "mem0" in psec.lower():
            refs.append("mem0")
        if "git" in psec.lower():
            refs.append("git history")
        print(f"PASS: 'Prior decisions consulted' is non-empty and references {refs}")
    else:
        print("FAIL: 'Prior decisions consulted' references neither mem0 nor git history")
        ok = False
    return ok


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--brief", help="brief path (default: latest recordings/pmf_brief_*.md)")
    ap.add_argument("--ledger", help="ledger path (default: recordings/pmf_ledger.json)")
    args = ap.parse_args(argv)

    ledger_path = Path(args.ledger) if args.ledger else LEDGER_PATH
    L = _load_ledger(ledger_path)

    brief = Path(args.brief) if args.brief else _latest_brief()
    if brief is None:
        print("HARNESS ERROR: no PMF brief found (run scripts/pmf_kanban_run.sh)",
              file=sys.stderr)
        return 2

    print("--- A. ledger: >=2 ranked, scored, grounded opportunities + feedback ---")
    a = check_ledger(L)
    print("--- B. brief echoes the ranked, scored, grounded opportunities ---")
    b = check_brief(brief)
    print("--- C. prior decisions consulted (mem0 + git) recorded ---")
    c = check_prior_decisions_ledger(L)

    ok = a and b and c
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
