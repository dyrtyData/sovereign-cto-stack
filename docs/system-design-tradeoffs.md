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

## Per-phase findings

_Coupling findings, RAG choices, and refactor reasoning are appended here as Phases 2–4 land._
