# CTO Functions — "Teach Me to Think Like a CTO"

The Sovereign CTO Stack is built to both *do* CTO work and *teach the reasoning behind it*. The
user is new to thinking like a CTO (design "Current State"), so this document is the explicit
map of **the CTO-level functions the system performs**, each one **grounded in the named corpus
texts that feed it**. It is the answer to "what does a CTO actually decide, and what should I
read to reason about it?"

Every function below follows the same discipline (design Q5, enforced by `hermes/AGENTS.md`
rule #1): **consult `query_cto_knowledge` before acting**, decompose the question into its
dimensions, issue **one query per dimension**, and **cite the union** of the distinct
`source_file`s retrieval returns — never one query / one citation, never a pre-curated title
list (let retrieval decide; see the "multi-angle grounding" decision in
[`system-design-tradeoffs.md`](./system-design-tradeoffs.md)).

> **How to read the citations.** Each function names the converted corpus files
> (`<slug>.md` under the gitignored `corpus/`) that `query_cto_knowledge` surfaces for it. The
> corpus map (which book maps to which domain) lives in
> [`system-design-tradeoffs.md` → "Surfaced gold-standard texts per domain"](./system-design-tradeoffs.md).
> A `*` marks a function the stack **demonstrates today** (Phases 3–4); the rest are functions
> the *same machinery* extends to (see the [full-build ticket](../tickets/) backlog).

---

## 1. Tech-debt / architecture audit  *(demonstrated — Phase 3, the hero loop)*

**The CTO question:** *Where is this system most expensive to change, and what is the
highest-leverage refactor?* A CTO does not fix every smell — they find the **coupling hubs**
whose change-amplification and blast-radius tax every future feature, and justify a scoped
refactor in business terms (the "interest" the debt charges).

**How the stack does it:** graphify maps the target (`GoogleCloudPlatform/microservices-demo`)
statically; `scripts/service_topology.py` derives the service-level coupling
(`frontend` = 7 outbound gRPC edges, `checkoutservice` = 6); the `CTO-Architecture` profile
multi-angle-queries the RAG brain and files a HumanLayer-ready `[Brownfield]` Linear ticket
naming exact `src/<service>/` files with a `Grounded in:` line per cited text (GLO-8/9/10/11).

**Grounding dimensions → texts:**

| Dimension queried | Texts surfaced |
|---|---|
| Coupling (efferent/afferent, change amplification) | `software-architecture.md` (*Software Architecture: The Hard Parts*), `sam-newman-building-microservices.md`, `balancing-coupling-in-software-design.md` (Khononov) |
| Technical-debt economics / interest | `managing-technical-debt.md` |
| Service decomposition & granularity tradeoffs | `strategic-monoliths-and-microservices.md`, `architecture-for-flow.md` |
| Delivery / throughput performance | `accelerate.md`, `lean-enterprise.md` |
| Data-at-scale architecture (when relevant) | `designing-data-intensive-applications.md` (Kleppmann) |

---

## 2. Product-market-fit (PMF) / product-opportunity research  *(demonstrated — Phase 4)*

**The CTO question:** *Is there a real, underserved need here, and which opportunity should we
bet on?* A technical CTO co-owns product judgment: they separate problem-space from
solution-space, size the market, and frame the riskiest assumption as a cheap experiment rather
than a year-long build.

**How the stack does it:** the `CTO-Market` profile scrapes the web for current signal,
multi-angle-queries the growth/PMF corpus, writes a textbook-cited strategic brief
(`recordings/pmf_brief_*.md`), then diffs the brief against what the product offers today and
files ONE market-informed `[Product]` opportunity ticket (GLO-12). It hands off over the shared
Kanban board (`kanban_complete()` with summary + metadata) so the orchestrator can act on it.

**Grounding dimensions → texts:**

| Dimension queried | Texts surfaced |
|---|---|
| Problem / solution fit, value proposition | `the-lean-product-playbook.md` (Olsen — the PMF Pyramid) |
| Target customer & market sizing (TAM/SAM/SOM) | `the-lean-product-playbook.md`, `hacking-growth.md` |
| Experimentation / validated learning | `lean-enterprise.md`, `trustworthy-online-controlled-experiments.md` (Kohavi) |
| Growth loops / acquisition / North Star metric | `hacking-growth.md` (Ellis, Brown) |

---

## 3. Pivot / vertical strategy

**The CTO question:** *Given how the market is moving, should we pivot, pick a vertical, or hold
the line — and on what evidence?* This is PMF research applied to a strategic inflection: read
the value-chain, find where the position is defensible, and decide what to *stop* doing.

**How the stack extends to it:** the same `CTO-Market` PMF loop, asked a strategy question
(e.g. "which vertical should the auditor specialize in first?"), with Wardley-mapping the value
chain to expose where components are evolving from custom-built toward commodity (and therefore
where to invest vs. outsource). The full-build backlog's **P4 (PMF→product loop, full version)**
ranks multiple opportunities RICE/ICE and optionally consults graphify for technical
feasibility of a proposed capability.

**Grounding dimensions → texts:**

| Dimension queried | Texts surfaced |
|---|---|
| Value-chain / evolution / positioning | `practical-introduction-to-wardley-mapping.md`, `architecture-for-flow.md` |
| Strategy under uncertainty / portfolio bets | `lean-enterprise.md`, `an-elegant-puzzle.md` (Larson — sequencing investments) |
| Market sizing & demand signal | `the-lean-product-playbook.md`, `hacking-growth.md` |
| When to monolith vs. decompose for the bet | `strategic-monoliths-and-microservices.md` |

---

## 4. Organization design / engineering leadership

**The CTO question:** *How should teams, ownership boundaries, and the org be shaped so the
architecture and the delivery flow reinforce each other?* (Conway's Law in both directions.) A
CTO designs team topologies, defines clear single-responsibility capabilities, and sequences
where to invest org capacity.

**How the stack extends to it:** the orchestrator (or a dedicated `cto-org` profile) answers org
questions through the same grounded loop — and the stack already *embodies* the principle:
specialist profiles (`CTO-Architecture`, `CTO-Market`) are single-responsibility capabilities
coordinating over one shared surface (the Kanban board), exactly the Team-Topologies pattern.

**Grounding dimensions → texts:**

| Dimension queried | Texts surfaced |
|---|---|
| Team boundaries / cognitive load / interaction modes | `team-topologies.md` (Skelton, Pais) |
| Sequencing org investment / scaling the org | `an-elegant-puzzle.md` (Larson) |
| The executive's operating model & priorities | `the-engineering-executive-s-primer.md` (Larson) |
| Manager/IC growth & role clarity | `camille-fournier-the-manager-s-path.md` (Fournier) |
| Organizing boundaries for flow (Conway alignment) | `architecture-for-flow.md`, `zero-distance.md` |

---

## 5. Delivery / engineering-excellence stewardship

**The CTO question:** *Is the engineering org delivering safely and fast, and what one lever
moves throughput most?* A CTO watches the four DORA metrics and treats loosely-coupled
architecture + small-batch delivery as the levers — which is exactly why the **tech-debt audit
(function 1)** grounds its delivery dimension in `accelerate.md`.

**Grounding dimensions → texts:**

| Dimension queried | Texts surfaced |
|---|---|
| Delivery performance / DORA / small batches | `accelerate.md` (Forsgren, Humble, Kim) |
| Continuous delivery & lean flow at scale | `lean-enterprise.md` |
| Architecture as a delivery enabler | `architecture-for-flow.md`, `strategic-monoliths-and-microservices.md` |

---

## 6. Agentic / GenAI systems architecture

**The CTO question:** *How should we architect the multi-agent system itself?* The Sovereign CTO
Stack is itself an agentic system; the CTO reasoning that designed it (orchestrator + specialist
profiles + shared coordination surface + grounded tool-use) is grounded in the agentic-systems
corpus.

**Grounding dimensions → texts:**

| Dimension queried | Texts surfaced |
|---|---|
| Multi-agent coordination & roles | `designing-multi-agent-systems.md` |
| Agentic architecture patterns | `agentic-architectural-patterns-for-building-multi-agent-systems.md` |
| GenAI design patterns (RAG, tool-use, grounding) | `generative-ai-design-patterns.md` |

---

## How the functions compose (the factory loop)

```
query_cto_knowledge (CTO brain, consulted FIRST — design Q5)
        │  grounds every function below
        ▼
┌───────────────────────────────────────────────────────────────┐
│ graphify ── tech-debt audit (fn 1) ──► [Brownfield] Linear ─┐   │
│ web scrape ─ PMF/strategy (fn 2,3) ──► [Product] Linear ────┤   │
│ org/delivery reasoning (fn 4,5) ─────► grounded brief ──────┤   │
└─────────────────────────────────────────────────────────────┘   │
        │ all coordinate over the shared single-host Kanban board  │
        ▼                                                          ▼
   git-tracked tickets/<ID>.md  ◄── snapshot_tickets.py    HumanLayer / engineer acts
```

Every filed ticket is snapshotted into the tracked `tickets/<ID>.md` (see
[`setup-guide.md` → "Ticket tracking"](./setup-guide.md)) so **git history is the authoritative
record** of every CTO decision the system makes — mem0 is a complement, not a dependency (design
"Desired End State").
