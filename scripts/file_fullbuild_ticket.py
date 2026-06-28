#!/usr/bin/env python3
"""file_fullbuild_ticket.py — create/update the comprehensive "full-build" Linear epic (Phase 5).

This is the single ticket (design Q1) that captures the ENTIRE Sovereign CTO Stack vision —
all 5 phases as sections — plus a clearly PRIORITIZED deferred-work backlog (P0–P4), the
remaining original deferred items, and a recurring "author the next epic" closeout (Part D),
each with scope + rationale, so the whole system can be (re)built later by HumanLayer or another
engineer.

It is idempotent: pass an existing id to UPDATE in place, or none to CREATE. After filing it
snapshots itself into tickets/<ID>.md via scripts/snapshot_tickets.py (the Phase-5 ticket
tracking wiring).

Closeout (Phase 6, design Q5): GLO-13's Part B carries a CHECKED-OFF P0->P4 checklist, and the
`--next-epic` mode authors **GLO-14** — the next full-build epic (Part D recurrence) — rolling
forward the Part C remainder + items discovered while executing P0-P4 (mem0 passive memory
capture, Moderne/OpenRewrite paid-tier eval, the real-Linear-UI demo ending, host-orchestrator
MicroVM confinement). GLO-14 also carries the `[Full-Build]` label and the full 5-phase + P1-P4
structure, so `scripts/assert_fullbuild_ticket.py GLO-14` passes its nine structural checks.

Closeout (GLO-14 Phase 7, design D-6 / Q11 / Q12): GLO-14's own backlog is now substantially
actioned, so the `--closeout-epic` mode authors the epic *after* GLO-14 — the next full-build epic
in the self-perpetuating Part-D recurrence. It rolls forward GLO-14's Part C deferrals
(Moderne/OpenRewrite — no account, OSS-pilot preserved as an option; the mem0 OSS server + Next.js
dashboard; OpenHands via Portal/LiteLLM; the second-account walkthrough; and the mem0
passive-capture-via-proxy option) PLUS the items discovered while building GLO-14 P1–P5 (the
live-profile skill-deploy step, the duplicate-finding dedupe need, and the Greptile global setup
as an out-of-repo prerequisite). Linear assigns its id (the next free GLO-NN, after GLO-19); we
snapshot whatever id `save_issue` returns. `scripts/assert_fullbuild_ticket.py <ID>` then asserts
the rolled-forward items are present.

Usage:
  python3 scripts/file_fullbuild_ticket.py                 # create/update GLO-13 (the [Full-Build] epic)
  python3 scripts/file_fullbuild_ticket.py GLO-13          # update that id in place
  python3 scripts/file_fullbuild_ticket.py --next-epic     # author/update GLO-14 (the epic GLO-13 authored)
  python3 scripts/file_fullbuild_ticket.py --next-epic GLO-14
  python3 scripts/file_fullbuild_ticket.py --closeout-epic # author the NEXT epic AFTER GLO-14 (Linear assigns the id)
  python3 scripts/file_fullbuild_ticket.py --closeout-epic GLO-20
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linear_mcp as L  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
TITLE = "[Full-Build] Sovereign CTO Stack — complete vision (all phases) + prioritized deferred backlog"

# Standing review instruction appended to EVERY filed ticket body (GLO-14 P2 / design D-3/D-4).
# The gate scripts/assert_greptile_instruction.py reads this exact line back from the live Linear
# ticket AND the tickets/<ID>.md snapshot. The Greptile CLI/skill/`/greptile` command live globally
# in ~/.claude (an out-of-repo prerequisite) — this repo only carries the instruction line.
GREPTILE_INSTRUCTION = (
    "After you open a PR for this ticket, run Greptile on it (/greptile) "
    "and address the findings before requesting merge."
)
GREPTILE_REVIEW_SECTION = f"\n\n---\n\n## Review\n{GREPTILE_INSTRUCTION}\n"

DESCRIPTION = r"""## What this is

The single comprehensive **full-build epic** for the Sovereign CTO Stack (design Q1): the entire
vision captured so the complete system can be (re)built later, even though only the phased slice
(Phases 0–4) was executed for the Hermes Hackathon. The first part records the 5 phases that ARE
built; the second part is the **prioritized deferred backlog** (P1–P4) plus the remaining
original deferred items — each with scope + rationale.

Public repo: https://github.com/dyrtyData/sovereign-cto-stack · decision record:
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
HumanLayer-ready `[Brownfield]` ticket naming exact `src/<service>/` files (GLO-8/9/10/11);
scheduled on cron. Verified: topology assertion, brownfield-ticket assertion (label + concrete
file + multi-source citation), legible service-graph.html.

### Phase 4 — PMF research profile + autonomous-run `.mp4` recording
`CTO-Market` profile coordinating over the shared single-host Kanban board (Q4); `pmf_brief`
skill (web scrape + multi-angle grounding → cited brief → ONE `[Product]` opportunity ticket,
GLO-12); Xvfb+ffmpeg recorder capturing a LIVE split-screen of the hero loop to
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

**Status (closeout — Phase 6): the P0→P4 backlog is BUILT and gated.** Each slice shipped its own
`scripts/assert_*.py` gate (exit-0-on-pass) and is committed on the
`glo-13-full-build-sovereign-cto-stack-complete-vision-all-phases` branch:

- [x] **P0 — Demo video authenticity** — real `agent.tool_executor` tool-call lines stream into the
      recorded run; `assert_demo_authenticity.py` exits 0. Ending renders the local
      `tickets/GLO-NN.md` snapshot to a self-contained `file://` HTML (no Linear auth wall).
