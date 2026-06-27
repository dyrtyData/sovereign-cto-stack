---
name: pmf_brief
description: Produce a textbook-grounded product-market-fit (PMF) / growth strategic brief AND file ONE market-informed [Product] opportunity ticket in Linear. Use when given a product or market question. Scrape the web for current signal, cross-reference query_cto_knowledge (growth/PMF texts) by multi-angle querying, write a concise brief that cites the union of grounding texts, then scan what THIS product offers, diff it against the market findings, pick ONE concrete product-gap opportunity, and file ONE HumanLayer-ready [Product] Linear ticket grounded in a market URL + a RAG citation union. Save the brief to recordings/ or workspaces/ and hand off via kanban_complete with a summary + metadata.
---

# pmf_brief

Take a product/market question, research it on the open web, ground it in the CTO
growth/PMF corpus by **multi-angle querying**, emit a concise **strategic brief**
that cites the union of the grounding texts, write the brief to a file, and hand
off the result on the shared Kanban board via `kanban_complete()`.

A brief is "good" when a founder/CTO could read it and know: who the target
customer is, what the market is actually doing (cited web signal), what the
frameworks say about it (cited corpus texts), the recommendation, and the riskiest
assumption to test next.

## Hard preconditions (do these first — non-negotiable)

1. **Scrape the web.** Use the browser/web search tools in this session to gather
   current, concrete signal about the product/market question — competitors,
   demand signals, pricing, customer language. Keep the sources (URLs) so you can
   cite them. (For the recorded run the browser is rendered on the virtual display
   so the scrape is visible; do not skip it.)

2. **Ground it in the corpus by MULTI-ANGLE querying (design Q5).** A real PMF
   question has several dimensions; one query phrased one way only surfaces one
   slice of the corpus and under-cites. BEFORE writing the brief you MUST
   **decompose the question into its distinct dimensions and issue a separate
   `query_cto_knowledge` call for each** — at minimum these four angles:

   - **problem / solution fit** — e.g. `query_cto_knowledge(query="problem solution fit value proposition target customer", k=5)`
   - **target customer & market sizing** — e.g. `query_cto_knowledge(query="market sizing segmentation target customer underserved needs", k=5)`
   - **experimentation / validated learning** — e.g. `query_cto_knowledge(query="hypothesis experiment minimum viable product validated learning A/B test", k=5)`
   - **growth loops / acquisition** — e.g. `query_cto_knowledge(query="growth loops acquisition retention north star metric", k=5)`

   Add more angles if the question has more dimensions (e.g. pricing, retention,
   distribution). Read every returned passage.

   Then **cite the UNION of distinct `source_file`s your queries returned that
   support the brief** — let retrieval decide which texts are relevant; never
   pre-curate or guess a title list. A multi-angle PMF query typically returns
   (among others) `the-lean-product-playbook.md`, `hacking-growth.md`,
   `lean-enterprise.md`, and `trustworthy-online-controlled-experiments.md` — but
   cite what YOUR queries actually return, not this list. If the corpus returns
   nothing relevant for a given angle, say so for that angle — do not invent
   grounding.

## Write the brief to a file

Write the brief as Markdown to a path the recorder/verifier can read back. Prefer:

```text
recordings/pmf_brief_<slug>_<timestamp>.md      # alongside the run capture
```

(fall back to `workspaces/pmf_brief_<timestamp>.md` if `recordings/` is not
writable). Save the path — you will return it in the handoff metadata.

## Required brief body shape

The brief MUST contain, in order:

1. **Question & target customer** — the product/market question and who it's for.
2. **Market signal (web)** — what the market is actually doing, with the source
   URLs you scraped. Concrete, not hand-wavy.
3. **Framework analysis** — apply the corpus frameworks to interpret the signal
   (problem/solution fit, sizing, experimentation, growth).
4. **Grounding** — for **every distinct `source_file` your multi-angle queries
   returned that supports the brief**, a literal line
   `Grounded in: <source_file> (<what THIS text backs>)` tying that source to the
   dimension it grounds. Cite the union — never pre-curate or guess. The string
   `Grounded in:` MUST appear verbatim, once per cited source. At least one cited
   `source_file` must be a real corpus `*.md` (e.g. `the-lean-product-playbook.md`).
5. **Recommendation** — a clear call.
6. **Riskiest assumption to test next** — the single experiment to run.

### Template

```markdown
# PMF Brief — <product/market question>

## Question & target customer
<the question> for <target customer / segment>.

## Market signal (web)
- <signal 1> — <source URL>
- <signal 2> — <source URL>

## Framework analysis
<2–4 paragraphs interpreting the signal through the corpus frameworks:
problem/solution fit, market sizing, experimentation, growth loops>

## Grounded in
(one line per distinct source_file the multi-angle queries returned — cite the union)
Grounded in: the-lean-product-playbook.md (Product-Market Fit Pyramid — target
customer → underserved needs → value proposition → feature set → UX).
Grounded in: hacking-growth.md (the growth loop / north-star metric and the
experiment cadence that compounds acquisition).
Grounded in: lean-enterprise.md (validated learning and build-measure-learn under
uncertainty).
Grounded in: trustworthy-online-controlled-experiments.md (designing trustworthy
A/B tests to validate the riskiest assumption).

## Recommendation
<the call>

## Riskiest assumption to test next
<the single experiment / hypothesis>
```

## Then turn the brief into ONE filed product opportunity (THIN loop — do this every run)

