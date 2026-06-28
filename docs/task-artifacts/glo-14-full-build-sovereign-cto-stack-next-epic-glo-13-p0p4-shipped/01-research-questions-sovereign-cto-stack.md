---
type: research-questions
---

# Research Questions

> **Where the code lives.** The GLO-14 epic builds on the GLO-13 P0–P4 work, which is **not on `main`**. It lives on the `glo-13-full-build-sovereign-cto-stack-complete-vision-all-phases` branch, checked out as a git worktree at
> `/Users/laptop/.humanlayer/workspaces/glo-13-full-build-sovereign-cto-stack-complete-vision-all-phases/sovereignCTO`.
> The `main` checkout at `sovereignCTO/` is an earlier snapshot and is missing the P0–P4 assert scripts (`assert_demo_authenticity.py`, `assert_egress_policy.py`, `assert_stripe_grounding.py`, `assert_sonar_fusion.py`, `assert_pmf_ranked.py`, `assert_showcase_video.py`) and `egress/`. Research the **worktree**, and note where the two diverge.

1. In the worktree's `scripts/mem0_pmf_decisions.py`, `scripts/mem0_roundtrip.py`, `hermes/mem0.json`, and `scripts/assert_pmf_ranked.py`, trace the full mem0 data flow end to end: how the self-hosted OSS mem0 SDK is configured against the docker-compose `mem0-postgres`/pgvector backend, which collections exist (`memories` vs `pmf_decisions`), exactly where the code `search()`es/reads prior decisions, and where (if anywhere) it `add()`s/writes — i.e. confirm whether the read path and the write path are the same collection and which collection each agent loop actually touches.

2. Across the agent loops (tech-debt/architecture audit, the PMF brief, and any other CTO function entry points in `scripts/` and `hermes/skills/`), where does each loop persist its decision/output today (e.g. `tickets/*.md` snapshots, `recordings/*`, git commits, `docs/system-design-tradeoffs.md`), and at what point in each loop would a "record this decision" step sit relative to the existing `query_cto_knowledge` consult and ticket-filing steps?

3. How does the Hermes orchestrator's webhook receiver work — what does `hermes webhook` expose, how is a run "resumed," and how are external MCP back-ends (e.g. the Codegen/Linear MCP servers in `hermes/config.yaml mcp_servers`) registered, authorized, and invoked from within a loop? Document the existing receiver entry points, config keys, and the OAuth/token storage layout under `~/.hermes/`.

4. What do the Greptile code-review product and its GitHub App / API offer for programmatically triggering a PR review and ingesting its findings, and what are the GitHub `pull_request` (opened/synchronize) webhook payload fields a receiver would parse? (Use web/library research — capture the Greptile GitHub-App auto-review path vs. an API/webhook-driven path, and any auth/endpoint requirements.)

5. How does the demo recording pipeline produce its current "ticket in browser" ending — trace `scripts/record_run.sh`, `recorder/Dockerfile`, `recorder/entrypoint.sh`, `scripts/render_ticket_card.py`, and `scripts/verify_recording.py`: how the throwaway-container Chromium renders the local `tickets/GLO-NN.md` snapshot to a `file://` HTML page, how Xvfb+ffmpeg capture is wired, and where a Chromium user-data-dir / persistent profile or session would attach.

6. How is the NemoClaw/OpenShell egress sandbox built and enforced today — read `egress/policy.yaml`, `egress/Dockerfile`, and `scripts/assert_egress_policy.py`: which OpenShell compute driver (container) is used, how the OPA CONNECT proxy + Landlock layers are invoked (`openshell sandbox create …`), what the allow-list endpoints are, and — critically — how/where the **host Hermes orchestrator process itself** is launched today (inside or outside any sandbox).

7. What does OpenShell document about its **MicroVM compute driver** (libkrun + Apple Hypervisor.framework, "Option B") versus the container driver — configuration, how a long-lived host process is run inside a MicroVM, and the known macOS limitations already noted in `docs/system-design-tradeoffs.md` (Landlock `best_effort`, the `inference.local` mDNS bug, no CUDA on Apple Silicon)? (Web/library research + cross-reference the tradeoffs doc.)

8. How does the PMF ranking + ledger work today — trace `recordings/pmf_ledger.json`, `scripts/assert_pmf_ranked.py`, and the PMF brief skill: what fields the ledger holds (including `shipped`), how RICE/ICE ranking is computed, what real signals feed it (e.g. the Stripe MRR/churn grounding and `query_cto_knowledge`), and where a `shipped:false→true` outcome flip would read from.

9. How does the remediation-routing decision get encoded today — in `hermes/config.yaml`, the `[Brownfield]` ticket skill (`hermes/skills/file_brownfield_ticket.md`), the SonarQube/graphify fusion (`scripts/assert_sonar_fusion.py`, `graphify-out/service-coupling.json`), and the GLO-16 ticket — specifically how Codegen is named as the back-end and how an MCP server (e.g. Moderne/OpenRewrite's local `mod config agent-tools install`) is registered under `mcp_servers` and surfaced to the agent?

10. What is the current state of the rolled-forward Part C items in the repo — is there any existing mem0 OSS server / dashboard scaffolding, any Next.js or other frontend/UI code anywhere in the repo, and any OpenHands or Portal/LiteLLM (`provider: nous`, the local OpenAI-compatible proxy at `127.0.0.1:8645/v1`) integration points? If any frontend/dashboard surface exists or is scaffolded, what component library, styling approach, design tokens (colors/typography/spacing), and theming convention does it use?
