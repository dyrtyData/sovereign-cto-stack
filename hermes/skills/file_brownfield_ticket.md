---
name: file_brownfield_ticket
description: File a HumanLayer-ready [Brownfield] tech-debt ticket in Linear. Use after auditing a codebase with graphify + query_cto_knowledge, when you have a concrete coupling/refactor finding that names exact src/<service>/ files and is grounded in a cited corpus text. Encodes the [Brownfield] label and the Linear save_issue field shape.
---

# file_brownfield_ticket

Wrap the Linear `save_issue` MCP tool to file a **HumanLayer-ready** `[Brownfield]`
tech-debt ticket. A ticket is "HumanLayer-ready" when a human (or a HumanLayer
worktree agent) could pick it up and act on it **without asking any follow-up
questions**: it names the exact files, states the measured signal, gives the
refactor rationale, and cites the grounding text.

## Two fused signals (Phase 4 P3): graphify COUPLING + SonarQube QUALITY

The tech-debt loop fuses **two complementary static signals** and you are the
**JUDGMENT/curation layer** between them:

- **graphify (KEEP)** — cross-service gRPC **coupling** topology (frontend=7,
  checkoutservice=6 outbound edges). SonarQube has no coupling metric; graphify
  is kept for exactly this.
- **SonarQube (DETECT)** — code **quality** issues/measures (bugs, code smells,
  vulnerabilities, complexity) from a REAL scan. `scripts/sonarqube_client.py`
  writes `graphify-out/sonar-issues.json`; `scripts/fuse_signals.py` merges it
  onto `graphify-out/service-coupling.json` under a top-level `static_analysis`
  key (with a per-service fusion view, a `billing_path` flag, and an
  `exemplar_issue` already selected on the priority surface).

Your ticket MUST cite **BOTH** signals: a concrete **SonarQube issue key** AND a
graphify **coupling** path. You also **prioritize the billing path**
(cart/checkout/payment/currency = the priority surface — the P2 secondary audit
folded into P3) and **name a remediation back-end** (see below).

## Hard preconditions (do these first — non-negotiable)

1. **Read BOTH fused signals.** Read `graphify-out/service-coupling.json`
   (service-level coupling AND its `static_analysis` block) and
   `graphify-out/sonar-issues.json` (the real SonarQube issues/measures).
   Identify the coupling hotspot — for Online Boutique the hubs are `frontend`
   (7 outbound gRPC edges) and `checkoutservice` (6) — and the SonarQube
   `static_analysis.exemplar_issue` (already chosen on the billing path / a hub,
   in a real `src/<service>/` source file). Prefer the service where the two
   signals **overlap** (e.g. `checkoutservice`: a billing-path coupling hub that
   also carries SonarQube issues) so a single finding is grounded in both.
2. **Ground it in the corpus by MULTI-ANGLE querying (design Q5).** A real
   architecture finding has several dimensions; one query phrased one way will only
   surface one slice of the corpus and under-cite. BEFORE writing the ticket, you
   MUST **decompose the finding into its distinct dimensions and issue a separate
   `query_cto_knowledge` call for each** — at minimum these four angles:

   - **coupling** — e.g. `query_cto_knowledge(query="service coupling efferent afferent change amplification", k=5)`
   - **technical-debt economics / interest** — e.g. `query_cto_knowledge(query="technical debt friction interest remediation cost", k=5)`
   - **service decomposition & granularity tradeoffs** — e.g. `query_cto_knowledge(query="service decomposition granularity bounded context tradeoffs", k=5)`
   - **delivery / throughput performance** — e.g. `query_cto_knowledge(query="delivery throughput deployment performance loosely coupled", k=5)`

   Add more angles if the finding has more dimensions (e.g. data ownership,
   resilience). Read every returned passage.

   Then **cite the UNION of distinct `source_file`s your queries returned that
   support the finding** — let retrieval decide which texts are relevant; never
   pre-curate or guess a title list. A multi-angle audit of an Online Boutique
   coupling hub typically returns (among others) `software-architecture.md`,
   `managing-technical-debt.md`, `balancing-coupling-in-software-design.md`,
   `sam-newman-building-microservices.md`, `strategic-monoliths-and-microservices.md`,
   and `accelerate.md` — but cite what YOUR queries actually return, not this list.
   If the corpus returns nothing relevant for a given angle, say so for that
   angle — do not invent grounding.

