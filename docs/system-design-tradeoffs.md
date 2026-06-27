# System Design — Decisions & Tradeoffs

The authoritative decision record for the Sovereign CTO Stack. Git history is the source of
truth; this document is the human-readable, textbook-grounded narrative behind each locked
decision. It is updated every phase.

## Citation convention

Every design rationale that draws on the CTO corpus cites its grounding text inline, e.g.:

> _Grounded in: *Building Microservices* (Newman) — on service coupling; *Accelerate*
> (Forsgren, Humble, Kim) — on small-batch delivery._

Citations name the **book title** (and author where helpful). Once the RAG brain is online
(Phase 2), citations should map to the exact converted corpus file(s) `query_cto_knowledge`
surfaces. Until then, citations name the text by title.

## Locked decisions

### Q1 — Scope: strict sequential, gated phasing (+ a Phase 0 and a demo slice)

The build is **Phase 0→1→2→3→4→5, strictly sequential and gated**: each phase is a thin
vertical slice that boots and is independently verifiable before the next begins. This matches
the ticket's own "do not move to Phase 2 until Phase 1 is operational," de-risks the EOD-June-30
deadline (a partial-but-working slice always exists), and gives a clean public-showcase
narrative. The discarded alternatives were **parallel workstreams** (external dependencies —
tokens, OAuth logins — serialize the work anyway, and partial failures compound) and
**single-domain only** (too narrow; sacrifices the showcase breadth).

**Reconciliation (precedence: outline > design > research).** The design discussion sequenced
the RAG brain *after* the tech-debt loop, but Q5 mandates consulting `query_cto_knowledge`
*before every CTO function, including the tech-debt loop*. To honor Q5 without a backward
dependency, the RAG brain was brought **up to Phase 2, before** the first grounded CTO function
(Phase 3). The hero demo is still the tech-debt audit; no phase requires a later phase to verify.