- [x] **P1 — Deny-by-default egress** — real NVIDIA OpenShell sandbox enforces `egress/policy.yaml`;
      `assert_egress_policy.py` exits 0 (negative test load-bearing: a non-allow-listed CONNECT is
      refused 403; `api.linear.app:443` allowed 200).
- [x] **P2 — Stripe-grounded AARRR** — `stripe_client.py` reads real test-mode MRR $1,281/mo / 25%
      churn / 3 cohorts → `recordings/stripe_metrics.json`; the PMF brief grounds Revenue/Retention
      in it; `assert_stripe_grounding.py` exits 0.
- [x] **P3 — SonarQube + graphify fusion** — real SonarQube Community scan (240 issues) fused onto
      `service-coupling.json` as `static_analysis`; GLO-16 cites issue `go:S1135` + the degree-6
      billing-path hub + Codegen back-end; `assert_sonar_fusion.py` exits 0.
- [x] **P4 — Full ranked PMF loop** — 3 RICE-ranked opportunities + `recordings/pmf_ledger.json`;
      consults real prior decisions (self-hosted mem0 + git) and does not re-propose GLO-12;
      `assert_pmf_ranked.py` exits 0.
- [x] **Closeout — showcase montage + GLO-14** — `build_showcase_video.py` ffmpeg-concats the
      passing segments (hybrid montage, design Q6) into `recordings/showcase_<ts>.mp4`;
      `assert_showcase_video.py` exits 0; GLO-14 (the next epic) authored + snapshotted.

### P0 — Demo video authenticity: stream REAL tool-call events — quick win (do first)
**Scope.** Replace the scripted progress ticker in the recorded run with genuine agent
activity: tail Hermes' session log / event stream (the real `query_cto_knowledge` and
`save_issue` tool-call events) into the left split-screen pane as they fire; optionally scroll
the actual retrieved RAG chunks and show the Linear ticket appearing in the browser at the end.
Keep the existing non-blank + non-static recording checks. The recorder/split-screen infra
(`recorder/`, `scripts/record_run.sh`, `scripts/verify_recording.py`) already exists — this is a
surface swap, not new infrastructure.
**Rationale.** Competition-relevant: a demo showing real tool calls firing is materially more
convincing than a ticker, and it's a few-hours change. Small + high-signal → do it BEFORE the
heavier P1/P2 so the submitted artifact improves immediately.

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
**Scope — the layered stack (record this architecture):**
**SonarQube (DETECT)** — Community (free) tier, pull issues via REST `GET /api/issues/search`
and metrics via `GET /api/measures/component`; **+ graphify (KEEP IT)** for cross-service
coupling / centrality — SonarQube has NO coupling metrics and its beta Architecture feature is
Cloud-only / Java-first / repo-scoped, so graphify is genuinely additive for the polyglot
multi-service case → **Hermes (JUDGMENT / CURATION layer — the white space)**: textbook-grounded
judgment, cross-signal synthesis, dedup/curation, prioritization, and a business-justified ticket
→ **remediation backends**.
**Remediation backends (integrate, neither replaces Hermes):**
- **Codegen** — autonomous ticket→PR, hosted MCP at `mcp.codegen.com`, whole-repo graph-sitter,
  but Python/TS/JS only (not Java); PR quality depends on ticket quality, so pilot first. Use for
  NOVEL fixes.
- **Moderne / OpenRewrite** — deterministic recipe-based mass refactors (dependency/framework
  upgrades, broad languages incl. Java); note some recipes moved to source-available/proprietary
  license. Use for RECIPE-AMENABLE debt.
**Rationale.** Hermes is the self-learning judgment/curation layer that decides which SonarQube
signals are worth fixing — the genuine white space; detectors and remediators are commodities
around it. GLO-12 (the PMF product ticket) independently proposed exactly this Codegen-style
autonomous-remediation gap. Deferred because the hero loop already proves detect→ground→file on
graphify; this is a substantial multi-tool build. P3.

### P4 — PMF → product loop, FULL version
**Scope.** Multiple opportunities ranked RICE/ICE, grounded in real usage + Stripe data (P2),
with a feedback loop on shipped bets (North Star: opportunities-shipped, not tickets-filed);
optionally consult graphify for the technical feasibility of a proposed capability.
**Rationale.** The thin loop (one ranked opportunity, one `[Product]` ticket, GLO-12) demonstrates
the capability; the full version depends on P2 (real revenue grounding) and on accumulated usage
data, hence P4.

---

## Part C — remaining original deferred items (with rationale)

- **Full mem0 OSS server + Next.js dashboard** (deferred from Phase 1). *Why:* Phase 1 uses the
  mem0 SDK-on-host against pgvector to minimize moving parts on the critical path; the dashboard
  is not required to verify any phase. The M3 can host it later.
- **OpenHands via Portal/LiteLLM (Q7).** *Why:* the greenfield path for now is "Hermes research →
  HumanLayer Linear ticket → Claude Code executes." Claude Code Max cannot back OpenHands (OAuth
  tokens blocked in third-party tools); point OpenHands at the Portal OpenAI-compatible endpoint
  via LiteLLM (`LLM_MODEL`/`LLM_API_KEY`/`LLM_BASE_URL`) to avoid a separate Anthropic key.
- **Second-account "fresh setup" walkthrough (Q4/Q8b).** *Why:* the single-account /
  multiple-profiles topology is what makes the shared Kanban board work (Hermes has no cross-host
  / cross-account coordination primitive); a two-account setup is future-only.

