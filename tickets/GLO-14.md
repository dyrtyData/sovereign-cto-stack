# GLO-14 — [Full-Build] Sovereign CTO Stack — next epic (GLO-13 P0–P4 shipped) + rolled-forward backlog

- **identifier:** GLO-14
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled
- **team:** Global South Ai Safety
- **status:** Backlog
- **labels:** Full-Build
- **priority:** High (2)
- **snapshot captured:** 2026-06-28T20:02:53+00:00

## Description

## What this is

The **next full-build epic** for the Sovereign CTO Stack — authored on the <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> closeout
(Part D recurrence: "the final step is to author the next full-build epic", mirroring how Phase 5
of the original build authored <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue>). <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> captured the complete vision and its prioritized
backlog P0–P4; that backlog is now **built and gated** on-branch. This epic rolls forward whatever
remains (<issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> Part C) and folds in the concrete items discovered while executing P0–P4, so git
history stays the self-perpetuating, always-current roadmap.

Public repo: [https://github.com/dyrtyData/sovereign-cto-stack](<https://github.com/dyrtyData/sovereign-cto-stack>) · decision record:
`docs/system-design-tradeoffs.md` · CTO-function map: `docs/cto-functions.md` · setup:
`docs/setup-guide.md`. Git history is the authoritative decision record; mem0 is a complement.

---

## Part A — what <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> delivered (Phases 0–5 + the P0–P4 backlog, all gated)

<issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> shipped the entire phased build as thin, gated, verifiable slices — recorded here so this
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
(<issue id="9b8ed28f-a84c-406d-a141-fe8bd84e1d46" href="https://linear.app/global-south-ai-safety/issue/GLO-8/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-backend">GLO-8</issue>/9/10/11, then <issue id="ef6ce1dd-6c47-4875-ac1e-234e7129154f" href="https://linear.app/global-south-ai-safety/issue/GLO-15/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-backend">GLO-15</issue>/<issue id="fa4a8772-3428-459f-90c3-d5cd77cbbe11" href="https://linear.app/global-south-ai-safety/issue/GLO-16/brownfield-checkoutservice-billing-path-grpc-coupling-hub-degree-6">GLO-16</issue> re-centered on the billing-path hub).

### Phase 4 — PMF research profile + autonomous-run `.mp4` recording

`CTO-Market` profile over the shared Kanban; `pmf_brief` skill → cited brief → one `[Product]`
ticket (<issue id="43187d4c-dfc8-4755-8c0c-4efec4574a4a" href="https://linear.app/global-south-ai-safety/issue/GLO-12/product-tech-debt-auditor-stops-at-diagnosis-add-autonomous">GLO-12</issue>); Xvfb+ffmpeg recorder capturing a live split-screen.

### Phase 5 — Documentation finalization + the <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> full-build epic

`setup-guide.md` / `system-design-tradeoffs.md` / `cto-functions.md`; ticket-tracking wired into
the workflow; the comprehensive full-build ticket (<issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue>).

### The <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> P0–P4 backlog (built + gated this pass — recap, for self-containment)

The <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> prioritized deferred backlog shipped in order, each with an exit-0 gate:

* **P0 — Demo video authenticity** (`assert_demo_authenticity.py`): real `agent.tool_executor`
  tool-call lines stream into the recorded run. (<issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> promoted this from the original video-
  **authenticity** "someday" deferral to a P0 quick-win.)
* **P1 — NemoClaw / OpenShell egress hardening** (`assert_egress_policy.py`): deny-by-default
  egress enforced by a real NVIDIA OpenShell sandbox loading `policy.yaml`; the load-bearing
  negative test refuses a non-allow-listed CONNECT (403), positive path `api.linear.app:443` (200).
* **P2 — Stripe** (`assert_stripe_grounding.py`): real test-mode **MRR** $1,281/mo / 25% churn / 3
  cohorts ground the PMF brief's AARRR Revenue/Retention (vs assumptions).
* **P3 — SonarQube** DETECT + **graphify (KEEP IT)** for cross-service coupling → **Hermes****
****(JUDGMENT)** → **Codegen** for novel fixes / **Moderne** for recipe-amenable debt
  (`assert_sonar_fusion.py`): 240 real SonarQube issues fused onto `service-coupling.json`; <issue id="fa4a8772-3428-459f-90c3-d5cd77cbbe11" href="https://linear.app/global-south-ai-safety/issue/GLO-16/brownfield-checkoutservice-billing-path-grpc-coupling-hub-degree-6">GLO-16</issue>
  cites a SonarQube issue + the billing-path coupling hub + Codegen. (<issue id="43187d4c-dfc8-4755-8c0c-4efec4574a4a" href="https://linear.app/global-south-ai-safety/issue/GLO-12/product-tech-debt-auditor-stops-at-diagnosis-add-autonomous">GLO-12</issue>, the PMF `[Product]`
  ticket, independently proposed exactly this autonomous-remediation gap.)
* **P4 — PMF** full version, **RICE/ICE**-ranked (`assert_pmf_ranked.py`): 3 ranked opportunities +
  a shipped-bet ledger + a prior-decisions consult (self-hosted mem0 + git) that does not
  re-propose the already-decided <issue id="43187d4c-dfc8-4755-8c0c-4efec4574a4a" href="https://linear.app/global-south-ai-safety/issue/GLO-12/product-tech-debt-auditor-stops-at-diagnosis-add-autonomous">GLO-12</issue> bet.
* **Closeout** — hybrid-montage showcase video (`assert_showcase_video.py`) + this next epic.

---

## Part B — rolled-forward + newly-discovered backlog (build in this order)

### P1 — NemoClaw / OpenShell: REAL passive long-lived mem0 memory capture on every run (newly discovered, top priority)

**Scope.** mem0 is verified working (self-hosted on pgvector; `assert_pmf_ranked.py`'s prior-
decisions consult round-trips it live), but the configured `memories` collection is **empty** —
only test/seed rows exist; **nothing accumulates over time**. The agent loops (tech-debt audit,
PMF, every CTO function) must **write each decision to the configured mem0** `memories` **collection****
****on every run** — passive, long-lived memory capture — so the system genuinely remembers what it
decided and why across runs, not just re-seeds from the tracked `tickets/` snapshots. Git history
stays authoritative (`policy.yaml` of the mind: mem0 is a complement, never a dependency), but the
recall convenience must actually fill up. This is the user's explicitly-requested <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> item.
**Rationale.** Today the loop *reads* prior decisions (seeded from `tickets/[Product]` + git) but
never *writes* new ones, so the memory never grows. Closing the write path is the difference
between a demo of memory and a system that learns. Highest priority — it is load-bearing for the
self-learning judgment-layer story and is the smallest, highest-signal gap.

### P2 — Autonomous PR-review loop: HumanLayer PR → Hermes resume → Greptile review → triage (newly discovered)

**Scope.** Close the full autonomy loop. When HumanLayer opens a PR, fire a GitHub `pull_request`
(opened/synchronize) **webhook** into Hermes' existing `hermes webhook` receiver so the orchestrator
**resumes** and **kicks off a Greptile review** of the PR, then **ingests Greptile's findings and****
****triages them** — grounding each via `query_cto_knowledge` and filing `[Brownfield]` follow-ups /
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

**Scope.** This DOES use NemoClaw/OpenShell — it is the SAME stack <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> P1 shipped, switched to
OpenShell's **MicroVM compute driver** (libkrun + Apple Hypervisor.framework, OpenShell Option B)
instead of the **container** driver. P1 (container driver) confines the **containerized sub-tools**
(the sandbox demonstrably refuses a non-allow-listed CONNECT). P4 confines the **host Hermes****
****orchestrator's OWN egress** — the orchestrator runs on the macOS host, *outside* any sandbox today —
by running it inside an OpenShell-managed MicroVM. i.e. "use NemoClaw to sandbox the brain too,"
not a different tool and not a re-do of P1. Already recorded in `docs/system-design-tradeoffs.md`.
Inference stays cloud (no CUDA on Apple Silicon); watch the Landlock `best_effort` and
`inference.local` mDNS macOS bugs.
**Rationale.** Strongest confinement, biggest moving-parts/DNS risk — sequenced after the
load-bearing containerized layer that ships today (An Elegant Puzzle: sequence the hardening).

### P5 — PMF → product loop: real shipped-bet feedback (close the North Star loop)

**Scope.** EXTENDS the <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> P4 PMF loop that already SHIPPED (it ranks opportunities RICE/ICE
and records a `shipped` field in `recordings/pmf_ledger.json`) — but nothing flips
`shipped:false → true` from real outcomes yet. Wire the actual feedback signal (a shipped bet's
measured result) back into the ranking so the North Star — **opportunities shipped**, not tickets
filed — is computed from reality, grounded in real usage + Stripe data.
**Rationale.** Closes the learning loop the <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> P4 slice scaffolded; depends on accumulated
usage data, so it follows the memory-capture (P1) work.

### P6 — Moderne / OpenRewrite paid-tier evaluation (LOWEST priority — paid, no account yet)

**Scope.** Evaluate **Moderne / OpenRewrite** (no free tier — paid; no account provisioned yet, so
deliberately last) as the deterministic, recipe-based mass-refactor back-end ALONGSIDE Codegen:
Codegen for NOVEL, judgment-heavy fixes; Moderne for RECIPE-AMENABLE mechanical debt
(dependency/framework upgrades, broad languages incl. Java, which Codegen does not cover). <issue id="fa4a8772-3428-459f-90c3-d5cd77cbbe11" href="https://linear.app/global-south-ai-safety/issue/GLO-16/brownfield-checkoutservice-billing-path-grpc-coupling-hub-degree-6">GLO-16</issue>
already routes its billing-path refactor to Codegen and explicitly defers the Moderne evaluation
here. Register the Moderne local MCP (`mod config agent-tools install`) under
`hermes/config.yaml mcp_servers` and pilot one recipe.
**Rationale.** The Hermes JUDGMENT layer should route each ticket to the right remediation
back-end; without Moderne, recipe-amenable + Java debt has no autonomous path. Paid-tier with no
account yet, so it is a future evaluation/decision item — moved to the end of the backlog.

---

## Part C — rolled-forward original deferred items (with rationale)

* **Full mem0 OSS server + Next.js dashboard** (from <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> Phase 1 / Part C). *Why still**
**deferred:* the SDK-on-host path verifies every phase; the dashboard is a visualization nicety.
  Now more relevant once P1 above makes the `memories` collection actually fill up — a dashboard
  over a growing memory is worth more than over an empty one.
* **OpenHands via Portal/LiteLLM** (from <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> Part C). *Why:* the greenfield path stays "Hermes
  research → HumanLayer Linear ticket → Claude Code executes"; point OpenHands at the Portal
  OpenAI-compatible endpoint via LiteLLM to avoid a separate Anthropic key when picked up.
* **Second-account "fresh setup" walkthrough** (from <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue> Part C). *Why:* single-account /
  multiple-profiles is what makes the shared Kanban work; two-account is future-only.

*(*<issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue>*'s demo-authenticity item was promoted to P0 and is now shipped; its real-Linear-UI ending**
**is rolled forward as P3 above.)*

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

---

## Review

After you open a PR for this ticket, run Greptile on it (/greptile) and address the findings before requesting merge.
