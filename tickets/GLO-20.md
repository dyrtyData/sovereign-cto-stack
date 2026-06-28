# GLO-20 — [Full-Build] Sovereign CTO Stack — next epic (GLO-14 learn/review/feedback shipped) + rolled-forward backlog

- **identifier:** GLO-20
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-20/full-build-sovereign-cto-stack-next-epic-glo-14-learnreviewfeedback
- **team:** Global South Ai Safety
- **status:** Backlog
- **labels:** Full-Build
- **priority:** High (2)
- **snapshot captured:** 2026-06-28T22:20:31+00:00

## Description

## What this is

The **next full-build epic** for the Sovereign CTO Stack — authored on the <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> closeout
(Part D recurrence: "the final step is to author the next full-build epic", mirroring how <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue>'s
Phase 5 authored <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue>). <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> made the system actually **learn and review**: it closed mem0's
write path so `memories` accumulates run-over-run (P1), had every filed ticket prompt a Greptile PR
review (P2), flipped the PMF North Star from a real Stripe-grounded outcome (P5), told a fuller
authenticated demo (P3 / D-2), and spiked host-orchestrator MicroVM confinement (P4) — each behind
an exit-0 `assert_*.py` gate. This epic rolls forward <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue>'s Part C deferrals and folds in the
concrete items discovered while building P1–P5, so git history stays the self-perpetuating,
always-current roadmap.

