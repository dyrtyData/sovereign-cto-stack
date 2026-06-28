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

### Backlog P1 — Deny-by-default egress hardening (built; the sovereign safety layer)

The Q3 deferral above is now **partially actioned** as the GLO-13 P1 slice. What landed and
the honest tradeoffs:

**What's built.** A reviewable allow-list artifact (`egress/policy.yaml`) enforced
out-of-process by a **real NVIDIA OpenShell sandbox** (verified against OpenShell 0.0.71) — not
a hand-rolled proxy. A workload is confined with
`openshell sandbox create --no-keep --policy egress/policy.yaml --from egress/ -- <cmd>`; the
sandbox supervisor (PID 1) auto-injects `HTTPS_PROXY` and routes every outbound TLS CONNECT
through the OpenShell gateway's OPA proxy (`https://127.0.0.1:17670`, a local launchd service).
A CONNECT whose `host:port` matches an `enforcement: enforce` endpoint in the policy (Linear /
Telegram / Nous-inference / web-scrape) is tunnelled; every other CONNECT is **refused by
default** (`curl: (56) CONNECT tunnel failed, response 403`). No `egress-proxy` compose service
exists — enforcement is the sandbox, and the policy is loaded read-only by OpenShell. The gate
`scripts/assert_egress_policy.py` drives a real sandbox and proves it.

**Decision: the gate's load-bearing assertion is the NEGATIVE test (Q3-sub, Option β).**
Deny-by-default is only meaningful if you can demonstrate a denial; a positive-only gate is
satisfiable by a sandbox that blocks nothing. So the gate runs both probes inside the confined
sandbox and asserts a CONNECT to a non-allow-listed host (`example.com:443`) is **refused**
(load-bearing — curl exit 56 / 403) *and* `api.linear.app:443` **succeeds** (positive path —
http 200), proving the allow-list doesn't break legitimate egress.

> _Grounded in: *Accelerate* — make safety properties observable and verifiable, not asserted;
> reproducible feedback over trust._

**Honest degradation — the two documented macOS bugs.** The network CONNECT layer (what we
enforce + assert) is deliberately **independent of the Landlock filesystem layer**, because
on macOS the OpenShell sandbox's Landlock support runs in `best_effort` mode and can
**silently degrade** (OpenShell #803) — a filesystem-confinement assertion there would be
fragile. By making the load-bearing assertion a *network* CONNECT refusal, the safety proof
stays reliable regardless of the Landlock state. Separately, the sandbox has a known
`inference.local` **mDNS resolution constraint** on macOS (the broken local-Ollama DNS path):
inference therefore stays **cloud** (Nous Portal, already required since there's no CUDA on
Apple Silicon), which sidesteps the mDNS path entirely.

**Recorded for GLO-14, not built now: host-orchestrator-in-MicroVM confinement (Q3 Option B).**
This slice enforces egress on the **containerized** sub-tools inside the LinuxKit VM. Confining
the **host** Hermes orchestrator's own egress requires moving it into a MicroVM (libkrun +
Hypervisor.framework), which adds the biggest moving-parts/DNS risk; that is captured as a
**GLO-14** path, not built in this pass.

> _Grounded in: *An Elegant Puzzle* (Larson) — sequence the hardening investment; enforce the
> layer that is load-bearing and reliable now, and record the stronger confinement as a
> deliberate next step rather than over-engineering the platform before the deadline._

### Backlog P2 — Stripe-grounded AARRR Revenue/Retention (built)

The Q4 deferral is now actioned as the GLO-13 P2 slice.

**What's built.** A stdlib-only reference client (`scripts/stripe_client.py`, following the
`linear_mcp.py` pattern) reads **real Stripe test-mode** MRR / churn / cohort data and writes
`recordings/stripe_metrics.json`; the `pmf_brief` skill grounds the AARRR **Revenue/Retention**
cells in it (citing the artifact), replacing the old web-scraped competitor-pricing assumptions.
The fresh sandbox is seeded idempotently (`scripts/stripe_seed.py`, metadata tag
`seed:sovereign-cto-stack`) so the numbers are genuinely real: MRR $1,281/mo, 25% lifetime churn,
3 monthly cohorts (60%/75%/100% retention). `scripts/assert_stripe_grounding.py` gates it.

