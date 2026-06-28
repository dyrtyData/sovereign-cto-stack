---
type: research-questions
---

# Research Questions

These questions document how the **Sovereign CTO Stack** (`sovereignCTO/`, a standalone git
repo nested in `GS_AISafetyHackathon/` and gitignored by the parent) works today. The codebase
already implements Phases 0–5; the GLO-13 epic also defines a prioritized deferred backlog
(P0–P4). The research should capture the current state of the built phases (to support a clean
rebuild) and the existing infrastructure each backlog item builds on.

1. **Hermes orchestrator boot + memory + gateway (Phase 1).** In `sovereignCTO/hermes/`
   (`config.yaml`, `SOUL.md`, `AGENTS.md`, `mem0.json`, `.env.example`) and
   `scripts/` (`preflight.sh`, `mem0_roundtrip.py`, `init-pgvector.sql`), how does Hermes boot
   end-to-end? Specifically: how is Nous Portal inference configured, how is self-hosted mem0
   wired as the native memory provider (SDK-on-host against the `mem0-postgres` pgvector service
   on host port 5433) with the `MEM0_API_KEY` Platform fallback, how are facts scoped by
   `user_id`/`agent_id`, and how is the Telegram gateway configured and gated (`TELEGRAM_BOT_TOKEN`,
   `TELEGRAM_ALLOWED_USERS`)?

2. **CTO RAG brain and `query_cto_knowledge` (Phase 2).** In `sovereignCTO/rag/` (`server.py`,
   `Dockerfile`, `requirements.txt`) and `scripts/` (`convert_corpus.sh`, `rag_smoke.py`), how is
   the local Vector MCP sidecar implemented — MiniLM embeddings, embedded LanceDB index, FastMCP
   HTTP transport — and how does it expose `query_cto_knowledge`? How is the corpus converted
   (docling PDF + pandoc EPUB) into `corpus/*.md`, how is it ingested/chunked, how is the tool
   bound to Hermes (`hermes/config.yaml` MCP binding), and how is the "consult before every CTO
   function and cite the source files" standing instruction expressed in `SOUL.md` /
   `hermes/profiles/*/SOUL.md` and synced into `~/.hermes`?

3. **Tech-debt auditor hero loop (Phase 3).** Trace the flow from graphify static map to a filed
   `[Brownfield]` Linear ticket: `scripts/run_graphify.sh` → `graphify-out/` →
   `scripts/service_topology.py` (the frontend=7 / checkout=6 coupling derivation) →
   `hermes/profiles/cto-architecture/SOUL.md` + `hermes/skills/file_brownfield_ticket.md` →
   `scripts/linear_mcp.py`. How are tickets actually filed and how are they validated
   (`assert_graph_topology.py`, `assert_brownfield_ticket.py`)? How is the loop scheduled on cron,
   and how does the `workspaces/microservices-demo` (Online Boutique) clone fit in as a
   static-analysis-only target?

4. **PMF research profile + Kanban coordination (Phase 4 & relevant to P4).** In
   `hermes/profiles/cto-market/SOUL.md`, `hermes/skills/pmf_brief.md`, and
   `scripts/pmf_kanban_run.sh` / `assert_pmf_run.py` / `assert_product_ticket.py`, how does the
   `CTO-Market` profile run the `pmf_brief` skill (web scrape + multi-angle grounding → cited brief
   → one `[Product]` ticket)? How is the shared single-host Kanban board implemented
   (`~/.hermes/kanban.db`, the ready→running→done handoff, `kanban_complete()` summary/metadata),
   and how are the AARRR sections of the brief currently grounded (i.e., where would real Stripe
   MRR/churn/cohort data plug in for P2/P4)?

5. **Autonomous-run recording pipeline and the progress ticker (Phase 4 + P0).** In `recorder/`
   (`Dockerfile`, `entrypoint.sh`), `scripts/record_run.sh`, and `scripts/verify_recording.py`,
   how does the Xvfb + ffmpeg x11grab capture work, and what exactly does the left split-screen
   pane show today? Detail the `start_ticker`/`stop_ticker` scripted progress ticker, how the
   agent's reasoning/tool-call output is written to `$AGENT_LOG` and tailed live, what the
   recorder healthcheck/non-blank/non-static guards verify, and — critically for P0 — what
   genuine Hermes session log / event-stream artifacts exist that expose real `query_cto_knowledge`
   and `save_issue`/`file ticket` tool-call events (format, location, how they could be tailed
   instead of the ticker).

6. **Egress / network posture and the Docker allow-list (P1).** What network and sandboxing
   controls exist today across `docker-compose.yml`, `recorder/`, `rag/`, and the Hermes
   configuration — port bindings, any allow-list, what outbound endpoints the stack actually
   contacts (Nous inference, Linear, Telegram, web-scrape targets)? How does Hermes run on the
   Apple Silicon host relative to the Docker Desktop LinuxKit VM, and where in the current config
   would a deny-by-default egress layer (NemoClaw/OpenShell: Landlock + seccomp + OPA CONNECT
   proxy, `policy.yaml`) attach? Use web/library research to characterize NVIDIA OpenShell/NemoClaw
   capabilities and the two noted macOS constraints (Landlock `best_effort` fallback; the broken
   local-Ollama `inference.local` DNS).

7. **Skill/MCP integration contract and the graphify→remediation surface (P2 & P3).** How does a
   Hermes skill (`hermes/skills/*.md`) declare and invoke MCP tools, and how are MCP servers
   registered/bound (`hermes/config.yaml`, `scripts/linear_mcp.py`) — i.e., the pattern a new
   Stripe MCP or a SonarQube REST client would follow? What is the structure of graphify output
   (`graphify-out/`, `run_graphify.sh`, `render_service_graph.py`) that SonarQube signals would be
   layered onto, and how are filed tickets snapshotted to `tickets/` (`snapshot_tickets.py`,
   `snapshot_after_run.sh`, AGENTS.md rule 7)? Use web/library research to characterize the
   SonarQube REST endpoints (`/api/issues/search`, `/api/measures/component`), Codegen MCP
   (`mcp.codegen.com`), and Moderne/OpenRewrite where the ticket relies on external capabilities.

8. **Visual / HTML surfaces rendered into the demo (design system check, P0).** The recorded run
   and P0 paint browser/HTML surfaces (the `service-graph.html` coupling graph, the Linear ticket
   in a browser, scrolling RAG chunks). In `scripts/render_service_graph.py` and the recorder
   browser surface, how is `service-graph.html` generated and styled — what HTML/CSS/JS approach,
   templating, color/typography/layout conventions, and any libraries (graph viz, etc.) are used?
   What patterns exist for producing a legible, self-contained HTML surface that could also render
   live tool-call events or RAG chunks for the P0 demo?

9. **Reproducibility, verification gates, and the self-perpetuating ticket workflow (Phases 0 & 5,
   Part D).** How is the repo made public-safe and clean-cloneable: `.gitignore` scope,
   `.env.example`, the tracked `.githooks/pre-commit` gitleaks hook, `scripts/preflight.sh`,
   `scripts/fresh_clone_smoke.sh`, `scripts/check_doc_links.py`, and `docker compose config -q`?
   How does the full-build ticket workflow operate end-to-end —
   `scripts/file_fullbuild_ticket.py`, `assert_fullbuild_ticket.py`, `snapshot_after_run.sh`, and
   the `docs/` set (`setup-guide.md`, `system-design-tradeoffs.md`, `cto-functions.md`) — such that
   filing a ticket persists `tickets/<ID>.md` and the "author the next epic (GLO-14)" closeout
   (Part D) can be reproduced?
