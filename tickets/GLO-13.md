# GLO-13 — [Full-Build] Sovereign CTO Stack — complete vision (all phases) + prioritized deferred backlog

- **identifier:** GLO-13
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized
- **team:** Global South Ai Safety
- **status:** Backlog
- **labels:** Full-Build
- **priority:** High (2)
- **snapshot captured:** 2026-06-27T17:19:53+00:00

## Description

## What this is

The single comprehensive **full-build epic** for the Sovereign CTO Stack (design Q1): the entire
vision captured so the complete system can be (re)built later, even though only the phased slice
(Phases 0–4) was executed for the Hermes Hackathon. The first part records the 5 phases that ARE
built; the second part is the **prioritized deferred backlog** (P1–P4) plus the remaining
original deferred items — each with scope + rationale.

Public repo: [https://github.com/dyrtyData/sovereign-cto-stack](<https://github.com/dyrtyData/sovereign-cto-stack>) · decision record:
`docs/system-design-tradeoffs.md` · CTO-function map: `docs/cto-functions.md` · setup:
`docs/setup-guide.md`. Git history is the authoritative decision record; mem0 is a complement.

---

## Part A — the built vision (Phases 0–5, each a thin, gated, verifiable slice)

### Phase 0 — Public-safe repo skeleton + prerequisites gate

Standalone git repo nested in the parent but gitignored by it (Q2); `.env.example` + strict
`.gitignore` (corpus/recordings/db/hermes-home); `docker-compose.yml` skeleton; README Manual
Prerequisites checklist; `scripts/preflight.sh` halts on missing keys. Verified: gitleaks clean,
`docker compose config -q`, preflight halts/passes, parent still ignores the subtree.

### Phase 1 — Hermes orchestrator boots end-to-end (Portal + mem0 + Telegram)

Install Hermes (v0.17.0, `--with mcp --with python-telegram-bot`); Portal OAuth
(`hermes portal login`); self-hosted mem0 on pgvector (SDK-on-host, host port 5433); mem0 as the
native memory provider with Platform fallback (`MEM0_API_KEY`); Telegram gateway hello-world.
Verified: mem0 round-trip, session export, gitleaks clean.

### Phase 2 — CTO knowledge RAG brain (`query_cto_knowledge`)

Convert the Growth / System Design / Org Design textbook corpus (docling PDF + pandoc EPUB,
prefer PDF) to `corpus/*.md` (gitignored); local Vector MCP sidecar (MiniLM + LanceDB + FastMCP
HTTP) exposing `query_cto_knowledge`; bound to Hermes; standing instruction synced into
`~/.hermes` SOUL.md so the supervised gateway loads it. Consulted before EVERY CTO function (Q5),
citing the union of returned source files. Verified: 21 sources / ~22.8k chunks, retrieval smoke,
`hermes mcp test`, Telegram cite-the-book.

### Phase 3 — Tech-debt auditor loop (graphify → grounded `[Brownfield]` Linear ticket) — HERO

Clone Online Boutique; graphify static map; `scripts/service_topology.py` derives service-level
coupling (frontend=7, checkout=6); `CTO-Architecture` profile multi-angle-grounds and files a
HumanLayer-ready `[Brownfield]` ticket naming exact `src/<service>/` files (<issue id="9b8ed28f-a84c-406d-a141-fe8bd84e1d46" href="https://linear.app/global-south-ai-safety/issue/GLO-8/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-backend">GLO-8</issue>/9/10/11);
scheduled on cron. Verified: topology assertion, brownfield-ticket assertion (label + concrete
file + multi-source citation), legible service-graph.html.

### Phase 4 — PMF research profile + autonomous-run `.mp4` recording

`CTO-Market` profile coordinating over the shared single-host Kanban board (Q4); `pmf_brief`
skill (web scrape + multi-angle grounding → cited brief → ONE `[Product]` opportunity ticket,
<issue id="43187d4c-dfc8-4755-8c0c-4efec4574a4a" href="https://linear.app/global-south-ai-safety/issue/GLO-12/product-tech-debt-auditor-stops-at-diagnosis-add-autonomous">GLO-12</issue>); Xvfb+ffmpeg recorder capturing a LIVE split-screen of the hero loop to
`recordings/run_hero_<ts>.mp4`. Verified: brief citation, Kanban ready→running→done handoff,
recording valid/non-blank/non-static, `[Product]` ticket assertion.

### Phase 5 — Documentation finalization + this full-build ticket

Finalized `setup-guide.md` (full clean-clone walkthrough + both OAuth points + the `~/.hermes`
sync steps), `system-design-tradeoffs.md` (Q1–Q8b rationale + why each deferral), new
`cto-functions.md` (the CTO functions ↔ corpus grounding map); ticket-tracking wired into the
workflow (`scripts/snapshot_after_run.sh` + skill post-steps + run-script post-steps so filing a
ticket persists `tickets/<ID>.md` in git); this epic. Verified: gitleaks clean, markdown link
check, `docker compose config -q`, fresh-clone smoke, Linear find returns this ticket.

---

## Part B — PRIORITIZED deferred backlog (build in this order)

### P1 — NemoClaw / OpenShell egress hardening on Apple Silicon (Q3) — competition requirement

**Scope.** Layer NVIDIA OpenShell/NemoClaw on top of the Docker allow-list: deny-by-default
egress enforced out-of-process (Landlock filesystem + seccomp process + OPA-evaluated CONNECT
proxy for network). Run inside the Docker Desktop LinuxKit VM (or libkrun + Hypervisor.framework
MicroVM). Author a `policy.yaml` allow-listing only Linear / Telegram / Nous-inference /
web-scrape endpoints, e.g.:

```yaml
version: 1
network_policies:
  linear_api:
    endpoints: [{ host: api.linear.app, port: 443, enforcement: enforce, access: read-write }]
  telegram_api:
    endpoints: [{ host: api.telegram.org, port: 443, enforcement: enforce, access: read-write }]
  nous_inference:
    endpoints: [{ host: inference-api.nousresearch.com, port: 443, enforcement: enforce }]
  # + web-scrape endpoints; node agents must also whitelist /usr/local/bin/node
```

**Rationale.** This is the competition's safety/egress story and the "sovereign" in Sovereign
CTO. Deferred from the hackathon slice because the Docker allow-list suffices for Phases 0–4 and
the full sandbox adds moving parts + two known macOS bugs (Landlock `best_effort` fallback;
broken local-Ollama `inference.local` DNS) onto the deadline path. Inference must stay cloud
(no CUDA on Apple Silicon). P1 because it is the headline safety requirement.

### P2 — Stripe skills integration — competition requirement

**Scope.** PRIMARY: a CTO profile reads real Stripe MRR / churn / cohort data and uses it to
GROUND the PMF brief's AARRR Revenue & Retention sections in actual revenue instead of
assumptions. SECONDARY: a billing-path tech-debt audit — the Stripe integration code is the
highest-business-impact code, so the `[Brownfield]` auditor should treat it as priority surface.
**Rationale.** The hackathon slice proves the grounded-CTO-function loop without live billing
data; grounding PMF in real revenue (vs assumptions) is the single biggest credibility upgrade to
the product loop and a competition requirement, hence P2.

### P3 — SonarQube integration AUGMENTING the existing tech-debt Hermes workflow

**Scope — the layered stack (record this architecture):****
****SonarQube (DETECT)** — Community (free) tier, pull issues via REST `GET /api/issues/search`
and metrics via `GET /api/measures/component`; **+ graphify (KEEP IT)** for cross-service
coupling / centrality — SonarQube has NO coupling metrics and its beta Architecture feature is
Cloud-only / Java-first / repo-scoped, so graphify is genuinely additive for the polyglot
multi-service case → **Hermes (JUDGMENT / CURATION layer — the white space)**: textbook-grounded
judgment, cross-signal synthesis, dedup/curation, prioritization, and a business-justified ticket
→ **remediation backends**.
**Remediation backends (integrate, neither replaces Hermes):**

* **Codegen** — autonomous ticket→PR, hosted MCP at `mcp.codegen.com`, whole-repo graph-sitter,
  but Python/TS/JS only (not Java); PR quality depends on ticket quality, so pilot first. Use for
  NOVEL fixes.
* **Moderne / OpenRewrite** — deterministic recipe-based mass refactors (dependency/framework
  upgrades, broad languages incl. Java); note some recipes moved to source-available/proprietary
  license. Use for RECIPE-AMENABLE debt.
  **Rationale.** Hermes is the self-learning judgment/curation layer that decides which SonarQube
  signals are worth fixing — the genuine white space; detectors and remediators are commodities
  around it. <issue id="43187d4c-dfc8-4755-8c0c-4efec4574a4a" href="https://linear.app/global-south-ai-safety/issue/GLO-12/product-tech-debt-auditor-stops-at-diagnosis-add-autonomous">GLO-12</issue> (the PMF product ticket) independently proposed exactly this Codegen-style
  autonomous-remediation gap. Deferred because the hero loop already proves detect→ground→file on
  graphify; this is a substantial multi-tool build. P3.

### P4 — PMF → product loop, FULL version

**Scope.** Multiple opportunities ranked RICE/ICE, grounded in real usage + Stripe data (P2),
with a feedback loop on shipped bets (North Star: opportunities-shipped, not tickets-filed);
optionally consult graphify for the technical feasibility of a proposed capability.
**Rationale.** The thin loop (one ranked opportunity, one `[Product]` ticket, <issue id="43187d4c-dfc8-4755-8c0c-4efec4574a4a" href="https://linear.app/global-south-ai-safety/issue/GLO-12/product-tech-debt-auditor-stops-at-diagnosis-add-autonomous">GLO-12</issue>) demonstrates
the capability; the full version depends on P2 (real revenue grounding) and on accumulated usage
data, hence P4.

---

## Part C — remaining original deferred items (with rationale)

* **Full mem0 OSS server + Next.js dashboard** (deferred from Phase 1). *Why:* Phase 1 uses the
  mem0 SDK-on-host against pgvector to minimize moving parts on the critical path; the dashboard
  is not required to verify any phase. The M3 can host it later.
* **OpenHands via Portal/LiteLLM (Q7).** *Why:* the greenfield path for now is "Hermes research →
  HumanLayer Linear ticket → Claude Code executes." Claude Code Max cannot back OpenHands (OAuth
  tokens blocked in third-party tools); point OpenHands at the Portal OpenAI-compatible endpoint
  via LiteLLM (`LLM_MODEL`/`LLM_API_KEY`/`LLM_BASE_URL`) to avoid a separate Anthropic key.
* **Second-account "fresh setup" walkthrough (Q4/Q8b).** *Why:* the single-account /
  multiple-profiles topology is what makes the shared Kanban board work (Hermes has no cross-host
  / cross-account coordination primitive); a two-account setup is future-only.
* **Video authenticity upgrade.** *Why:* the current recording pairs a progress ticker with the
  real agent output because Hermes' `-z` mode buffers its final answer; streaming real tool-call
  events from Hermes' session log into the recording is polish, not a blocker.

---

## Acceptance criteria (for the full-build epic)

- [ ] An engineer (or HumanLayer worktree) can rebuild the entire stack from this ticket + the
      three docs, with no missing step.
- [ ] The prioritized backlog P1→P4 is actioned in order, each as its own sub-issue when picked up.
- [ ] P1 (egress hardening) and P2 (Stripe) — the two competition requirements — are tracked as
      the top of the backlog.
- [ ] Each deferred item states scope + the reason it was deferred (done above).