**The parallel deliverable** (this decision's second half): author one comprehensive
**"full-build" Linear ticket** capturing the entire vision + the deferred backlog so the whole
system can be rebuilt later even though only the phased slice is executed now. Filed in Phase 5.

> _Grounded in: *An Elegant Puzzle* (Larson) — sequencing investments rather than starting
> everything at once; *Accelerate* — small-batch delivery and keeping a working increment._

### Q2 — Standalone repo, gitignored by the parent (nested-repo safety)

`sovereignCTO/` is its own git repo (`git init`, remote `dyrtyData/sovereign-cto-stack`) nested
inside the `GS_AISafetyHackathon` parent. This is safe **only because** the parent's
`.gitignore` ignores the exact folder name `sovereignCTO/`, so the parent never descends into
it or stores a stray gitlink. (Contrast: a nested repo whose name the parent does *not* ignore
gets exposed as an embedded-repo gitlink on `git add`.) The local folder name stays
`sovereignCTO` because the live HumanLayer session is pinned to that path; the GitHub repo name
is independent and already correct.

> _Grounded in: *Accelerate* — version control of everything and clean repository hygiene as a
> delivery-performance practice._

### Q3 — Docker egress isolation for Phases 0–2; OpenShell/NemoClaw sandbox deferred to Phase-3 hardening

For Phases 0–2, "sovereign" egress control comes cheaply from a Docker network allow-list. The
full NVIDIA OpenShell/NemoClaw sandbox (Landlock + seccomp + OPA-evaluated CONNECT proxy via
`policy.yaml`) is **deferred** as optional Phase-3 hardening. It is confirmed viable on Apple
Silicon (OpenShell supports macOS aarch64 via the Docker Desktop LinuxKit VM / libkrun +
Hypervisor.framework), with caveats: inference must be cloud (no CUDA on Apple Silicon), and a
couple of known bugs to watch (Landlock `best_effort` fallback; broken local-Ollama DNS in the
sandbox on macOS). Deferring keeps moving parts off the EOD-June-30 critical path.

> _Grounded in: *An Elegant Puzzle* (Larson) — sequencing investments / not over-engineering
> the platform before it is load-bearing._

### Q4 — One Nous account, multiple Hermes profiles, shared single-host Kanban

Instead of juggling two Nous accounts, run several Hermes **profiles** (personas) on this one
host: an orchestrator, a `CTO-Architecture` auditor, and a `CTO-Market` researcher. They
coordinate through one shared `~/.hermes/kanban.db` board. This "multi-multi-agent" pattern
works **only** on a single host — Hermes has no implemented cross-host/cross-account
coordination primitive, so two-account topologies would break Kanban coordination. The
second-account "fresh setup" walkthrough is documented for the future (folded into the Phase-5
full-build ticket).

> _Grounded in: *An Elegant Puzzle* — organizing specialized roles around a shared coordination
> surface rather than fragmenting ownership._

### Q7 — OpenHands deferred; future enablement via Portal/LiteLLM

OpenHands (autonomous greenfield prototyping) is **deferred** for the hackathon. The greenfield
path for now is "Hermes research -> HumanLayer Linear ticket -> Claude Code executes." Claude
Code Max **cannot** back OpenHands (Anthropic blocks subscription OAuth tokens in third-party
tools; OpenHands needs a pay-per-token API key). The chosen future enablement is pointing
OpenHands at the Nous Portal OpenAI-compatible endpoint via LiteLLM, avoiding a separate
Anthropic key. This is captured in the Phase-5 full-build ticket.

> _Grounded in: *The Engineering Executive's Primer* (Fournier) — deferring tooling investment
> until it is justified by a concrete workflow need._

### Q6 — mem0 & graphify placement: local-first, with mem0 Platform as fallback

graphify runs **locally on the host** against the cloned audit target (the code-graph layer is
fully local via tree-sitter; no LLM key for the default AST path). mem0 is Hermes' **native
memory provider, self-hosted on Postgres + pgvector** (SDK-on-host; see the deferred note below
on why the full OSS server is out of the critical path). **mem0 Platform** (`MEM0_API_KEY`,
already in `.env`) is the **fallback** if the self-hosted path is troublesome. This pairs with
the project's durability principle: **memory is a convenience layer over the authoritative git
history** — if mem0 is unavailable or wrong, the git log + this doc must still let a human
reconstruct every decision. Discarded: a Neo4j graph push (extra service, unneeded for
static-coupling analysis).

> _Grounded in: *Accelerate* — version control of everything as the source of truth; mem0 as a
> recall convenience, never a dependency._

### Q8 / Q8b — Manual prerequisites gate; both accounts greenfield

A **Manual Prerequisites** checklist sits at the top of the README and the build **halts** on it
(programmatically via `scripts/preflight.sh`, which fails on any missing/placeholder required
key). Both Nous accounts are **greenfield** (corrected from the ticket's premise): only the
static `NOUS_PORTAL_API_KEY` and `MEM0_API_KEY` exist; Hermes was not installed, Portal OAuth not
run, no Telegram bot, Linear connected only to HumanLayer. So the "primary account already
configured" path is dropped — it collapses into Q4 (one greenfield account, multiple profiles).

The only **human-gated** points are: (1) the two browser OAuth approvals (`hermes portal login`;
`hermes mcp install linear`), (2) creating the Telegram bot token + numeric id by hand
(@BotFather / @userinfobot) into `.env`, (3) the Telegram hello-world confirmation, and (4)
keeping the laptop plugged in + lid open for long/recorded runs. Everything else is scripted and
reproducible from the [setup guide](./setup-guide.md). The **hero demo is the Phase-3 tech-debt
audit** (visually concrete, central to the primary use case); the PMF brief is the secondary
capture. The Docker `ffmpeg`/`Xvfb` sidecar is the capture method (manual screen recording was
the discarded deadline fallback).

> _Grounded in: *The Engineering Executive's Primer* — making prerequisites explicit and gating
> on them rather than discovering missing setup mid-flight._

### Q5 — CTO knowledge RAG: local Vector MCP sidecar; consult before *every* CTO function

The CTO brain is a **local Vector MCP sidecar** (`rag/`) — MiniLM embeddings (all-MiniLM-L6-v2,
384 dims) over an embedded **LanceDB** index of the converted textbook corpus, served by FastMCP
over Streamable HTTP, exposing one tool: `query_cto_knowledge`. The agent must consult it
**before every CTO function** (tech-debt audit, PMF, org/strategy) and cite the returned
`source_file`(s) — enforced by `hermes/AGENTS.md` rule #1.

**Why this option (vs the alternatives surveyed in research §10):**

- **Chosen — local Vector MCP sidecar:** fully local, **zero external keys** (reuses the same
  embedding model as the mem0 round-trip), returns **raw cited chunks** the agent can ground
  on, and binds cleanly to Hermes as an MCP tool. Self-contained: file-based LanceDB means no
  second DB service on the critical path before EOD June 30.
- **Discarded — `claude-context` (Zilliz/Milvus cloud):** cloud dependency + an OpenAI embedding
  key; also disabled in this environment.
- **Discarded — NotebookLM CLI:** black-box server-side retrieval — no query-ranked chunk access,
  so the agent cannot cite exact grounding passages.
- **Discarded — indexed grep/dig-down:** weak recall, no semantic ranking.

These remain **documented future possibilities** but are not built now.

> _Grounded in: *Accelerate* — fast, local feedback loops; and the showcase goal of citable,
> reproducible reasoning over a black-box service._

**Conversion pipeline (design Q5 / research §15):** docling (PDF, Apple MPS) + pandoc (EPUB —
docling has no EPUB support), preferring the PDF when both exist (a stable title-slug maps both
formats to one `corpus/<slug>.md`). OCR is disabled (born-digital books; docling 2.68's bundled
RapidOCR engine fails to initialize on this host). Output is **gitignored** (copyrighted content
stays local); the conversion script is tracked.

**Hermes MCP-client gap (recorded so a clean clone reproduces):** Hermes v0.17.0 ships without
the `mcp` Python SDK, so HTTP MCP binding fails until you
`uv tool install hermes-agent --with mcp --with python-telegram-bot`.

#### Surfaced "gold-standard" texts per domain (the corpus map)

The corpus the RAG brain indexes, grouped by the CTO function each domain feeds:

| Domain | Texts (cite the converted `source_file`) |
|---|---|
| **Architecture / tech-debt** (Phase 3) | *Building Microservices* (Newman), *Software Architecture: The Hard Parts*, *Balancing Coupling in Software Design* (Khononov), *Managing Technical Debt*, *Strategic Monoliths and Microservices*, *Designing Data-Intensive Applications* (Kleppmann) |
| **Delivery / engineering excellence** | *Accelerate* (Forsgren, Humble, Kim), *Lean Enterprise* |
| **Growth / PMF** (Phase 4) | *The Lean Product Playbook* (Olsen), *Hacking Growth* (Ellis, Brown), *Trustworthy Online Controlled Experiments* (Kohavi, Tang, Xu), *Lean Enterprise* |
| **Org design / eng leadership** | *An Elegant Puzzle* (Larson), *The Engineering Executive's Primer* (Larson), *The Manager's Path* (Fournier), *Team Topologies* (Skelton, Pais), *Architecture for Flow* (Kaiser), *Practical Wardley Mapping*, *Zero Distance* |
| **Agentic / GenAI systems** | *Designing Multi-Agent Systems*, *Agentic Architectural Patterns*, *Generative AI Design Patterns* |

> _Grounded in: *Building Microservices* / *Balancing Coupling* — the architecture audit's
> primary references; *The Lean Product Playbook* / *Hacking Growth* — the PMF references;
> *An Elegant Puzzle* / *The Engineering Executive's Primer* — org & strategy._

## Per-phase findings

### Phase 3 — Online Boutique coupling audit (the hero loop)

**What the graph showed.** graphify maps the source of `GoogleCloudPlatform/microservices-demo`
(Online Boutique) statically (tree-sitter, no deploy). The raw AST graph (2,513 nodes /
~4,290 edges) is file/symbol-level, so the *service-level* coupling — the signal a CTO
cares about — is derived deterministically by `scripts/service_topology.py` from the gRPC
client wiring (`mustConnGRPC(...)` over each `*_SERVICE_ADDR`). The result
(`graphify-out/service-coupling.json`) reproduces the known topology (research §13):

| Service | Outbound gRPC edges | Wired in |
|---|---|---|
| **`frontend`** | **7** (productcatalog, currency, cart, recommendation, shipping, checkout, ad) | `src/frontend/main.go` |
| **`checkoutservice`** | **6** (shipping, productcatalog, cart, currency, email, payment) | `src/checkoutservice/main.go` |
| `recommendationservice` | 1 (productcatalog) | `src/recommendationservice/recommendation_server.py` |
| all others | 0 (leaves) | — |

Two endpoints are deliberately **excluded** from gRPC coupling degree: the OpenTelemetry
`COLLECTOR_SERVICE_ADDR` (telemetry, not a business service) and `shoppingassistantservice`
(the newer REST/Flask Gemini+AlloyDB add-on — *not* in the `protos/demo.proto` gRPC
contract). Counting them would inflate `frontend` to 8; the honest gRPC-coupling number is 7.

**Why it's the tech-debt headline.** `frontend` and `checkoutservice` are the two
high-efferent-coupling hubs, and *every* edge flows through one shared contract,
`protos/demo.proto`. That concentrates **change amplification** and **blast radius**: a
backward-incompatible change to any backend contract ripples into `frontend`, and a
`demo.proto` change touches all services at once. The grounded refactor (filed as the
`[Brownfield]` ticket **GLO-8**) is to introduce a backend-for-frontend / anti-corruption
seam in `frontend` and split `demo.proto` per bounded context so a contract change stops
fanning out to the whole system.

> _Grounded in (surfaced by `query_cto_knowledge` before the ticket was written, design Q5,
> via **multi-angle querying** — see the decision below — citing the **union** of the
> distinct `source_file`s the angle queries returned):
> *software-architecture.md* — "Coupling levels" / "Service Granularity": efferent coupling
> (CE) measures how many components this one depends on, and breaking apart a high-CE
> component reduces change amplification; *managing-technical-debt.md* — "Shining an Economic
> Spotlight on Technical Debt": coupling debt carries interest paid as friction on every
> change, with explicit remediation cost/benefit (T4); *sam-newman-building-microservices.md*
> — "The Interplay of Coupling and Cohesion": a backward-incompatible contract forces upstream
> consumers to change in lockstep; *balancing-coupling-in-software-design.md* — coupling
> strength and the distance a change propagates; *strategic-monoliths-and-microservices.md* —
> right-sizing service granularity and decomposition boundaries; *architecture-for-flow.md* —
> organizing service boundaries for flow; *accelerate.md* (with *lean-enterprise.md*) —
> loosely-coupled architecture as a top driver of delivery throughput._

**Decision: derive the service graph deterministically rather than trust raw node degree.**
graphify's AST graph degree is dominated by intra-file symbol edges (`method`, `contains`,
`references`), which would not surface the 7/6 service topology directly. A small,
auditable extractor over the gRPC wiring gives a stable, reviewable signal the auditor and
the CI assertion (`scripts/assert_graph_topology.py`) both read — and keeps the default run
fully local (no LLM key) by pruning non-code assets from the throwaway clone.

> _Grounded in: *Accelerate* — fast, reproducible, local feedback loops over opaque tooling._

**Decision: the auditor is a separate `cto-architecture` profile, not the orchestrator.**
It is cloned from `default` (inheriting both MCP bindings), carries its own auditor
`SOUL.md` (the always-loaded slot, so the rule survives the supervised gateway's `~/.hermes`
cwd), and files via the `file_brownfield_ticket` skill. Linear OAuth tokens are per-`HERMES_HOME`,
so the already-approved token is copied into the profile's `mcp-tokens/` — no second browser
approval, same account.

> _Grounded in: *An Elegant Puzzle* — specialized roles around a shared coordination surface;
> *Team Topologies* — a clear, single-responsibility "auditor" capability rather than overloading
> the orchestrator._

**Decision: ground by MULTI-ANGLE querying and cite the union — never one query / one
citation, never a pre-curated list.** The first pass of the loop under-cited: the auditor
issued a single coupling-phrased `query_cto_knowledge` call and the skill hard-coded a curated
example title list with a "cite at least one source_file" floor — so it cited two texts and
missed the corpus's most on-point ones (`managing-technical-debt.md`, which is the top hit at
0.71 for the economics angle, and `software-architecture.md`, which leads on three angles).
A real CTO finding is multi-dimensional, and one query phrased one way only surfaces one
slice. The rule is now generalized in all three loaded surfaces (orchestrator `SOUL.md`,
auditor `SOUL.md`, the `file_brownfield_ticket` skill): **decompose the finding into its
dimensions, issue one `query_cto_knowledge` call per dimension** (for coupling: coupling,
technical-debt economics/interest, service decomposition & granularity tradeoffs,
delivery/throughput performance), **and cite the union of the distinct `source_file`s those
queries return** — letting retrieval, not a guessed list, decide what is relevant. Re-running
this against the live RAG endpoint returns 8 distinct sources; GLO-8 now carries a
`Grounded in:` line for each, every line tied to the dimension it backs. Because the rule
lives in the orchestrator SOUL too, it applies unprompted to the Phase-4 PMF profile and every
other CTO function.