## The Linear `save_issue` call

The Linear MCP server (`mcp_linear_save_issue`) normalizes Linear's GraphQL
`IssueCreateInput`. The fields you set (note: the server uses `team`/`labels`,
the human-readable forms of GraphQL's `teamId`/`labelIds`):

| Field | Value |
|---|---|
| `title` | **Must start with `[Brownfield]`**, then a one-line finding, e.g. `[Brownfield] frontend is a 7-service gRPC coupling hub — extract a backend-for-frontend boundary` |
| `team` | `Global South Ai Safety` (the workspace's team; also accepts the team ID `132f84d7-56c2-40b8-b271-52f934307ff6`) |
| `labels` | `["Brownfield"]` — attaches the `Brownfield` label (already created in the workspace). `save_issue` resolves label names to IDs. |
| `priority` | `2` (High) for a coupling hub; `3` (Medium) otherwise. (0=None,1=Urgent,2=High,3=Medium,4=Low) |
| `description` | Markdown, the body shape below. Use literal newlines, not escapes. |

## Required `description` body shape

The description MUST contain, in order:

1. **Finding** — the coupling hotspot and the measured signal
   (e.g. "frontend opens 7 outbound gRPC client connections"), AND the fused
   SonarQube quality signal (e.g. project totals: 240 issues — 230 code smells,
   7 bugs, 3 vulnerabilities — and the per-service breakdown for the chosen hub).
2. **Concrete files** — the exact `src/<service>/` path(s), e.g.
   `src/checkoutservice/main.go` (a billing-path coupling hub AND the file the
   cited SonarQube issue sits in). At least **one concrete `src/<service>/` file**
   is required.
3. **SonarQube issue** — cite a concrete **SonarQube issue key** on this surface,
   verbatim as `SonarQube issue: <key> (<rule> / <severity> / <type>) at
   <component>:L<line> — <message>`. Use `static_analysis.exemplar_issue` from the
   fused `service-coupling.json` (it is already chosen on the priority surface).
   The string `SonarQube issue:` MUST appear verbatim.
4. **Why it matters** — change-amplification / blast-radius reasoning, and why the
   billing path is the priority surface (a defect or coupling change on
   cart/checkout/payment/currency directly threatens revenue).
5. **Proposed refactor** — a concrete, scoped first step (not "consider
   refactoring"), and **name the remediation back-end** on a line beginning
   `Proposed refactor` that names either **Codegen** (agentic multi-file SWE
   back-end — for novel, judgment-heavy fixes; registered under `mcp_servers` in
   `hermes/config.yaml`) or **Moderne/OpenRewrite** (deterministic recipe engine —
   for recipe-amenable, mechanical debt). Pick the one that fits the fix and say
   why. (For this stack, the live remediation back-end is **Codegen**;
   Moderne/OpenRewrite is documented as the recipe-amenable alternative and rolled
   into GLO-14 as a paid evaluation — see `hermes/config.yaml`.)
6. **Grounding** — for **every distinct `source_file` your multi-angle queries
   returned that supports the finding**, a literal line
   `Grounded in: <source_file> (<what THIS text backs>)` tying that source to the
   specific dimension it grounds. Cite the union — never pre-curate or guess; let
   retrieval decide which texts are relevant. The string `Grounded in:` MUST appear
   verbatim, once per cited source.
7. **Acceptance criteria** — a short checklist so it is actionable as-is.

### Template

```markdown
## Finding
`checkoutservice` is a billing-path coupling hub in Online Boutique: it opens **6
outbound gRPC client connections** (cart, currency, email, payment,
productcatalog, shipping) — the second-highest coupling degree after `frontend`
(7). It is ALSO flagged by SonarQube. Fused SonarQube scan (DETECT): **240 issues
project-wide — 230 code smells, 7 bugs, 3 vulnerabilities** (ncloc 5,856,
complexity 550); `checkoutservice` itself carries SonarQube issues on
`src/checkoutservice/main.go`. graphify (KEEP) supplies the coupling; SonarQube
(DETECT) supplies the quality signal; this ticket fuses both.

## Concrete files
- `src/checkoutservice/main.go` — the 6-backend `mustConnGRPC(...)` block (the
  coupling evidence_file) AND the file the cited SonarQube issue sits in.
- `protos/demo.proto` — the single shared gRPC contract every service couples to.

## SonarQube issue
SonarQube issue: <KEY> (go:S1135 / INFO / CODE_SMELL) at
online-boutique:src/checkoutservice/main.go:L151 — Complete the task associated to
this TODO comment.
(use static_analysis.exemplar_issue from the fused service-coupling.json)

## Why it matters
A change to any of the 6 backend contracts can ripple into `checkoutservice`, and a
`demo.proto` change touches every service at once. Because this is the **billing
path** (cart/checkout/payment/currency), a defect or coupling change here directly
threatens revenue — making it the priority surface for remediation.

## Proposed refactor (first step)
Proposed refactor — route to **Codegen** (the agentic multi-file SWE back-end
registered under `mcp_servers` in `hermes/config.yaml`): introduce an explicit
anti-corruption seam in `checkoutservice` isolating the 6 service contracts, and
resolve the flagged SonarQube issue in the same change. This is a novel,
judgment-heavy refactor spanning wiring + contract boundaries, so Codegen fits
better than a mechanical recipe. (Moderne/OpenRewrite — the deterministic recipe
engine — is the recipe-amenable alternative for mechanical debt; evaluating it
(paid) is rolled into GLO-14.) Then split `demo.proto` per bounded context so a
contract change no longer fans out to all services.

## Grounded in
(one line per distinct source_file the multi-angle queries returned — cite the union)
Grounded in: software-architecture.md (efferent coupling CE / afferent coupling CA —
breaking apart a high-CE component reduces change amplification).
Grounded in: sam-newman-building-microservices.md (the interplay of coupling and
cohesion — a backward-incompatible contract forces upstream consumers to change in lockstep).
Grounded in: balancing-coupling-in-software-design.md (coupling strength and the
distance over which a change propagates).
Grounded in: managing-technical-debt.md (the economic spotlight — coupling debt
carries interest paid as friction on every future change, and remediation cost/benefit).
Grounded in: strategic-monoliths-and-microservices.md (right-sizing service
granularity and decomposition boundaries).
Grounded in: accelerate.md (loosely-coupled architecture as a top driver of delivery
throughput and deployment performance).

## Acceptance criteria
- [ ] BFF/anti-corruption seam introduced in `src/frontend/` isolating the 7 clients.
- [ ] `protos/demo.proto` split per bounded context (no single all-service contract).
- [ ] No service imports another service's stubs directly.
```

## After filing

1. Confirm by reading the ticket back: `list_issues(query="[Brownfield]", team="Global South Ai Safety")`
   (or `get_issue`) and verify the `Brownfield` label is attached, the body names a
   concrete `src/<service>/` file, and it carries a `Grounded in:` line for **every
   distinct `source_file` your multi-angle queries returned** (not just one).
2. **Persist the ticket into git (decision record).** Git history is the authoritative
   record of every CTO decision (design "Desired End State"), so snapshot the ticket you
   just filed into the tracked `tickets/<ID>.md`:
   ```bash
   python3 scripts/snapshot_tickets.py <THE_ID>     # e.g. GLO-13
   # or, to refresh every agent-filed ticket: bash scripts/snapshot_after_run.sh
   ```
   Then the operator reviews and commits `tickets/`. (Cron/recorded runs call
   `scripts/snapshot_after_run.sh` automatically as a post-step.)
3. Report the issue identifier/URL and a one-line summary; deliver to Telegram.