A brief that no one acts on is inert. After the brief is written, close the loop
into a single, concrete, **HumanLayer-ready `[Product]` Linear ticket**. Keep it
THIN: exactly **one** opportunity, **one** ticket, deterministic enough to verify.

1. **Scan what THIS product currently offers.** Read the repo to learn the current
   capability surface — at minimum `README.md`, `AGENTS.md`, `docs/*` (e.g.
   `docs/setup-guide.md`, `docs/system-design-tradeoffs.md`), and the skills under
   `hermes/skills/*` (the agent's actual capabilities, e.g. `file_brownfield_ticket`,
   `pmf_brief`). Summarize in one or two sentences what the product does today.

2. **Diff current offering against the market/competitor findings in the brief.**
   What are competitors / the market doing (from the web signal you scraped) that
   THIS product does NOT yet do? Name the single sharpest gap.

3. **Pick ONE concrete, market-informed product-gap opportunity.** It must name a
   **concrete capability gap** (a thing the product cannot do today that the market
   wants) — not a vague theme. State it as: *"Today the product does X; the market
   wants Y; the gap is the capability Z."*

4. **File ONE `[Product]` Linear ticket** via the `save_issue` MCP tool, reusing the
   same field shape as `file_brownfield_ticket` (the server uses `team`/`labels`,
   the human forms of GraphQL `teamId`/`labelIds`):

   | Field | Value |
   |---|---|
   | `title` | **Must start with `[Product]`**, then the one-line opportunity, e.g. `[Product] PMF agent emits a brief but cannot rank opportunities by market size — add a TAM/SAM sizing step` |
   | `team` | `Global South Ai Safety` (or team id `132f84d7-56c2-40b8-b271-52f934307ff6`) |
   | `labels` | `["Product"]` — the `Product` label (already created in the workspace; `save_issue` resolves the name to its id). If for any reason the label cannot attach, KEEP the `[Product]` title prefix as the marker. |
   | `priority` | `2` (High) for a clear, demanded gap; `3` (Medium) otherwise. |
   | `description` | Markdown, the body shape below. Literal newlines, not escapes. |

   **Required `[Product]` `description` body shape (in order):**

   1. **Current offering** — one or two sentences on what the product does today
      (from your repo scan), naming a concrete artifact you read
      (e.g. `hermes/skills/pmf_brief.md`).
   2. **Market signal** — what the market/competitors are doing, with **at least one
      concrete market source URL** (`https://…`) from your web scrape. The string
      `https://` MUST appear in the ticket body.
   3. **The gap (concrete capability)** — the single capability the product lacks
      that the market wants. Be specific: name the capability.
   4. **Proposed opportunity (first step)** — a concrete, scoped first step to close
      the gap (not "consider exploring").
   5. **Grounding** — one `Grounded in: <source_file> (<what THIS text backs>)` line
      per **distinct corpus `source_file` your multi-angle queries returned** that
      supports the opportunity. Cite the UNION — never pre-curate. The string
      `Grounded in:` MUST appear verbatim, at least one citing a real corpus `*.md`.
   6. **Acceptance criteria** — a short checklist so it is actionable as-is.

5. **Confirm by reading the ticket back** (`list_issues(query="[Product]", team=...)`
   or `get_issue`): verify the `Product` label (or the `[Product]` title marker), a
   concrete capability gap, a market `https://` URL, and a `Grounded in:` line.
   Report the issue identifier/URL.

A `[Product]` ticket is "HumanLayer-ready" when a human (or a HumanLayer worktree
agent) could pick it up and build the capability without asking follow-up
questions: it states what exists today, the market gap, the scoped first step, the
grounding, and acceptance criteria.

## Hand off via the Kanban board (kanban_complete)

This profile coordinates with the orchestrator over the shared single-host Kanban
board (`~/.hermes/kanban.db`, design Q4). When the brief is written, **close the
task with a structured handoff** so the orchestrator and downstream tasks can read
the result without re-doing the work:

```text
kanban_complete(
  task_id=<the task you claimed>,
  summary="PMF brief for <question>: <one-line recommendation>. Grounded in <N> corpus texts.",
  metadata={
    "artifact": "recordings/pmf_brief_<slug>_<ts>.md",
    "grounded_in": ["the-lean-product-playbook.md", "hacking-growth.md", ...],
    "recommendation": "<the call>",
    "riskiest_assumption": "<the experiment>"
  }
)
```

If you are running this skill outside a claimed Kanban task (e.g. a one-shot
`-z` run), still write the brief file and print the same summary + metadata as JSON
so the recorder/verifier can read the handoff; the operator/script will record the
matching Kanban row.

## After filing

1. Confirm the brief file exists and contains at least one `Grounded in:` line
   citing a real corpus `*.md`.
2. **Persist the `[Product]` ticket into git (decision record).** Git history is the
   authoritative record of every CTO decision (design "Desired End State"), so snapshot
   the ticket you just filed into the tracked `tickets/<ID>.md`:
   ```bash
   python3 scripts/snapshot_tickets.py <THE_ID>     # e.g. GLO-13
   # or, to refresh every agent-filed ticket: bash scripts/snapshot_after_run.sh
   ```
   Then the operator reviews and commits `tickets/`. (Cron/recorded runs call
   `scripts/snapshot_after_run.sh` automatically as a post-step.)
3. Report the brief path, the cited sources, and the one-line recommendation;
   deliver to Telegram if a delivery target is configured.