> _Grounded in: *Accelerate* — reproducible, evidence-driven feedback over opaque single-shot
> judgement; *Managing Technical Debt* — making the debt's interest legible (the very text the
> single-query pass missed)._

**Decision: render a legible service-level graph rather than ship graphify's raw graph as the
demo surface.** graphify's `graph.html` is the raw file/symbol AST graph (hundreds of nodes) —
correct, but unreadable and useless for a screen recording. `scripts/render_service_graph.py`
reads the derived `graphify-out/service-coupling.json` and emits `graphify-out/service-graph.html`:
~11 service nodes, directed gRPC edges, with `frontend` (7 outbound) and `checkoutservice` (6)
emphasized by size/color/label and the leaf backends muted. It is self-contained (vis-network
from CDN, data embedded inline), opens standalone in any browser, and is the surface the Phase-4
recording captures. The renderer is tracked; its HTML output stays in the gitignored
`graphify-out/` (a derived artifact, reproducible from `run_graphify.sh` step 5).

> _Grounded in: *Accelerate* — make the signal legible and reproducible; the audit's value is
> only realized if a human can see the coupling hub at a glance._

### Phase 4 — PMF research, Kanban coordination, recording

**Decision: the PMF researcher is a second `cto-market` profile coordinating over the shared
Kanban board, not a fan-out subagent.** The two specialists (`cto-architecture`, `cto-market`)
and the orchestrator share one `~/.hermes/kanban.db` (design Q4). The PMF run is driven through
the board lifecycle (`create → claim → run → complete` with a structured `summary` + `metadata`
handoff), so the result is a durable, readable `task_runs` row — not an ephemeral RPC return.
This is the durable, audit-trailed coordination primitive over the ephemeral `delegate_task`
fan-out (research §5).