**Decision: NO graceful degradation — fail loud, TEST-key-only.** Unlike the outline's
"optional/seeded" framing, the client FAILS LOUDLY (never fabricates) if `STRIPE_API_KEY` is
absent/invalid or the sandbox is empty, and a guard **REFUSES** any `sk_live_`/`rk_live_` key. The
key is documented as required for the grounding but `preflight.sh` stays ungated (the stack still
runs without it; only the Stripe grounding is unavailable) — mirroring the optional `MEM0_API_KEY`
pattern. Credibility comes from real data or an honest failure, never a fabricated number.

> _Grounded in: *The Lean Product Playbook* — grounding the value hypothesis in real revenue signal
> rather than assumptions; *Accelerate* — reproducible, evidence-driven feedback._

### Backlog P3 — SonarQube DETECT + graphify KEEP → Hermes JUDGMENT → Codegen/Moderne (built)

The Q4-folded secondary billing audit + the full-build P3 architecture, now actioned.

**What's built.** A profile-gated SonarQube Community service (compose `--profile sonar`) scans the
real `workspaces/microservices-demo/` clone; `scripts/sonarqube_client.py` (Bearer token from the
gitignored `.sonar-token`) pulls `/api/issues/search` + `/api/measures/component` into
`graphify-out/sonar-issues.json` — a **real scan: 240 issues (230 smells / 7 bugs / 3 vulns)**.
`scripts/fuse_signals.py` merges them onto `graphify-out/service-coupling.json` as an additive
`static_analysis` block (the schema is unvalidated JSON), keeping graphify's coupling/`hubs`
intact (frontend=7 / checkout=6). The auditor files GLO-16 citing the real SonarQube issue key
(`go:S1135` @ `src/checkoutservice/main.go`) **and** the degree-6 billing-path coupling hub **and**
a remediation back-end. `scripts/assert_sonar_fusion.py` gates all three.

**Decision: keep graphify; SonarQube augments, never replaces it; Hermes is the JUDGMENT layer.**
SonarQube has **no coupling metric** (its beta Architecture feature is Cloud-only / Java-first /
repo-scoped), so for a polyglot multi-service target graphify is genuinely additive. The detectors
(SonarQube) and remediators (Codegen/Moderne) are commodities; the **white space is the
textbook-grounded judgment/curation layer** that synthesizes both signals, prioritizes the
**billing path** (revenue surface — the folded-in P2 secondary), and routes to the right back-end.

**Decision: route to Codegen now; defer the Moderne/OpenRewrite (paid, no free tier) evaluation to
GLO-14.** GLO-16's billing-path refactor is a novel, judgment-heavy multi-file change, so it routes
to **Codegen** (named-only — 0 free runs burned). **Moderne/OpenRewrite** is the deterministic
recipe engine for recipe-amenable + Java debt, but it has **no free tier**, so evaluating it is an
explicit decision item rolled forward to GLO-14 rather than an unconditional build.

> _Grounded in: *Managing Technical Debt* — making the debt's economic interest legible and
> prioritizing the highest-business-impact (billing) surface; *Software Architecture: The Hard
> Parts* — CE/CA coupling analysis as the additive structural signal SonarQube lacks._

### Backlog P4 — Full PMF loop: RICE/ICE-ranked + prior-decisions consult (built)