Public repo: [https://github.com/dyrtyData/sovereign-cto-stack](<https://github.com/dyrtyData/sovereign-cto-stack>) · decision record:
`docs/system-design-tradeoffs.md` · CTO-function map: `docs/cto-functions.md` · setup:
`docs/setup-guide.md`. Git history is the authoritative decision record; mem0 is a complement.

---

## Part A — what <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> delivered (the learn / review / feedback loops, all gated)

<issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> shipped seven thin, gated, verifiable slices on top of <issue id="41ce0a1f-c6c8-475d-a0b5-aebe8b17db81" href="https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized">GLO-13</issue>'s phased build:

* **P1 — mem0 OSS ≥ v2.0.0 upgrade** (`scripts/mem0_roundtrip.py`): pinned `mem0ai>=2.0.0`
  (resolved 2.0.10); native entity-linking replaces external graph DBs (no Neo4j); the round-trip
  smoke asserts the v2 return shape and self-skips the `infer=True` entity-link proof when Ollama
  is absent.
* **P2 — Close the mem0 write path** (`scripts/assert_memory_accumulates.py`): a deterministic
  `mem0_record_decision.py` writes each filed decision into the unified `memories` collection with
  `infer=True`, between ticket-filing and snapshot in **both** loops; the PMF consult reads the same
  collection. Two runs both grow the count, run 2 recalls run 1, and the recalled text is absent
  from every `tickets/*.md` (accumulated, not re-seeded).
* **P3 — Greptile ticket-instruction line** (`scripts/assert_greptile_instruction.py`): every filed
  ticket carries a standing "run Greptile on the PR" line; the gate reads it back from the live
  ticket + the snapshot. The Greptile CLI / skill / `/greptile` command live **globally in**
  `~/.claude`**, out of repo** (a project-agnostic prerequisite, not a repo deliverable).
* **P5 — PMF shipped-bet flip** (`scripts/assert_shipped_flip.py`): a Stripe-grounded shipped-result
  record flips the matching `pmf_ledger.json` row `false → true`; the recorded metric must equal a
  real `stripe_metrics.json` value (no fabrication), unrelated rows untouched, atomic write.
* **P3 / D-2 — Fuller demo + memory view + authenticated Linear ending**
  (`scripts/assert_showcase_video.py`, `render_memory_card.py`, `assert_memory_view_grows.py`): the
  montage surfaces more components and can end on the **real** authenticated Linear ticket UI
  (persistent Chromium profile), with the `file://` snapshot as the reproducible default; a
  read-only memory view proves `memories` grows.
* **P4 — Host-orchestrator MicroVM confinement spike** (`scripts/assert_microvm_spike.py`): the
  OpenShell `vm` driver (libkrun + Apple Hypervisor.framework) was spiked to the driver-binds layer
  and a dated **NO-GO** go/no-go recorded with the four macOS limitations (Q9 Option A: scoped, not
  built).
* **Closeout** — Part C deferral capture + this next epic (`scripts/assert_closeout_ready.py` gates
  the D-6 boundary: every prior gate exit-0 + the <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> acceptance checklist fully ticked).

---

## Part B — rolled-forward + newly-discovered backlog (build in this order)

### P1 — mem0 OSS server + read-only Next.js memory dashboard (rolled forward — now worth building)

**Scope.** <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> built a *lightweight static* read-only memory view (`render_memory_card.py`) that
proves the `memories` collection grows. Roll forward the **full mem0 OSS server + a small Next.js****
****read-only dashboard** over the now-accumulating collection — entity links, per-run decision rows,
search — as the standing visualization surface (no frontend exists in the repo yet).
**Rationale.** Deferred in <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> (Q12) because the static card verifies the phase and no frontend
scaffolding exists; now that P1/P2 made `memories` actually fill up, a dashboard over a growing
memory is worth materially more than over an empty one. Read-only — mem0 stays a recall complement,
git stays authoritative.

### P2 — Moderne / OpenRewrite remediation back-end (rolled forward — needs an account OR the OSS pilot)

**Scope.** Evaluate **Moderne / OpenRewrite** as the deterministic, recipe-based mass-refactor
back-end ALONGSIDE Codegen: Codegen for NOVEL, judgment-heavy fixes; Moderne for RECIPE-AMENABLE
mechanical debt (dependency/framework upgrades, broad languages incl. Java, which Codegen does not
cover). Two paths: (a) provision a Moderne account and register the local MCP
(`mod config agent-tools install`) under `hermes/config.yaml mcp_servers` — the **commented stub is****
****already staged** in that file (deferred, not registered); or (b) pilot **OpenRewrite OSS** directly
(no account) on one recipe-amenable change and record the route-to-Moderne decision with cost/benefit
vs Codegen in `docs/system-design-tradeoffs.md`.
**Rationale.** <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> moved this from an active backlog item to a Part C deferral (Q11) because no
Moderne account is provisioned; remediation continues to route to Codegen ("named-only"). The
OpenRewrite-OSS-pilot option is preserved so a recipe can be piloted without a paid account when the
decision is made — the Hermes JUDGMENT layer should route each ticket to the right back-end.

### P3 — Autonomous PR-review TRIAGE loop (rolled forward, deeper than <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> P2)

**Scope.** <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> P2 deliberately decoupled Greptile to a *global, out-of-repo* skill that
HumanLayer-on-Claude-Code runs on the PR (the only in-repo deliverable being the ticket-instruction
line). The deeper, in-repo version — captured but **not** built in <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> — is to **ingest Greptile's****
****findings back into Hermes** and triage them: ground each via `query_cto_knowledge` and file
`[Brownfield]` follow-ups / Kanban cards rather than leaving raw inline comments. Keep egress
deny-by-default (any Greptile/GitHub endpoint joins `egress/policy.yaml`).
**Rationale.** Turns "agents that ship + review" into "agents that ship, review, *and re-prioritize**
**from the review*" — the triage/grounding step is the sovereign-CTO white space. Deferred in <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue>
in favour of the clean global-skill decoupling; rolled forward as the next autonomy increment.

### P4 — mem0 passive capture via its OpenAI-compatible proxy (rolled forward — considered + rejected for now)

**Scope.** <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue>'s Q3 probe confirmed the closed-source `hermes-agent` binary does **not** write
`memories` natively, so the deterministic `mem0_record_decision.py` writer is load-bearing. The only
"passive, as-intended" route is to chain inference through mem0's OpenAI-compatible proxy
(`mem0.proxy.main.Mem0 → hermes proxy :8645 → Nous`), with mem0 silently `add()`-ing every turn.
Evaluate adopting it deliberately if the tradeoff ever becomes worth it.
**Rationale.** Rejected for <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> because it places mem0 **in the critical inference hot path** (a
mem0 outage breaks every agent call) and captures noisy raw turns instead of curated, tagged,
gate-able decisions — violating the standing rule that mem0 is a recall complement, never
load-bearing (git stays authoritative). The exact enablement path is recorded in
`docs/system-design-tradeoffs.md` so a future epic can adopt it on purpose.

### P5 — Host-orchestrator MicroVM confinement: BUILD the deferred remainder (rolled forward from <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> P4)

**Scope.** <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> P4 spiked the OpenShell `vm` driver to the **driver-binds** layer and recorded a
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

## Part C — rolled-forward original deferred items + <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> discoveries (with rationale)

* **Greptile global setup (out-of-repo prerequisite).** *Why out of repo:* the Greptile CLI + Claude
  Code skill + `/greptile` command are set up **globally in** `~/.claude` (project-agnostic; a
  separate task — `greptile login` once, install/adapt `github.com/greptileai/skills`). This repo's
  sole Greptile surface is the ticket-instruction line; the global setup is a prerequisite, not a
  <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue>/next-epic repo deliverable. Recorded so a fresh clone knows the dependency.
* **Live-profile skill-deploy step (discovered building** <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> **P3).** *Why:* the Greptile
  instruction line lives in the tracked `hermes/skills/*.md`, but Hermes reads from the live
  `~/.hermes` profile dirs — so a deploy step that syncs the tracked skills into each live profile is
  required for the instruction to actually fire. Capture it as a documented setup step / small script.
* **Duplicate-finding dedupe (discovered building** <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue>**).** *Why:* re-filing `[Brownfield]` tickets
  produced duplicate issues (<issue id="9b8ed28f-a84c-406d-a141-fe8bd84e1d46" href="https://linear.app/global-south-ai-safety/issue/GLO-8/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-backend">GLO-8</issue>/9/10/11 → re-centered <issue id="ef6ce1dd-6c47-4875-ac1e-234e7129154f" href="https://linear.app/global-south-ai-safety/issue/GLO-15/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-backend">GLO-15</issue>/16); a dedupe step that detects and
  consolidates near-duplicate filed tickets keeps the tracker and `tickets/` snapshots clean.
* **Full mem0 OSS server + Next.js dashboard** (promoted to P1 above). *Why now:* see P1 rationale —
  worth building once the collection accumulates.
* **mem0 passive capture via the proxy** (promoted to P4 above). *Why still deferred:* see P4 —
  keeps mem0 off the critical inference hot path.
* **OpenHands via Portal/LiteLLM** + the **second-account walkthrough** (promoted to P6 above).
  *Why:* future-only, see P6 rationale.
* **Moderne/OpenRewrite** (promoted to P2 above; OSS-pilot option preserved). *Why:* see P2 — no
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
- [ ] Host-orchestrator MicroVM confinement is BUILT (the <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/full-build-sovereign-cto-stack-next-epic-glo-13-p0-p4-shipped-rolled">GLO-14</issue> spike's deferred remainder) or the
      go/no-go is re-confirmed with updated evidence.
- [ ] Each rolled-forward item states scope + rationale (done above), incl. the Greptile global
      prerequisite, the live-profile skill-deploy step, and the duplicate-finding dedupe need.
- [ ] On closeout, the NEXT full-build epic is authored (Part D) and snapshotted into `tickets/`.

---

## Review

After you open a PR for this ticket, run Greptile on it (/greptile) and address the findings before requesting merge.