> _Grounded in: *Team Topologies* — single-responsibility teams coordinating over a clear shared
> interface; *An Elegant Puzzle* — durable coordination surfaces over fire-and-forget delegation._

**Decision: close the PMF loop into a filed `[Product]` ticket, not just a brief.** A brief no
one acts on is inert, so every PMF run scans the current product, diffs it against the market
findings, picks ONE concrete capability gap, and files a HumanLayer-ready `[Product]` ticket
(GLO-12). Notably the agent independently surfaced the **autonomous-remediation gap** (detect-only
auditor → no PR), which is exactly the white space the full-build P3 backlog formalizes.

> _Grounded in: *The Lean Product Playbook* — moving down the PMF Pyramid from problem to a
> concrete feature bet; *Hacking Growth* — a North Star (opportunities shipped) over vanity output._

**Decision: record a LIVE split-screen surface, because `x11grab` records pixels.** A text-only
agent run captures a black frame, so the recorder paints a visible surface onto `:99` *before*
capture and `record_run.sh` refuses to start if no window is mapped. The hero recording is a live
split-screen: the auditor's log scrolling on the left (`tail -f`, demonstrably non-static) next to
the legible coupling graph on the right. `verify_recording.py` asserts container validity,
`duration>0`, a finalized moov atom, a non-blank mid frame, **and** non-static (inter-frame luma
delta) — so a black or still recording fails CI.