The Q1 full-scope P4, now actioned (depends on P2's real revenue grounding).

**What's built.** The loop emits **multiple opportunities ranked RICE/ICE** (3 here: 67.5/32.4/10.0)
+ a `recordings/pmf_ledger.json` carrying `rice_score`, `shipped`, and the prior-decisions record,
each opportunity grounded in the corpus + Stripe. `scripts/assert_pmf_ranked.py` gates ≥2 scored,
ranked, grounded opportunities + a non-empty "Prior decisions consulted" section.

**Decision (user-requested): consult prior decisions before ranking; fail rather than fabricate.**
`scripts/mem0_pmf_decisions.py` idempotently seeds the tracked `tickets/[Product]` decisions into
**self-hosted mem0** (pgvector `mem0-postgres`, local HF embedder) and semantically searches them,
plus reads the `git log` of `tickets/`. The brief carries a "Prior decisions consulted" section and
**drops** any candidate matching a prior decision — it correctly does **not** re-propose the
already-decided GLO-12 autonomous-remediation bet (mem0 returns it @ score 0.32). **No graceful
degradation:** if mem0 can't persist/retrieve, the run FAILS rather than fabricating "no prior
decisions".

**Honest limitation → GLO-14.** This slice **reads** prior decisions (seeded + git) but does not yet
**write** each run's new decision back into the mem0 `memories` collection — so mem0 is verified-
working but the collection does not yet accumulate over time. Closing that **passive long-lived
memory-capture** write path is the headline GLO-14 item (the user's explicit request).

> _Grounded in: *Hacking Growth* — a North Star (opportunities shipped) over vanity output;
> *An Elegant Puzzle* — not re-litigating decided bets; mem0 as a recall convenience over the
> authoritative git history (never a dependency)._

### Closeout — comprehensive showcase montage (hybrid montage, design Q6) (built)

**What's built.** `scripts/build_showcase_video.py` assembles a **hybrid montage**: live
split-screen captures for the visual hero loops + short purpose-built segments for the non-visual
proofs (denied egress / Stripe AARRR / SonarQube issues / ranked PMF), each rendered from its repo
artifact via `scripts/render_title_card.py` (the `render_service_graph.py` self-contained-HTML
house style). A **simple `ffmpeg concat`** stitches exactly the segments that pass
`verify_recording.py` into `recordings/showcase_<ts>.mp4` + a `showcase_manifest.json`;
`scripts/assert_showcase_video.py` gates a valid, non-static concat carrying ≥ the guaranteed
visual hero loop(s).

**Decision: simple ffmpeg concat, no editing suite (design Q6 sub-decision).** A GUI editor would
make the final video a hand-made artifact that can't be rebuilt by a gate or a fresh clone,
breaking the repo's core regenerate-from-clean-clone invariant. The scripted concat reads whatever
segments passed `verify_recording.py` and stitches exactly those — so a missing Stripe/SonarQube
segment simply isn't in the list and the script still produces a valid video (the graceful
fallback, for free). Title cards are just more self-contained HTML painted onto `:99`, and ffmpeg
is already the recorder's only video dependency — no new tools enter the stack.

**Decision: P0 ticket-in-browser ending = local-snapshot `file://` HTML, not the live Linear URL.**
The throwaway container Chromium has no Linear session, so the live ticket URL hit Linear's auth
wall. `scripts/render_ticket_card.py` renders the tracked local `tickets/<ID>.md` snapshot to a
self-contained `file://` HTML and the hero capture ends on **that** — the filed ticket visible, no
auth, fully reproducible. The real-Linear-UI ending (a persistent authenticated Chromium profile)
is the stronger-but-fragile next step, rolled forward to GLO-14.

> _Grounded in: *Accelerate* — reproducibility and determinism over hand-made artifacts; make the
> working system observable without breaking the clean-clone invariant._

### GLO-14 P1 — mem0 OSS pinned to >= v2.0.0 for native entity-linking (built; the foundation slice)

**Decision (design D-1, Option A): upgrade and pin mem0 OSS to `>=2.0.0,<3.0.0`** (tested against
`2.0.10`) and rely on its **built-in entity linking** rather than an external graph store. This is
the de-risking foundation the rest of GLO-14's "system that learns" stands on (P2 closes the write
path on top of it). The pin lives in the PEP 723 inline-dependency headers of
`scripts/mem0_roundtrip.py` and `scripts/mem0_pmf_decisions.py`; `uv` resolves it per-run, so there
is no project-wide lockfile to drift.

**Why this is low-risk.** We never configured `graph_store`, so the "native entity-linking replaces
external graph DBs" change is purely additive for us — there is **no Neo4j and no `graph_store` key
to remove**, and `hermes/mem0.json` loads unchanged under v2.0.0. The two behavioural changes that
v2.0.0 actually makes — (1) `add()`/`search()` always return a dict with a `results` list, and
(2) entity IDs (`user_id`/`agent_id`/`run_id`) must be passed inside `search()`'s `filters` argument
— were *already* how the repo's scripts call mem0 (the PMF consult and the round-trip both pass
`filters={"user_id": …}` and unwrap `results`). So the bump is a pin, not a rewrite.

**How the bump is gated.** `scripts/mem0_roundtrip.py` (the existing CI smoke) is extended beyond its
`infer=False` persistence proof to assert the v2.0.0 contract via `_assert_v2_shape()` —
`results[]` present, each row carries a stable `id`, search rows carry a numeric `score` — and to
exercise `infer=True` + native entity-linking over two facts that share an entity
(`checkoutservice`), asserting the linked entity is observable in recall. The entity-link pass
**self-skips** (logs `SKIP`, still exit 0) when the local Ollama fact-extractor is unreachable, so
CI never depends on a local LLM while a dev box with Ollama proves the link automatically. Option B
(stay pinned, vector-only) was discarded — it forgoes the native-graph recall quality that makes
"graph logic handled natively under the hood" real for this stack.

