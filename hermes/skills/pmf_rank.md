---
name: pmf_rank
description: Rank MULTIPLE product opportunities best-first using a RICE or ICE score, after consulting prior decisions (mem0 + git history) so already-decided/rejected ideas are not re-proposed blindly. Use as the second half of the full PMF loop, after pmf_brief has produced the grounded market analysis. Each ranked opportunity carries a numeric score, a grounding union (corpus + Stripe + mem0 + git history), an optional graphify feasibility note, and a shipped-bet feedback field. Persist the ranking + feedback to a ledger (recordings/pmf_ledger.json) and surface the top-ranked opportunity as the [Product] ticket.
---

# pmf_rank

The full PMF loop does not stop at one opportunity. After `pmf_brief` produces the
grounded market analysis, this skill enumerates **multiple** candidate opportunities,
**consults prior decisions** so it does not re-propose something already decided, and
**ranks them best-first** with a transparent RICE or ICE score. The top-ranked
opportunity becomes the filed `[Product]` ticket; the whole ranking + a shipped-bet
feedback signal is persisted to a ledger.

North Star: **opportunities shipped**, not tickets filed. The ledger carries a
`shipped` flag per bet so a later run can learn from what actually shipped.

## Step 0 — Consult prior decisions FIRST (non-negotiable)

Before ranking or recommending anything, consult the two real, local records of
prior product decisions so you neither re-propose a decided/rejected idea nor lose
the rationale behind it:

1. **mem0 (self-hosted on pgvector).** Query the local mem0 backend (the
   docker-compose `mem0-postgres` service, local HuggingFace embedder) for prior
   product decisions relevant to this question:

   ```bash
   uv run scripts/mem0_pmf_decisions.py "<the PMF question>"
   ```

   This idempotently seeds the prior `[Product]` decisions that already live in git
   as tracked `tickets/` snapshots, then semantically searches them. It emits JSON
   `{mem0:{hits:[{decision_id,memory,score}]}, git:{product_tickets:[…],log:[…]}}`.
   If the backend cannot persist/retrieve, it FAILS — do not fabricate "no prior
   decisions"; bring `mem0-postgres` up (`docker compose up -d mem0-postgres`) and
   retry.

2. **git / GitHub history.** `git log` over the tracked `tickets/` decision record
   (and `gh` for issue history) is the authoritative WHY behind past calls. The
   helper above already returns the relevant commits; you may also run
   `git log --oneline -- tickets/` or `gh issue list` directly.

Render the result into a **"Prior decisions consulted"** section in the brief that
cites the mem0 hits (by `decision_id` + score) and/or the git commits. Then, for
each candidate opportunity, check it against these prior decisions:

- If an opportunity **was already decided** (e.g. a prior `[Product]` ticket already
  covers it), DO NOT re-propose it as novel. Either drop it, or — if you are
  re-raising it deliberately — **explicitly note the prior decision and what changed**
  (new market signal, new Stripe data) that justifies revisiting it.
- Prefer opportunities that are **genuinely new** relative to the prior record.

## Step 1 — Enumerate ≥2 candidate opportunities

From the brief's market signal + the capability-gap diff (what THIS product does vs.
what the market wants), name **at least two** concrete, distinct capability-gap
opportunities. Each must be a concrete capability (a thing the product cannot do
today that the market wants), not a vague theme.

## Step 2 — Score each with RICE or ICE

Use one consistent scoring model for the whole ranking. Show the inputs and the
arithmetic so the score is auditable, not asserted.

- **RICE** = (Reach × Impact × Confidence) ÷ Effort. Reach = how many users/period;
  Impact ∈ {0.25, 0.5, 1, 2, 3}; Confidence ∈ (0,1]; Effort = person-months.
- **ICE** = Impact × Confidence × Ease (each scored 1–10), reported as the product
  (or its mean). Pick ICE when reach is hard to estimate.

Ground the score inputs in evidence where you can:

- **Reach / Impact** lean on the brief's market signal and on the **real Stripe
  numbers** (`recordings/stripe_metrics.json`): MRR, churn, per-cohort retention.
  An opportunity that attacks the leg with the worst retention should score higher
  Impact, and you should say so.
- **Confidence** is lower for opportunities the prior decisions show are unproven and
  higher where there is corpus + market + revenue agreement.
- **Effort / Ease** may consult **graphify feasibility** (`graphify-out/service-coupling.json`)
  when the opportunity touches the codebase — a capability that lands on a high-degree
  coupling hub (e.g. `frontend`=7, `checkoutservice`=6) is higher-effort/lower-ease.

## Step 3 — Rank best-first and ground the union

Sort the opportunities by score **descending**. For EACH opportunity emit a
`Grounded in:` union spanning, at minimum:

- ≥1 real corpus `*.md` (the framework), and
- `stripe_metrics.json` (the Revenue/Retention evidence behind Reach/Impact),

plus, where relevant, a graphify feasibility reference and the prior-decision it was
checked against. The string `Grounded in:` MUST appear verbatim for each opportunity.

## Step 4 — Persist the ledger (shipped-bet feedback)

Write the ranking + feedback to `recordings/pmf_ledger.json` (lower-friction than
`task_runs.metadata`), one entry per opportunity, ranked:

```json
{
  "generated_at": "<iso8601>",
  "question": "<the PMF question>",
  "scoring_model": "RICE",
  "prior_decisions_consulted": {
    "mem0_hits": [{"decision_id": "GLO-12", "score": 0.31}],
    "git": ["<sha> <subject>", "..."]
  },
  "opportunities": [
    {
      "rank": 1,
      "title": "[Product] …",
      "rice_score": 42.0,
      "inputs": {"reach": 200, "impact": 2, "confidence": 0.7, "effort": 6.7},
      "grounded_in": ["the-lean-product-playbook.md", "stripe_metrics.json"],
      "graphify_feasibility": "lands on checkoutservice (degree-6 hub) — higher effort",
      "prior_decision": null,
      "shipped": false
    },
    { "rank": 2, "…": "…", "shipped": false }
  ]
}
```

`shipped` starts `false`; a later run (or a human) flips it to `true` once the bet
actually shipped — that is the feedback signal the North Star tracks. The ledger is
the cross-run memory of which bets were ranked and which shipped.

## Step 5 — File the top-ranked opportunity

The rank-1 opportunity becomes the filed `[Product]` Linear ticket (the `pmf_brief`
"turn the brief into ONE filed product opportunity" step files exactly the
top-ranked one). Its Revenue grounding ties back to Stripe, and it must NOT be one
the prior decisions already settled (unless explicitly re-raised with a what-changed
note).