> _Grounded in: *Accelerate* — make the working system observable and the demo reproducible._

## Deferred / future work — and *why* each was deferred (tracked in the full-build ticket)

These are intentional deferrals, not omissions. Each is captured as a prioritized section of the
Phase-5 full-build Linear ticket so the complete system can be (re)built later (design Q1). The
rationale below is the interview-ready "why now / why not now" for each.

- **(P1) NemoClaw / OpenShell egress hardening on Apple Silicon, incl. `policy.yaml` allow-list
  shape (Q3).** *Deferred because:* the Docker network allow-list gives "sovereign" egress control
  cheaply for Phases 0–4, and the full Landlock+seccomp+OPA sandbox adds moving parts (and two
  known macOS bugs — Landlock `best_effort` fallback; broken local-Ollama DNS) onto the
  EOD-June-30 critical path. It is confirmed viable on Apple Silicon (Docker Desktop LinuxKit VM /
  libkrun + Hypervisor.framework) and is the competition's safety/egress story, so it is P1.
- **(P2) Stripe skills integration (competition requirement).** *Deferred because:* the hackathon
  slice proves the grounded-CTO-function loop end-to-end without live billing data. The primary
  future use is to GROUND the PMF brief's AARRR Revenue/Retention in real MRR/churn/cohorts
  (vs assumptions); secondary is a billing-path tech-debt audit (the highest-business-impact code).
