# AGENTS.md — Sovereign CTO Stack conventions

Project conventions and architecture that any Hermes agent reads per working directory.
This is the **project** layer (distinct from `hermes/SOUL.md`, which is durable identity).

## What this project is

A public-safe, version-controlled multi-agent "engineering factory" on an Apple Silicon
host. A **Hermes orchestrator** (Nous Portal inference) coordinates specialist profiles over
a single-host Kanban board, with persistent **mem0** memory, a textbook-grounded **CTO RAG
brain**, a **graphify**-driven tech-debt auditor filing `[Brownfield]` Linear tickets, and a
PMF research profile — with autonomous runs captured to `.mp4`.

## Profiles (one Nous account, multiple profiles, shared Kanban)

- **orchestrator** (default `~/.hermes/`) — coordinates; holds the shared picture.
- **cto-architecture** — tech-debt auditor (Phase 3); reads the graphify graph, files tickets.
- **cto-market** — PMF researcher (Phase 4); web research + RAG cross-reference.

All profiles share `~/.hermes/kanban.db`. Coordinate via Kanban comments and structured
handoffs (`kanban_complete()` returns `summary` + `metadata`).

## Standing rules

1. **Consult `query_cto_knowledge` before every CTO function** (tech-debt audit, PMF, org/
   strategy) and **cite the grounding text(s)** in the output. (Enforced from Phase 2 onward.)
2. **Git history is the authoritative decision record.** mem0 is a complement, not a
   dependency. Record decisions in commits and in `docs/system-design-tradeoffs.md`.
3. **Never commit secrets.** Credentials live only in `.env` (repo, gitignored) and
   `~/.hermes/.env`. Config files committed to the repo carry zero secret values.
4. **Static analysis only for the audit target.** Online Boutique is analyzed as a source
   graph — never deployed.
5. **Small, verifiable steps.** Each phase boots and is verified before the next begins.
6. **Living docs updated every phase/commit.** Update `docs/setup-guide.md` (the
   repeatable clean-clone setup) **and** `docs/system-design-tradeoffs.md` (the cited
   decision record) as part of each phase/commit — both must stay reproducible from a
   fresh clone.
7. **Snapshot filed Linear tickets into `tickets/`.** Every `[Brownfield]`/`[Product]`/
   `[Full-Build]` ticket filed is persisted to `tickets/<ID>.md` (via
   `scripts/snapshot_tickets.py` / `scripts/snapshot_after_run.sh`) so the repo's
   decision record is self-contained — git history, not an external tracker, is the
   source of truth.
8. **gitleaks-clean, public-repo-safe, before every commit.** Run `gitleaks` (enforced by
   the tracked `.githooks/pre-commit` hook — enable once per clone with
   `git config core.hooksPath .githooks`). Never stage secrets, symlink targets, or
   large binaries; the repo is public.

## Memory

mem0 runs as the SDK on the host against the `mem0-postgres` pgvector service (OSS mode);
Platform mode is the fallback via `MEM0_API_KEY`. Facts are scoped by `user_id`/`agent_id`
(see `hermes/mem0.json`).