> _Grounded in: *Accelerate* — pin and gate dependency changes so a working increment is always
> reproducible; mem0 as a recall complement over the authoritative git history (never a dependency)._

### GLO-14 P2 — Close the mem0 write path: `memories` accumulates every run (built; the load-bearing slice)

**Decision (design Q2/Q3/Q4): a deterministic Python writer closes the loop, into the unified
`memories` collection, with `infer=True`.** GLO-13 left the system able to *read* prior decisions
but never *write* new ones, so the `memories` collection never accumulated — the headline GLO-14
gap (the user's explicit request). This slice inserts `scripts/mem0_record_decision.py` at the
single canonical position research pins in **both** agent loops — AFTER `save_issue` returns a
ticket id and BEFORE `snapshot_after_run.sh` (`scripts/record_run.sh` step 7b;
`scripts/pmf_kanban_run.sh` step 4b) — writing the full agent turn (grounding question + filed
decision) into `memories` so mem0 extracts/dedups/entity-links it natively.

- **Q2 — unify on `memories`.** The PMF consult (`scripts/mem0_pmf_decisions.py`) now *reads* the
  same `memories` collection (`user_id="sovereign-cto"`) the writer writes, instead of the old
  isolated `pmf_decisions` silo nobody else touched — so recall is real, not theatre. The
  idempotent seed of the tracked `tickets/[Product]` snapshots is preserved (so a fresh box still
  has prior decisions before any `agent_run` write lands) but tagged `source:"ticket_seed"` to stay
  distinct from accumulated `source:"agent_run"` decisions. Verified: the repointed consult returns
  the seeded `GLO-12` decision **and** the loop's own `agent_run` writes, and
  `assert_pmf_ranked.py` stays exit-0 with `prior_decisions_consulted.mem0_hits` populated from
  `memories`.
- **Q3 — the deterministic helper is load-bearing; the Hermes-native path is a *probe*, not a
  dependency.** Passive capture is unavailable for this stack (inference routes through the Nous
  Portal proxy, not mem0's OpenAI-compatible proxy), so an explicit `add()` is the only guaranteed
  mechanism. Whether the closed-source `hermes-agent` binary *also* writes `memories` on its own via
  `hermes/mem0.json` is answered empirically — not left open — by the non-gating diagnostic
  `scripts/diagnose_hermes_mem0_write.py`, which runs one loop with the helper disabled
  (`MEM0_RECORD_DECISION_DISABLE=1`) and reports a machine-readable verdict.

  > **Recorded Q3 verdict (2026-06-28, CONCLUSIVE):**
  > `{"verdict": "NO_NATIVE_WRITE", "collection": "memories", "user_id": "sovereign-cto",
  > "baseline_rows": 4, "post_rows": 4, "delta": 0, "loop_ran": true, "loop_rc": 0}`
  >
  > Ran with all three prerequisites satisfied: the `hermes` binary on PATH, the
  > `graphify-out/service-graph.html` input (generated via `scripts/run_graphify.sh`), and reachable
  > Nous inference. **The closed-source `hermes-agent` binary does NOT write the `memories` collection
  > on its own.** A full hero loop ran with our deterministic helper disabled (`rc=0`, 13 real tool
  > calls incl. `query_cto_knowledge` + `save_issue`), yet `memories` stayed at 4 rows (delta +0). This
  > empirically confirms design Q3: passive/native capture is unavailable for our architecture, so the
  > deterministic `mem0_record_decision.py` helper is **REQUIRED**, not merely a complement.
  >
  > **Inference-path correction (learned while running this probe):** `hermes -p` talks DIRECTLY to the
  > Nous remote API (`https://inference-api.nousresearch.com/v1`, provider `nous`) using the OAuth
  > credential from `hermes portal login` — it does **not** route through the optional local
  > `hermes proxy` on `:8645` (nothing in our loop does). The probe's reachability guard therefore
  > checks the remote inference API, not `:8645`; a network/timeout failure there yields `INCONCLUSIVE`
  > rather than a false `NO_NATIVE_WRITE`. (`hermes portal login` is one-shot OAuth onboarding — it
  > authenticates the host and is not re-run per session; the credential persists in `~/.hermes`.)

- **Q4 — `infer=True` (mem0's intended extraction), self-skipping to `infer=False` when Ollama is
  down.** The write feeds mem0 the whole turn so the extraction LLM pulls salient facts, dedups,
  and entity-links (`>= v2.0.0` native). When the local Ollama fact-extractor is unreachable the
  helper degrades to `infer=False` (the raw turn still persists, the collection still accumulates,
  recall extraction is skipped) and logs the downgrade — mirroring the round-trip's Ollama self-skip
  so CI never depends on a local LLM. The write **never** silently no-ops: a row always lands,
  tagged `source:"agent_run"` + `decision_id`.

**The gate (design Q5 — tolerant of `infer=True` phrasing).** `scripts/assert_memory_accumulates.py`
drives the writer twice in an *isolated* `memacc_<uuid>` collection (so it neither depends on nor
pollutes the live `memories`) and asserts, scripted: the `source:"agent_run"` count grew after each
run; a `search()` for run 2's topic returns run 2's `decision_id`; run 2 *also* recalls run 1's
`decision_id` (accumulation, not overwrite); and the recalled decision text is **not a substring of
any `tickets/*.md`** — the load-bearing "accumulated via the write path, not re-seeded from the git
snapshots" proof. Verified exit 0 (run 1: 0→2 rows, run 2: 2→4 rows, both decision ids recalled,
no ticket-substring leak).

**spaCy lemmatization (`mem0ai[nlp]`) — the hybrid LEXICAL index now uses real lemmas.** mem0 OSS
`>= v2.0.0` builds a hybrid retrieval index whose lexical half is a Postgres
`gin to_tsvector('simple', payload->>'text_lemmatized')` over a *lemmatized* copy of each memory.
Without spaCy, mem0 logged **`Failed to load spaCy lemma model`** and fell back to a simpler
tokenizer (worse keyword recall). We pinned the **`mem0ai[nlp]`** extra (which pulls spaCy) in every
mem0-touching script's PEP 723 header — the three new ones (`mem0_record_decision.py`,
`assert_memory_accumulates.py`, `diagnose_hermes_mem0_write.py`) and the two existing
(`mem0_roundtrip.py`, `mem0_pmf_decisions.py`) — changing `"mem0ai>=2.0.0,<3.0.0"` →
`"mem0ai[nlp]>=2.0.0,<3.0.0"`. spaCy also needs the `en_core_web_sm` model: the writer proactively
warms mem0's own lemma loader, which downloads the model once if missing and otherwise **degrades
with a logged note** (never hard-fails — same Ollama-style self-skip philosophy). Verified: across
the `record_decision` smoke, the accumulation gate, and the NO_AGENT PMF loop the logs now read
`spaCy lemma model loaded` / `spaCy lemma model ready` and the `Failed to load spaCy lemma model`
warning is **gone**; persisted rows carry a populated `text_lemmatized` (e.g. `couple coupling`,
`refactore refactoring`), confirming the lexical index is lemmatized.

> _Grounded in: *Accelerate* — close the feedback loop so the system learns from its own delivered
> work; *An Elegant Puzzle* (Larson) — a guaranteed deterministic mechanism over a probabilistic
> one for a step that must happen every run. Git history stays the authoritative decision record;
> mem0 is the recall complement that must never become load-bearing for correctness._

**Recorded alternative considered and rejected — mem0 passive capture via its OpenAI-compatible
proxy.** The Q3 probe proved the `hermes-agent` binary does not write `memories` natively, which
raises the obvious question: *could we get passive, "as-intended" capture by routing inference
through mem0?* Technically **yes** — mem0's only passive mode is its OpenAI-compatible proxy
(`mem0.proxy.main.Mem0`), which auto-`add()`s every turn **when, and only when, the LLM call flows
through mem0 itself**. Today `hermes -p` talks straight to the Nous remote API (provider `nous`,
OAuth), so mem0 is never in that path. To enable passive capture you would **chain the inference
path**: `hermes-agent → mem0 proxy → hermes proxy (:8645, OAuth→Nous)` — point Hermes' provider at
mem0's proxy as an OpenAI-compatible `base_url`, and mem0 forwards to the local `:8645` shim (which
already performs the OAuth translation) while silently capturing each turn. **We reject this for
GLO-14** because it places mem0 **in the critical inference hot path**: a mem0 outage would break
every agent call, and it captures raw conversational turns (noisy, untagged) instead of curated,
metadata-tagged, gate-able decisions — directly violating the standing rule that *mem0 is a recall
complement, never load-bearing for correctness* (AGENTS.md rule 2; git stays authoritative). The
deterministic `mem0_record_decision.py` writer gives strictly better control for our purpose. The
option is **rolled forward to Part C** below (and into the next epic's ticket) as a documented,
deliberately-deferred path — *here is exactly how to enable it if a future epic ever wants
passive capture*, with the load-bearing tradeoff stated up front.

### GLO-14 P3 — Greptile PR review as a standing ticket-instruction line (built; fully decoupled)

**Decision (design D-3/D-4): the ONLY in-repo Greptile deliverable is a standing instruction
LINE appended to every filed ticket body, plus a gate that reads it back.** There is **no in-repo
Greptile code, no MCP server, no webhook receiver, and no `query_cto_knowledge` triage** — those
were considered (the next-epic ticket sketches a webhook→resume→review→triage loop) and
deliberately **kept out of this repo**. The Greptile CLI, the Claude Code skill, and the
`/greptile` command are set up **globally in `~/.claude`, OUTSIDE this repo** (a separate,
project-agnostic task, not a GLO-14 repo deliverable and not tracked here). This repo's surface is
exactly: the filing skills (`hermes/skills/file_brownfield_ticket.md`, `pmf_brief.md`,
`pmf_rank.md`) and the epic filer (`scripts/file_fullbuild_ticket.py`) append the literal line —

> _After you open a PR for this ticket, run Greptile on it (/greptile) and address the findings
> before requesting merge._

— to the end of every `[Brownfield]`/`[Product]`/`[Full-Build]` ticket body, and
`scripts/assert_greptile_instruction.py` gates it.

**Why decoupled (D-3/D-4).** The sovereign-CTO payoff Greptile adds is "agents that ship *and*
review," but the *mechanism* that runs the review is project-agnostic developer tooling — it
belongs in the global `~/.claude` profile that any repo's PRs can use, not baked into this stack.
Embedding a Greptile MCP/webhook here would (a) couple this repo to a specific review vendor's
runtime, (b) duplicate setup that already lives globally, and (c) re-introduce an
inference-hot-path / always-on-service dependency of exactly the kind we rejected for mem0 passive
capture above. The standing instruction line is the thin, durable, in-repo contract; the heavy
lifting stays out-of-repo. **The Greptile GitHub App is the no-code fallback** — it auto-reviews
on PR-open with no custom hook — so even without the global CLI a reviewer path exists; the
in-repo line just makes "run the review" a non-optional standing instruction on every ticket.

**The gate (mirrors `assert_brownfield_ticket.py`).** `scripts/assert_greptile_instruction.py`
reads the newest filed ticket back over the SAME Linear MCP endpoint Hermes uses **and** reads the
tracked `tickets/<ID>.md` snapshot, asserting **both** carry the instruction line. Asserting both
proves the line survives the full path (agent files it into Linear → `snapshot_tickets.py`
persists it into git), not just one end. The match is tolerant of trivial wording-around (it keys
on "run Greptile … (/greptile) … address the findings") so a human copy-edit of the surrounding
prose doesn't break the gate while the operative instruction stays required. Verified exit 0 on
the newest `[Brownfield]` ticket (GLO-18) and on the next-epic `[Full-Build]` (GLO-14); the
unrelated `assert_brownfield_ticket.py` / `assert_product_ticket.py` invariants stay exit 0 (the
appended line is purely additive — it does not disturb the grounding/label/`src/<service>/`
checks).

> _Grounded in: *Accelerate* — peer review / fast feedback on every change as a delivery-
> performance practice; *An Elegant Puzzle* (Larson) — keep project-agnostic tooling out of the
> product repo and make the standing expectation explicit rather than embedding a vendor runtime._

### GLO-14 P5 — Close the PMF North Star loop: a Stripe-grounded shipped-bet flip (built)

**Decision (design D-5, Option C): flip `pmf_ledger.json[].shipped false -> true` from a
recorded shipped-result that is GROUNDED in real Stripe data — so "shipped" means a
*measured* outcome, never a hand-set flag.** The Backlog-P4 PMF loop ranks opportunities and
stamps each `shipped: false`, and the North Star metric is `opportunities_shipped` — but
nothing ever flipped a row, so the loop proposed forever and never closed. This slice adds the
missing feedback edge.

**What's built.** `scripts/pmf_shipped_results.py` is a small, deterministic module with two
pieces, the `fuse_signals.py` additive/atomic pattern throughout:

- a SHIPPED-RESULT RECORD, `recordings/shipped_results.json` — one entry per shipped bet
  (`bet_id` + measured `metric`/`value` + the `stripe_metrics.json` grounding ref);
- a DETERMINISTIC JOINER, `flip_shipped(ledger, results, stripe_metrics) -> int`, that joins
  the records onto the ledger by bet id (the opportunity title or its rank), flips each
  matching row `shipped false -> true`, and stamps `grounded_in += ["stripe_metrics.json"]`
  (idempotent — never duplicated). It reads the WHOLE ledger, mutates only the target rows,
  and writes the whole doc back via `os.replace` — **never clobbering any other ledger key**
  (`question`, `scoring_model`, `prior_decisions_consulted`, the unrelated opportunities).

It is wired into `scripts/pmf_kanban_run.sh` immediately after the ledger write: a no-op (0
rows) on a default run with no recorded result, and a real flip when a result has been
recorded. A flip is **itself a decision**, so each flipped row is recorded into the unified
mem0 `memories` collection via the Phase-2 `mem0_record_decision.py` helper (sequenced after
P1's write path closed, exactly as this phase depends on).

**Decision: GROUNDED, not asserted — refuse to flip on a fabricated number.** A shipped-result
is honored **only** when its recorded metric value equals a value actually present in
`recordings/stripe_metrics.json` (the real test-mode MRR/churn/cohort figures
`scripts/stripe_client.py` computes from the live Stripe API). A record whose value is not a
real Stripe figure is REFUSED — the same no-fabrication contract that runs through
`stripe_client.py`. No new Stripe surface and no new egress endpoint were added: the joiner
reuses the already-computed `stripe_metrics.json` artifact via a tiny additive
`stripe_client.load_metrics()` read helper (no API re-hit).

**The gate.** `scripts/assert_shipped_flip.py` seeds a `shipped_results.json` for a known bet
(the rank-1 opportunity, grounded in the real MRR read straight out of `stripe_metrics.json`),
runs the joiner on an **isolated temp copy** of the ledger (mirroring how
`assert_memory_accumulates.py` uses a throwaway collection — the real tracked
`recordings/pmf_ledger.json` is never mutated and stays all-false), and asserts: the target
bet flipped to `true`; its `grounded_in` cites `stripe_metrics.json`; the recorded metric value
EQUALS a real `stripe_metrics.json` value (the MRR/churn cross-read — "measured real outcome");
every unrelated opportunity stayed `false`; and every other ledger key is preserved
byte-for-byte. `scripts/assert_pmf_ranked.py` stays exit 0 (the ledger schema + ranking
invariants are untouched — `shipped` and `shipped_result` are additive fields).

> _Grounded in: *Hacking Growth* — a North Star (opportunities **shipped**) measured from real
> outcomes over vanity output; *Lean Analytics* / *The Lean Product Playbook* — validate a bet
> against a real revenue/retention metric, not a self-asserted flag; *Accelerate* —
> deterministic, reproducible, gate-able state changes over hand edits._

### GLO-14 P3 / D-2 — Fuller multi-component demo + read-only memory view + optional authenticated Linear ending (built)

**Decision (design D-2: Option A montage spine + Option B lightweight memory view).** The recorded
demo previously surfaced only two surfaces (a tool-call log + the coupling graph) and ended on a
locally-rendered ticket snapshot. This slice makes the montage show **more of the stack** and adds a
cheap read-only memory view, while keeping every default path **reproducible from a clean clone**.

**The D-2 segment list (what the montage now tells).** `build_showcase_video.py`'s `catalogue()`
was extended so the montage reads as the fuller story: the visual hero loop + the existing
artifact-backed data surfaces (egress **403** refusal, Stripe MRR/churn, SonarQube fusion, the
RICE ledger incl. the P5 `shipped` flip) **plus four always-rendered title-carded chapters** —
the **mem0 memory view**, the **Kanban** create→claim→complete lifecycle, the **Greptile** PR-review
instruction, and the **Linear ticket ending**. Lower-signal components (per the component-inventory
map: Nous Portal inference, `fuse_signals`, Codegen routing, the gate battery, the MicroVM spike)
become title cards rather than bespoke live captures — the graceful-degradation montage philosophy
(design Q6) carried forward. `assert_showcase_video.py` raises the manifest minima accordingly
(`SHOWCASE_MIN_SEGMENTS=5` + a required-id check on the four D-2 title segments; both env-overridable
so a deliberately smaller montage is still possible). **Final segment ORDERING is a collaborative
human micro-detail (D-2 open question), not gated.**

**The read-only memory view (P1 made visible).** `scripts/render_memory_card.py` is a NEW read-only
surface that queries the unified `memories` rows + mem0-native entity links and renders them to a
self-contained `file://` HTML — reusing the `render_ticket_card.py:51-107` marked.js template /
screenshot pattern (a module-level f-string + an inlined `json.dumps` payload + one CDN `<script>`,
no build step). It **never writes** to mem0 and degrades gracefully (emits a valid "collection
unreachable" card) if pgvector is down — the load-bearing accumulation proof remains
`assert_memory_accumulates.py`; this card is the *visualization*. A `--baseline`/`--against` diff
mode highlights rows that are NEW since a snapshot, which is exactly what the new
`scripts/assert_memory_view_grows.py` gate uses to SCRIPT the "visibly more rows after a loop" claim
(render before → run one decision through the real write path → render after → assert the parsed
count strictly grew). The gate runs against a throwaway isolated collection, so it never pollutes the
live `memories`.

**Decision: the default ending stays the reproducible `file://` snapshot; the authenticated
live-Linear ending is OPTIONAL and gated, never the default.** The throwaway container Chromium has
no Linear session, so the live ticket URL hits Linear's auth wall. Rather than make the demo depend
on a host-held login, the **default** ending remains the git-tracked `tickets/<ID>.md` snapshot
rendered to `file://` (no auth, always passes `verify_recording.py`). The authenticated ending is
opt-in: `recorder/entrypoint.sh`'s `launch_browser` appends `--user-data-dir=$CHROMIUM_USER_DATA_DIR`
**only when that env var is set**, `docker-compose.yml` bind-mounts a **gitignored**
`./recorder-profile` (it holds a live session — never committed, AGENTS.md rule 3/8), and
`record_run.sh`'s `TICKET_LIVE_URL=1` block resolves the filed ticket URL and launches the right
pane with that persistent profile so a logged-in session carries into the capture.

**Decision: gate the WIRING, leave the live-session eyeball to a human.** Proving a recording ends
on the *genuine* authenticated Linear page needs a human-held Linear session — that stays a human
checkpoint. But the wiring ("does the recorder launch Chromium WITH `--user-data-dir` when a profile
is provided?") is fully automatable: `scripts/assert_persistent_profile_wiring.py` drives the real
`launch_browser` path inside the running recorder with a **throwaway** `--user-data-dir` and a
harmless local target, then asserts the launched command carried the flag (and that Chromium
populated the dir) — exercising the wiring with no real Linear session. This keeps the falsifiable
exit-0 contract on the load-bearing mechanism while honestly scoping the two genuinely-human checks
(the authenticated-session eyeball and the collaborative segment ordering).

> _Grounded in: *The Lean Startup* — demo the working system honestly (a reproducible default that
> never fakes auth) over a staged screenshot; *Accelerate* — reproducible-from-clean-clone artifacts
> and deterministic exit-0 gates over manual, un-reproducible captures; *Building Microservices* —
> visualize the real component topology (the coupling graph, the memory layer, the Kanban lifecycle)
> so the architecture is legible, not asserted._

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
- **mem0 passive capture via its OpenAI-compatible proxy (GLO-14 Q3 follow-on).** *Deferred —
  considered and rejected for now.* The Q3 probe confirmed the Hermes binary does not write
  `memories` natively, so the only route to "passive, as-intended" capture is to chain inference
  through mem0's proxy: `hermes-agent → mem0 proxy (mem0.proxy.main.Mem0) → hermes proxy (:8645,
  OAuth→Nous)`, with mem0 silently `add()`-ing every turn. *Why not now:* it puts mem0 **in the
  critical inference hot path** (a mem0 outage breaks every agent call) and captures noisy raw turns
  instead of curated, tagged, gate-able decisions — violating the standing rule that mem0 is a recall
  complement, never load-bearing (git stays authoritative). The deterministic
  `mem0_record_decision.py` writer is the better fit. Recorded here (with the exact enablement path)
  so a future epic can adopt passive capture deliberately if the tradeoff ever becomes worth it.
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
