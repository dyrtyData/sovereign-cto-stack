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

## Open / deferred items (tracked for the Phase-5 full-build ticket)

- Full mem0 OSS server + Next.js dashboard (Phase 1 uses SDK-on-host against pgvector).
- OpenHands via Portal/LiteLLM (Q7).
- Second-account "fresh setup" walkthrough (Q4/Q8b).
- OpenShell/NemoClaw egress hardening on Apple Silicon, incl. `policy.yaml` allow-list shape (Q3).

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