- **(P3) SonarQube + graphify → Hermes judgment layer → Codegen / Moderne remediation.**
  *Deferred because:* the hero loop already proves the detect→ground→file chain on graphify;
  augmenting detection with SonarQube and adding autonomous remediation backends is a substantial
  build. The architecture is recorded in the full-build ticket — Hermes stays the textbook-grounded
  curation/judgment layer (the white space); graphify is kept for cross-service coupling (SonarQube
  has no coupling metrics).
- **(P4) PMF → product loop, full version.** *Deferred because:* the thin loop (one ranked
  opportunity, one ticket) is enough to demonstrate the capability; the full version (multiple
  opportunities ranked RICE/ICE, grounded in real usage + Stripe data, a feedback loop on shipped
  bets) depends on P2 and on accumulated usage data.
- **Full mem0 OSS server + Next.js dashboard.** *Deferred because:* Phase 1 uses the mem0
  SDK-on-host against pgvector — minimal moving parts on the critical path; the dashboard is not
  required to verify any phase, and the M3 can add it later resource-wise.
- **OpenHands via Portal/LiteLLM (Q7).** *Deferred because:* the greenfield path for now is
  "Hermes research → HumanLayer Linear ticket → Claude Code executes." Claude Code Max cannot back
  OpenHands (OAuth tokens blocked in third-party tools); pointing OpenHands at the Portal
  OpenAI-compatible endpoint via LiteLLM is the chosen future enablement (avoids a separate
  Anthropic key).
- **Second-account "fresh setup" walkthrough (Q4/Q8b).** *Deferred because:* the single-account /
  multiple-profiles topology is what makes the shared Kanban board work (Hermes has no cross-host /
  cross-account coordination primitive); a two-account setup is documented for the future only.
- **Video authenticity upgrade.** *Deferred because:* the current recording uses a progress ticker
  alongside the real agent output (Hermes' `-z` buffers its final answer); streaming real
  tool-call events from Hermes' session log into the recording is a polish item, not a blocker.

## Interview-ready summary (the showcase goal)

The throughline is **grounded, reproducible, version-controlled CTO judgment**. Every CTO
function consults a textbook RAG brain *first* and cites the union of texts retrieval returns
(no single-shot guessing); every decision is captured in git (the authoritative record) with mem0
as a recall convenience, never a dependency; every phase is a thin, independently-verifiable slice
sequenced to de-risk a hard deadline; and every external dependency (secrets, OAuth, sandboxing)
is either gated on an explicit prerequisites checklist or deferred with a written rationale. The
hero loop — graphify maps a real polyglot system, the agent grounds the finding in named texts and
files a HumanLayer-ready `[Brownfield]` ticket — is the concrete proof that the factory does
real CTO work, not a demo of toy output.