*(The video authenticity item was promoted to **P0** in Part B — it's competition-relevant and
small, so it's no longer a "someday" deferral.)*

---

## Part D — closeout: author the NEXT full-build epic (recurring)

When this epic's backlog (P0–P4) is substantially actioned — or at the next planning boundary —
the **final step is to author the next full-build epic (GLO-14)**, mirroring how Phase 5 of the
original build authored THIS epic (GLO-13). The next epic should: roll forward whatever remains of
Part C, fold in items discovered while executing P0–P4 (new gaps the auditor / PMF loops surface,
new competition or product requirements), and re-prioritize. Snapshot it to `tickets/<ID>.md` on
filing (AGENTS.md rule 7). This keeps the backlog self-perpetuating and git history the
authoritative, always-current roadmap.

---

## Acceptance criteria (for the full-build epic)
- [ ] An engineer (or HumanLayer worktree) can rebuild the entire stack from this ticket + the
      three docs, with no missing step.
- [ ] The prioritized backlog P0→P4 is actioned in order, each as its own sub-issue when picked up.
- [ ] P0 (demo video authenticity) is done first as the quick-win; P1 (egress hardening) and P2
      (Stripe) — the two competition requirements — follow as the top functional priorities.
- [ ] Each deferred item states scope + the reason it was deferred (done above).
- [ ] On closeout, the NEXT full-build epic (GLO-14) is authored (Part D) capturing Part C
      remainder + newly discovered items, and snapshotted into `tickets/`.
"""


NEXT_TITLE = "[Full-Build] Sovereign CTO Stack — next epic (GLO-13 P0–P4 shipped) + rolled-forward backlog"

NEXT_EPIC_DESCRIPTION = r"""## What this is

The **next full-build epic** for the Sovereign CTO Stack — authored on the GLO-13 closeout
(Part D recurrence: "the final step is to author the next full-build epic", mirroring how Phase 5
of the original build authored GLO-13). GLO-13 captured the complete vision and its prioritized
backlog P0–P4; that backlog is now **built and gated** on-branch. This epic rolls forward whatever
remains (GLO-13 Part C) and folds in the concrete items discovered while executing P0–P4, so git
history stays the self-perpetuating, always-current roadmap.

Public repo: https://github.com/dyrtyData/sovereign-cto-stack · decision record:
`docs/system-design-tradeoffs.md` · CTO-function map: `docs/cto-functions.md` · setup:
`docs/setup-guide.md`. Git history is the authoritative decision record; mem0 is a complement.

---

## Part A — what GLO-13 delivered (Phases 0–5 + the P0–P4 backlog, all gated)

GLO-13 shipped the entire phased build as thin, gated, verifiable slices — recorded here so this
epic stands alone:

### Phase 0 — Public-safe repo skeleton + prerequisites gate
Standalone gitignored-by-parent repo; `.env.example`; strict `.gitignore`; `docker-compose.yml`;
`scripts/preflight.sh` halts on missing keys. (gitleaks clean, `docker compose config -q`.)

### Phase 1 — Hermes orchestrator boots (Portal + mem0 + Telegram)
Hermes v0.17.0; Portal OAuth; self-hosted mem0 on pgvector (SDK-on-host); Telegram gateway.

### Phase 2 — CTO knowledge RAG brain (`query_cto_knowledge`)
Textbook corpus → `corpus/*.md`; local Vector MCP sidecar (MiniLM + LanceDB + FastMCP);
consulted before every CTO function, citing the union of returned source files.

### Phase 3 — Tech-debt auditor loop (graphify → grounded `[Brownfield]` ticket) — HERO
graphify static map; `service_topology.py` derives coupling (frontend=7, checkout=6); the
`CTO-Architecture` profile multi-angle-grounds and files HumanLayer-ready `[Brownfield]` tickets
(GLO-8/9/10/11, then GLO-15/GLO-16 re-centered on the billing-path hub).

### Phase 4 — PMF research profile + autonomous-run `.mp4` recording
`CTO-Market` profile over the shared Kanban; `pmf_brief` skill → cited brief → one `[Product]`
ticket (GLO-12); Xvfb+ffmpeg recorder capturing a live split-screen.

### Phase 5 — Documentation finalization + the GLO-13 full-build epic
`setup-guide.md` / `system-design-tradeoffs.md` / `cto-functions.md`; ticket-tracking wired into
the workflow; the comprehensive full-build ticket (GLO-13).

### The GLO-13 P0–P4 backlog (built + gated this pass — recap, for self-containment)
The GLO-13 prioritized deferred backlog shipped in order, each with an exit-0 gate:

- **P0 — Demo video authenticity** (`assert_demo_authenticity.py`): real `agent.tool_executor`
  tool-call lines stream into the recorded run. (GLO-13 promoted this from the original video-
  **authenticity** "someday" deferral to a P0 quick-win.)
- **P1 — NemoClaw / OpenShell egress hardening** (`assert_egress_policy.py`): deny-by-default
  egress enforced by a real NVIDIA OpenShell sandbox loading `policy.yaml`; the load-bearing
  negative test refuses a non-allow-listed CONNECT (403), positive path `api.linear.app:443` (200).
- **P2 — Stripe** (`assert_stripe_grounding.py`): real test-mode **MRR** $1,281/mo / 25% churn / 3
  cohorts ground the PMF brief's AARRR Revenue/Retention (vs assumptions).
- **P3 — SonarQube** DETECT + **graphify (KEEP IT)** for cross-service coupling → **Hermes
  (JUDGMENT)** → **Codegen** for novel fixes / **Moderne** for recipe-amenable debt
  (`assert_sonar_fusion.py`): 240 real SonarQube issues fused onto `service-coupling.json`; GLO-16
  cites a SonarQube issue + the billing-path coupling hub + Codegen. (GLO-12, the PMF `[Product]`
  ticket, independently proposed exactly this autonomous-remediation gap.)
- **P4 — PMF** full version, **RICE/ICE**-ranked (`assert_pmf_ranked.py`): 3 ranked opportunities +
  a shipped-bet ledger + a prior-decisions consult (self-hosted mem0 + git) that does not
  re-propose the already-decided GLO-12 bet.
- **Closeout** — hybrid-montage showcase video (`assert_showcase_video.py`) + this next epic.

---

## Part B — rolled-forward + newly-discovered backlog (build in this order)

### P1 — NemoClaw / OpenShell: REAL passive long-lived mem0 memory capture on every run (newly discovered, top priority)
**Scope.** mem0 is verified working (self-hosted on pgvector; `assert_pmf_ranked.py`'s prior-
decisions consult round-trips it live), but the configured `memories` collection is **empty** —
only test/seed rows exist; **nothing accumulates over time**. The agent loops (tech-debt audit,
PMF, every CTO function) must **write each decision to the configured mem0 `memories` collection
on every run** — passive, long-lived memory capture — so the system genuinely remembers what it
decided and why across runs, not just re-seeds from the tracked `tickets/` snapshots. Git history
stays authoritative (`policy.yaml` of the mind: mem0 is a complement, never a dependency), but the
recall convenience must actually fill up. This is the user's explicitly-requested GLO-14 item.
**Rationale.** Today the loop *reads* prior decisions (seeded from `tickets/[Product]` + git) but
never *writes* new ones, so the memory never grows. Closing the write path is the difference
between a demo of memory and a system that learns. Highest priority — it is load-bearing for the
self-learning judgment-layer story and is the smallest, highest-signal gap.

### P2 — Autonomous PR-review loop: HumanLayer PR → Hermes resume → Greptile review → triage (newly discovered)
**Scope.** Close the full autonomy loop. When HumanLayer opens a PR, fire a GitHub `pull_request`
(opened/synchronize) **webhook** into Hermes' existing `hermes webhook` receiver so the orchestrator
**resumes** and **kicks off a Greptile review** of the PR, then **ingests Greptile's findings and
triages them** — grounding each via `query_cto_knowledge` and filing `[Brownfield]` follow-ups /
a Kanban card (or requesting changes) rather than leaving them as raw inline comments. Net loop:
plan → implement → PR (HumanLayer) → `pull_request` webhook → Hermes → Greptile review → triage →
new grounded tickets.
**Design notes.** Greptile also ships a GitHub App that auto-reviews on PR-open with no custom hook;
routing *through Hermes* is what adds the sovereign-CTO payoff — the **triage/grounding step** that
turns review comments into prioritized, textbook-grounded work. Capture both paths; the webhook +
triage is the load-bearing build. Keep egress deny-by-default (the Greptile/GitHub endpoints join
the `policy.yaml` allow-list).
**Rationale.** Turns the repo from "agents that ship code" into "agents that ship *and review* code"
— the missing half of an autonomous engineering factory. Sequenced after the memory-capture (P1)
so review-triage decisions also accumulate into long-lived memory.

### P3 — Real-Linear-UI demo ending (persistent authenticated Chromium profile)
**Scope.** The P0 ticket-in-browser ending currently renders the **local** `tickets/GLO-NN.md`
snapshot to a self-contained `file://` HTML because the throwaway container Chromium has no Linear
session and the live ticket URL hits Linear's **auth wall**. Roll forward the *real* ending: a
persistent, authenticated Chromium profile (mounted user-data-dir with a saved Linear session, or
a short OAuth bootstrap) so the recording can end on the **actual Linear ticket page** in the UI.
**Rationale.** The local-snapshot HTML is honest and reproducible (and the right default), but the
real-Linear-UI ending is more convincing for the submission. Captured here as the deliberate next
step rather than fragile session plumbing on the deadline.

### P4 — Host-orchestrator egress confinement via OpenShell's MicroVM driver (still NemoClaw, deeper)
**Scope.** This DOES use NemoClaw/OpenShell — it is the SAME stack GLO-13 P1 shipped, switched to
OpenShell's **MicroVM compute driver** (libkrun + Apple Hypervisor.framework, OpenShell Option B)
instead of the **container** driver. P1 (container driver) confines the **containerized sub-tools**
(the sandbox demonstrably refuses a non-allow-listed CONNECT). P4 confines the **host Hermes
orchestrator's OWN egress** — the orchestrator runs on the macOS host, *outside* any sandbox today —
by running it inside an OpenShell-managed MicroVM. i.e. "use NemoClaw to sandbox the brain too,"
not a different tool and not a re-do of P1. Already recorded in `docs/system-design-tradeoffs.md`.
Inference stays cloud (no CUDA on Apple Silicon); watch the Landlock `best_effort` and
`inference.local` mDNS macOS bugs.
**Rationale.** Strongest confinement, biggest moving-parts/DNS risk — sequenced after the
load-bearing containerized layer that ships today (An Elegant Puzzle: sequence the hardening).

### P5 — PMF → product loop: real shipped-bet feedback (close the North Star loop)
**Scope.** EXTENDS the GLO-13 P4 PMF loop that already SHIPPED (it ranks opportunities RICE/ICE
and records a `shipped` field in `recordings/pmf_ledger.json`) — but nothing flips
`shipped:false → true` from real outcomes yet. Wire the actual feedback signal (a shipped bet's
measured result) back into the ranking so the North Star — **opportunities shipped**, not tickets
filed — is computed from reality, grounded in real usage + Stripe data.
**Rationale.** Closes the learning loop the GLO-13 P4 slice scaffolded; depends on accumulated
usage data, so it follows the memory-capture (P1) work.

### P6 — Moderne / OpenRewrite paid-tier evaluation (LOWEST priority — paid, no account yet)
**Scope.** Evaluate **Moderne / OpenRewrite** (no free tier — paid; no account provisioned yet, so
deliberately last) as the deterministic, recipe-based mass-refactor back-end ALONGSIDE Codegen:
Codegen for NOVEL, judgment-heavy fixes; Moderne for RECIPE-AMENABLE mechanical debt
(dependency/framework upgrades, broad languages incl. Java, which Codegen does not cover). GLO-16
already routes its billing-path refactor to Codegen and explicitly defers the Moderne evaluation
here. Register the Moderne local MCP (`mod config agent-tools install`) under
`hermes/config.yaml mcp_servers` and pilot one recipe.
**Rationale.** The Hermes JUDGMENT layer should route each ticket to the right remediation
back-end; without Moderne, recipe-amenable + Java debt has no autonomous path. Paid-tier with no
account yet, so it is a future evaluation/decision item — moved to the end of the backlog.

---

## Part C — rolled-forward original deferred items (with rationale)

- **Full mem0 OSS server + Next.js dashboard** (from GLO-13 Phase 1 / Part C). *Why still
  deferred:* the SDK-on-host path verifies every phase; the dashboard is a visualization nicety.
  Now more relevant once P1 above makes the `memories` collection actually fill up — a dashboard
  over a growing memory is worth more than over an empty one.
- **OpenHands via Portal/LiteLLM** (from GLO-13 Part C). *Why:* the greenfield path stays "Hermes
  research → HumanLayer Linear ticket → Claude Code executes"; point OpenHands at the Portal
  OpenAI-compatible endpoint via LiteLLM to avoid a separate Anthropic key when picked up.
- **Second-account "fresh setup" walkthrough** (from GLO-13 Part C). *Why:* single-account /
  multiple-profiles is what makes the shared Kanban work; two-account is future-only.

*(GLO-13's demo-authenticity item was promoted to P0 and is now shipped; its real-Linear-UI ending
is rolled forward as P3 above.)*

---

## Part D — closeout: author the NEXT full-build epic (recurring)

When this epic's backlog is substantially actioned — or at the next planning boundary — author the
**next** full-build epic, rolling forward whatever remains, folding in items discovered while
executing this backlog, and re-prioritizing. Snapshot it to `tickets/<ID>.md` on filing
(AGENTS.md rule 7). Self-perpetuating roadmap; git history is the authoritative record.

---

## Acceptance criteria (for this full-build epic)
- [ ] mem0 `memories` collection ACCUMULATES — every agent run writes its decision; a fresh query
      after N runs returns prior-run decisions that were never seeded from `tickets/`.
- [ ] Moderne/OpenRewrite evaluated: one recipe piloted, the route-to-Moderne decision recorded in
      `docs/system-design-tradeoffs.md` with cost/benefit vs Codegen.
- [ ] The recorded demo CAN end on the real Linear ticket UI (authenticated Chromium profile), with
      the local-snapshot HTML retained as the reproducible default.
- [ ] Host-orchestrator MicroVM confinement scoped (or built) with the macOS-bug tradeoffs recorded.
- [ ] Each rolled-forward item states scope + rationale (done above).
- [ ] On closeout, the NEXT full-build epic is authored (Part D) and snapshotted into `tickets/`.
"""


CLOSEOUT_TITLE = (
    "[Full-Build] Sovereign CTO Stack — next epic (GLO-14 learn/review/feedback shipped) "
    "+ rolled-forward backlog"
)

CLOSEOUT_EPIC_DESCRIPTION = r"""## What this is

The **next full-build epic** for the Sovereign CTO Stack — authored on the **GLO-14** closeout
(Part D recurrence: "the final step is to author the next full-build epic", mirroring how GLO-13's
Phase 5 authored GLO-14). GLO-14 made the system actually **learn and review**: it closed mem0's
write path so `memories` accumulates run-over-run (P1), had every filed ticket prompt a Greptile PR
review (P2), flipped the PMF North Star from a real Stripe-grounded outcome (P5), told a fuller
authenticated demo (P3 / D-2), and spiked host-orchestrator MicroVM confinement (P4) — each behind
an exit-0 `assert_*.py` gate. This epic rolls forward GLO-14's Part C deferrals and folds in the
concrete items discovered while building P1–P5, so git history stays the self-perpetuating,
always-current roadmap.

Public repo: https://github.com/dyrtyData/sovereign-cto-stack · decision record:
`docs/system-design-tradeoffs.md` · CTO-function map: `docs/cto-functions.md` · setup:
`docs/setup-guide.md`. Git history is the authoritative decision record; mem0 is a complement.

---

## Part A — what GLO-14 delivered (the learn / review / feedback loops, all gated)

GLO-14 shipped seven thin, gated, verifiable slices on top of GLO-13's phased build:

- **P1 — mem0 OSS ≥ v2.0.0 upgrade** (`scripts/mem0_roundtrip.py`): pinned `mem0ai>=2.0.0`
  (resolved 2.0.10); native entity-linking replaces external graph DBs (no Neo4j); the round-trip
  smoke asserts the v2 return shape and self-skips the `infer=True` entity-link proof when Ollama
  is absent.
- **P2 — Close the mem0 write path** (`scripts/assert_memory_accumulates.py`): a deterministic
  `mem0_record_decision.py` writes each filed decision into the unified `memories` collection with
  `infer=True`, between ticket-filing and snapshot in **both** loops; the PMF consult reads the same
  collection. Two runs both grow the count, run 2 recalls run 1, and the recalled text is absent
  from every `tickets/*.md` (accumulated, not re-seeded).
- **P3 — Greptile ticket-instruction line** (`scripts/assert_greptile_instruction.py`): every filed
  ticket carries a standing "run Greptile on the PR" line; the gate reads it back from the live
  ticket + the snapshot. The Greptile CLI / skill / `/greptile` command live **globally in
  `~/.claude`, out of repo** (a project-agnostic prerequisite, not a repo deliverable).
- **P5 — PMF shipped-bet flip** (`scripts/assert_shipped_flip.py`): a Stripe-grounded shipped-result
  record flips the matching `pmf_ledger.json` row `false → true`; the recorded metric must equal a
  real `stripe_metrics.json` value (no fabrication), unrelated rows untouched, atomic write.
- **P3 / D-2 — Fuller demo + memory view + authenticated Linear ending**
  (`scripts/assert_showcase_video.py`, `render_memory_card.py`, `assert_memory_view_grows.py`): the
  montage surfaces more components and can end on the **real** authenticated Linear ticket UI
  (persistent Chromium profile), with the `file://` snapshot as the reproducible default; a
  read-only memory view proves `memories` grows.
- **P4 — Host-orchestrator MicroVM confinement spike** (`scripts/assert_microvm_spike.py`): the
  OpenShell `vm` driver (libkrun + Apple Hypervisor.framework) was spiked to the driver-binds layer
  and a dated **NO-GO** go/no-go recorded with the four macOS limitations (Q9 Option A: scoped, not
  built).
- **Closeout** — Part C deferral capture + this next epic (`scripts/assert_closeout_ready.py` gates
  the D-6 boundary: every prior gate exit-0 + the GLO-14 acceptance checklist fully ticked).

---

## Part B — rolled-forward + newly-discovered backlog (build in this order)

### P1 — mem0 OSS server + read-only Next.js memory dashboard (rolled forward — now worth building)
**Scope.** GLO-14 built a *lightweight static* read-only memory view (`render_memory_card.py`) that
proves the `memories` collection grows. Roll forward the **full mem0 OSS server + a small Next.js
read-only dashboard** over the now-accumulating collection — entity links, per-run decision rows,
search — as the standing visualization surface (no frontend exists in the repo yet).
**Rationale.** Deferred in GLO-14 (Q12) because the static card verifies the phase and no frontend
scaffolding exists; now that P1/P2 made `memories` actually fill up, a dashboard over a growing
memory is worth materially more than over an empty one. Read-only — mem0 stays a recall complement,
git stays authoritative.

### P2 — Moderne / OpenRewrite remediation back-end (rolled forward — needs an account OR the OSS pilot)
**Scope.** Evaluate **Moderne / OpenRewrite** as the deterministic, recipe-based mass-refactor
back-end ALONGSIDE Codegen: Codegen for NOVEL, judgment-heavy fixes; Moderne for RECIPE-AMENABLE
mechanical debt (dependency/framework upgrades, broad languages incl. Java, which Codegen does not
cover). Two paths: (a) provision a Moderne account and register the local MCP
(`mod config agent-tools install`) under `hermes/config.yaml mcp_servers` — the **commented stub is
already staged** in that file (deferred, not registered); or (b) pilot **OpenRewrite OSS** directly
(no account) on one recipe-amenable change and record the route-to-Moderne decision with cost/benefit
vs Codegen in `docs/system-design-tradeoffs.md`.
**Rationale.** GLO-14 moved this from an active backlog item to a Part C deferral (Q11) because no
Moderne account is provisioned; remediation continues to route to Codegen ("named-only"). The
OpenRewrite-OSS-pilot option is preserved so a recipe can be piloted without a paid account when the
decision is made — the Hermes JUDGMENT layer should route each ticket to the right back-end.

### P3 — Autonomous PR-review TRIAGE loop (rolled forward, deeper than GLO-14 P2)
**Scope.** GLO-14 P2 deliberately decoupled Greptile to a *global, out-of-repo* skill that
HumanLayer-on-Claude-Code runs on the PR (the only in-repo deliverable being the ticket-instruction
line). The deeper, in-repo version — captured but **not** built in GLO-14 — is to **ingest Greptile's
findings back into Hermes** and triage them: ground each via `query_cto_knowledge` and file
`[Brownfield]` follow-ups / Kanban cards rather than leaving raw inline comments. Keep egress
deny-by-default (any Greptile/GitHub endpoint joins `egress/policy.yaml`).
**Rationale.** Turns "agents that ship + review" into "agents that ship, review, *and re-prioritize
from the review*" — the triage/grounding step is the sovereign-CTO white space. Deferred in GLO-14
in favour of the clean global-skill decoupling; rolled forward as the next autonomy increment.

### P4 — mem0 passive capture via its OpenAI-compatible proxy (rolled forward — considered + rejected for now)
**Scope.** GLO-14's Q3 probe confirmed the closed-source `hermes-agent` binary does **not** write
`memories` natively, so the deterministic `mem0_record_decision.py` writer is load-bearing. The only
"passive, as-intended" route is to chain inference through mem0's OpenAI-compatible proxy
(`mem0.proxy.main.Mem0 → hermes proxy :8645 → Nous`), with mem0 silently `add()`-ing every turn.
Evaluate adopting it deliberately if the tradeoff ever becomes worth it.
**Rationale.** Rejected for GLO-14 because it places mem0 **in the critical inference hot path** (a
mem0 outage breaks every agent call) and captures noisy raw turns instead of curated, tagged,
gate-able decisions — violating the standing rule that mem0 is a recall complement, never
load-bearing (git stays authoritative). The exact enablement path is recorded in
`docs/system-design-tradeoffs.md` so a future epic can adopt it on purpose.

### P5 — Host-orchestrator MicroVM confinement: BUILD the deferred remainder (rolled forward from GLO-14 P4)
**Scope.** GLO-14 P4 spiked the OpenShell `vm` driver to the **driver-binds** layer and recorded a
dated **NO-GO** for a default build (Q9 Option A). Build the deferred remainder once the fragile
surface is de-risked: gateway reconfigure to `OPENSHELL_DRIVERS=vm`, a guest bootstrap image +
guest-TLS, run the host orchestrator end-to-end inside the MicroVM, and clear the four documented
macOS limitations (Landlock `best_effort` no-op on XNU, mDNS `.local` non-traversal, no CUDA,
case-sensitive-APFS virtio-fs).
**Rationale.** Strongest confinement (confines the host "brain" itself), biggest moving-parts / DNS
risk — sequenced late, after the spike cleared the cheapest risk (does the driver boot? yes).

### P6 — OpenHands via Portal/LiteLLM + the second-account "fresh setup" walkthrough (rolled forward)
**Scope.** (a) **OpenHands** autonomous greenfield prototyping, pointed at the Nous Portal
OpenAI-compatible endpoint via **LiteLLM** (`LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL`) to avoid a
separate Anthropic key (Claude Code Max OAuth tokens are blocked in third-party tools). (b) A
**second-account fresh-setup walkthrough** documenting a two-account topology.
**Rationale.** The greenfield path stays "Hermes research → HumanLayer Linear ticket → Claude Code
executes" for now; the single-account / multiple-profiles topology is what makes the shared Kanban
board work (Hermes has no cross-account coordination primitive). Both are future-only, hence last.

---

## Part C — rolled-forward original deferred items + GLO-14 discoveries (with rationale)

- **Greptile global setup (out-of-repo prerequisite).** *Why out of repo:* the Greptile CLI + Claude
  Code skill + `/greptile` command are set up **globally in `~/.claude`** (project-agnostic; a
  separate task — `greptile login` once, install/adapt `github.com/greptileai/skills`). This repo's
  sole Greptile surface is the ticket-instruction line; the global setup is a prerequisite, not a
  GLO-14/next-epic repo deliverable. Recorded so a fresh clone knows the dependency.
- **Live-profile skill-deploy step (discovered building GLO-14 P3).** *Why:* the Greptile
  instruction line lives in the tracked `hermes/skills/*.md`, but Hermes reads from the live
  `~/.hermes` profile dirs — so a deploy step that syncs the tracked skills into each live profile is
  required for the instruction to actually fire. Capture it as a documented setup step / small script.
- **Duplicate-finding dedupe (discovered building GLO-14).** *Why:* re-filing `[Brownfield]` tickets
  produced duplicate issues (GLO-8/9/10/11 → re-centered GLO-15/16); a dedupe step that detects and
  consolidates near-duplicate filed tickets keeps the tracker and `tickets/` snapshots clean.
- **Full mem0 OSS server + Next.js dashboard** (promoted to P1 above). *Why now:* see P1 rationale —
  worth building once the collection accumulates.
- **mem0 passive capture via the proxy** (promoted to P4 above). *Why still deferred:* see P4 —
  keeps mem0 off the critical inference hot path.
- **OpenHands via Portal/LiteLLM** + the **second-account walkthrough** (promoted to P6 above).
  *Why:* future-only, see P6 rationale.
- **Moderne/OpenRewrite** (promoted to P2 above; OSS-pilot option preserved). *Why:* see P2 — no
  account provisioned; the OSS pilot is the no-account path.

---

## Part D — closeout: author the NEXT full-build epic (recurring)

When this epic's backlog is substantially actioned — or at the next planning boundary — author the
**next** full-build epic, rolling forward whatever remains, folding in items discovered while
executing this backlog, and re-prioritizing. Snapshot it to `tickets/<ID>.md` on filing
(AGENTS.md rule 7). Self-perpetuating roadmap; git history is the authoritative record.

---

## Acceptance criteria (for this full-build epic)
- [ ] A read-only mem0 dashboard (or the full OSS server + Next.js view) renders the now-accumulating
      `memories` collection (entity links + per-run decisions).
- [ ] Moderne/OpenRewrite is either account-provisioned + MCP-registered, or one OSS recipe is
      piloted, with the route-to-Moderne decision recorded vs Codegen in
      `docs/system-design-tradeoffs.md`.
- [ ] Greptile findings are ingested back into Hermes and triaged into grounded follow-ups (the
      deeper in-repo PR-review loop), with egress deny-by-default preserved.
- [ ] Host-orchestrator MicroVM confinement is BUILT (the GLO-14 spike's deferred remainder) or the
      go/no-go is re-confirmed with updated evidence.
- [ ] Each rolled-forward item states scope + rationale (done above), incl. the Greptile global
      prerequisite, the live-profile skill-deploy step, and the duplicate-finding dedupe need.
- [ ] Every Hermes-filed ticket is associated with the **`sovereign-cto-stack` Linear project**
      (not loose in the backlog) — `save_issue` sets `project` in both the scripts and the filing
      skills.
- [ ] **After everything is complete:** hard-copy this task's HumanLayer artifacts
      (`.humanlayer/tasks/<task>/*.md` — research questions, research, design discussion, structure
      outline, ticket) into **`docs/task-artifacts/<task>/`**, scrubbed of any secrets and **NOT**
      gitignored, and commit (to `main` once merged). This makes them visible to repomix / gitingest
      (which skip gitignored paths) so the whole decision trail flattens into context. Standing
      recurrence for every epic in this repo.
- [ ] On closeout, the NEXT full-build epic is authored (Part D) and snapshotted into `tickets/`.
"""


def find_closeout_epic() -> str | None:
    """Find the GLO-14-closeout-authored next epic by its distinctive title prefix.

    The fuzzy "Full-Build" search can lag the index for a just-filed ticket, so also scan the
    recent createdAt list — this keeps re-runs idempotent (update in place, never re-file).
    """
    prefix = "[Full-Build] Sovereign CTO Stack — next epic (GLO-14"
    for params in (
        {"query": "Full-Build", "team": L.TEAM, "limit": 50},
        {"team": L.TEAM, "limit": 50, "orderBy": "createdAt"},
    ):
        res = L.tool("list_issues", params)
        issues = res.get("issues", res) if isinstance(res, dict) else res
        for i in issues or []:
            if str(i.get("title", "")).startswith(prefix):
                return i.get("id") or i.get("identifier")
    return None


def find_existing(prefix_title: str = "[Full-Build] Sovereign CTO Stack — complete vision") -> str | None:
    """Find the ORIGINAL GLO-13 full-build epic (by its specific title prefix).

    Both GLO-13 and the next epic (GLO-14) carry the `[Full-Build]` label and a
    `[Full-Build]` title, so match on the distinctive GLO-13 title prefix rather
    than the bare bracket tag (which would also match GLO-14).
    """
    res = L.tool("list_issues", {"query": "Full-Build", "team": L.TEAM, "limit": 50})
    issues = res.get("issues", res) if isinstance(res, dict) else res
    for i in issues or []:
        if str(i.get("title", "")).startswith(prefix_title):
            return i.get("id") or i.get("identifier")
    return None


def find_next_epic() -> str | None:
    """Find the next-epic full-build ticket by its distinctive title prefix."""
    res = L.tool("list_issues", {"query": "Full-Build", "team": L.TEAM, "limit": 50})
    issues = res.get("issues", res) if isinstance(res, dict) else res
    for i in issues or []:
        if str(i.get("title", "")).startswith("[Full-Build] Sovereign CTO Stack — next epic"):
            return i.get("id") or i.get("identifier")
    return None


def main(argv: list[str]) -> int:
    L.init()

    # `--next-epic` authors GLO-14 (the epic GLO-13's closeout authored); `--closeout-epic`
    # authors the epic AFTER GLO-14 (the GLO-14 closeout recurrence — Linear assigns the id);
    # any remaining positional arg is the id to update in place. Default mode files/updates the
    # original GLO-13 [Full-Build] epic.
    next_epic = False
    closeout_epic = False
    rest: list[str] = []
    for a in argv:
        if a in ("--next-epic", "--next"):
            next_epic = True
        elif a in ("--closeout-epic", "--closeout"):
            closeout_epic = True
        else:
            rest.append(a)

    if closeout_epic:
        title, description = CLOSEOUT_TITLE, CLOSEOUT_EPIC_DESCRIPTION
        # No fixed slot: this epic gets the next free GLO-NN Linear assigns (after GLO-19).
        # Update in place only if explicitly given an id (positional / env) or if a prior run
        # already filed it (matched by its distinctive title prefix). NEVER reuse the GLO-14 slot.
        issue_id = (rest[0] if rest else None) or os.environ.get("CLOSEOUT_EPIC_ID") \
            or find_closeout_epic()
        what = "closeout-epic"
    elif next_epic:
        title, description = NEXT_TITLE, NEXT_EPIC_DESCRIPTION
        issue_id = (rest[0] if rest else None) or os.environ.get("NEXT_EPIC_ID") or find_next_epic()
        # Reuse the GLO-14 slot if it currently holds a superseded Brownfield
        # duplicate (GLO-15/GLO-16 are the canonical re-filings). Repurposing it
        # keeps the next epic at the conventional GLO-14 id without leaving a stale
        # duplicate; nothing is lost (the snapshot is regenerated below).
        if not issue_id:
            issue_id = "GLO-14"
        what = "next-epic"
    else:
        title, description = TITLE, DESCRIPTION
        issue_id = (rest[0] if rest else None) or os.environ.get("FULLBUILD_ID") or find_existing()
        what = "full-build"

    # Every filed ticket carries the standing Greptile review instruction (GLO-14 P2). Append
    # it idempotently so re-filing in place doesn't stack duplicate sections.
    if GREPTILE_INSTRUCTION not in description:
        description = description.rstrip() + GREPTILE_REVIEW_SECTION

    args = {
        "title": title,
        "team": L.TEAM,
        "project": L.PROJECT,
        "labels": ["Full-Build"],
        "priority": 2,
        "description": description,
    }
    if issue_id:
        args["id"] = issue_id
        print(f"updating {what} ticket {issue_id} in place")
    else:
        print(f"creating new {what} ticket")

    res = L.tool("save_issue", args)
    issue = res.get("issue", res) if isinstance(res, dict) else res
    ident = (issue or {}).get("id") or (issue or {}).get("identifier")
    url = (issue or {}).get("url", "")
    if not ident:
        print(f"FAIL: save_issue returned no id: {res!r}", file=sys.stderr)
        return 1
    print(f"OK: {what} ticket {ident} — {url}")

    # Phase-5 ticket tracking: snapshot it into git.
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "snapshot_tickets.py"), ident],
                   check=False)
    print(ident)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
