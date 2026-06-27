# sovereign-cto-stack

A public-safe, version-controlled multi-agent "engineering factory" for an Apple Silicon
host: a **Hermes** orchestrator (Nous Portal inference) with specialist profiles coordinating
over a single-host Kanban board, persistent **mem0** memory, a textbook-grounded **CTO RAG
brain** (`query_cto_knowledge`), a **graphify**-driven tech-debt auditor that files
HumanLayer-ready `[Brownfield]` Linear tickets, a PMF research profile, and external `.mp4`
capture of autonomous runs.

Anyone can `git clone` this repo and bring the stack up with `docker compose up` — there are
**zero secrets committed**. You supply your own credentials in a local `.env` (see below).

## Architecture (target)

- **Hermes orchestrator** — boots, authenticates to Nous Portal, persists facts in mem0,
  answers on Telegram, schedules CTO jobs via cron.
- **Specialist profiles** — `CTO-Architecture` (tech-debt auditor) and `CTO-Market` (PMF
  researcher), coordinating with the orchestrator over a shared single-host Kanban board.
- **CTO RAG brain** — local Vector MCP over the converted Growth / System Design / Org Design
  textbook corpus; consulted before every CTO function, citing its grounding text(s).
- **Tech-debt loop (hero)** — graphify maps Online Boutique -> the auditor reads the graph,
  consults the RAG brain, and files a `[Brownfield]` Linear ticket precise enough for HumanLayer.
- **Recording** — an external Xvfb + ffmpeg sidecar captures an autonomous run to `.mp4`.

## Build phases

The build is **strictly sequential and gated** — each phase is a thin vertical slice that boots
and is verifiable before the next begins.

- **Phase 0** — Public-safe repo skeleton, prerequisites gate & docs scaffolding (this commit).
- **Phase 1** — Hermes orchestrator boots end-to-end (Portal + mem0 + Telegram).
- **Phase 2** — CTO knowledge RAG brain (corpus -> Vector MCP -> `query_cto_knowledge`).
- **Phase 3** — Tech-debt auditor loop (graphify -> grounded `[Brownfield]` Linear ticket).
- **Phase 4** — PMF research profile + autonomous-run `.mp4` recording.
- **Phase 5** — Documentation finalization + comprehensive "full-build" Linear ticket.

## Quick start

```bash
git clone https://github.com/dyrtyData/sovereign-cto-stack.git
cd sovereign-cto-stack
cp .env.example .env          # then fill in your real values (see Manual Prerequisites)
bash scripts/preflight.sh     # halts until required keys are present
docker compose config -q      # validate the stack
```

## Manual Prerequisites

The build **halts** on this checklist (`scripts/preflight.sh` enforces the programmatic part).
Complete every item before running later phases.

- [ ] **Nous Portal key** — put `NOUS_PORTAL_API_KEY` in `.env`
      (from <https://portal.nousresearch.com/>).
- [ ] **Hermes Portal login** — run `hermes setup --portal`.
      :warning: **Needs your click** — opens a browser device-code OAuth flow. (Phase 1.)
- [ ] **Telegram bot token** — message **@BotFather**, send `/newbot`, choose a display name and
      a username ending in `bot`; put the token in `TELEGRAM_BOT_TOKEN` in `.env`.
- [ ] **Telegram numeric ID** — message **@userinfobot**; put your numeric id in
      `TELEGRAM_ALLOWED_USERS` in `.env` (comma-separate for more users).
- [ ] **Linear MCP OAuth** — run `hermes mcp install linear`.
      :warning: **Needs your click** — browser OAuth, separate from HumanLayer's Linear connection.
      (Phase 3.)
- [ ] **GitHub repo** — **done** (this repo is published at
      <https://github.com/dyrtyData/sovereign-cto-stack>).
- [ ] **Laptop plugged in + lid open** — required for long-running and recorded runs (only you
      can satisfy this). (Phase 4.)
- [ ] *(Optional, future)* **mem0 Platform key** — `MEM0_API_KEY` in `.env` enables the cloud
      fallback for self-hosted pgvector memory.

## Repository layout

```
.
├── .env.example              # credential template (copy to .env)
├── docker-compose.yml        # mem0-postgres / rag-sidecar / recorder (phased)
├── README.md                 # this file
├── scripts/
│   └── preflight.sh          # halts if required .env keys are missing
├── docs/
│   ├── setup-guide.md         # repeatable setup (filled incrementally per phase)
│   └── system-design-tradeoffs.md  # textbook-cited decision record
└── corpus/                   # converted textbooks (gitignored — stays local)
```

> **Documentation policy:** git history is the authoritative decision record; mem0 is a
> complement, not a dependency. `docs/system-design-tradeoffs.md` cites the named textbooks
> behind every locked decision.
