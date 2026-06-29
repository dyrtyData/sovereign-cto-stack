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
6. **Living docs updated every phase/commit.** As part of each phase/commit, update the
   living docs so a fresh clone stays reproducible and the story stays current:
   `README.md` (the front-door overview — components, build phases, repo layout),
   `docs/setup-guide.md` (the repeatable clean-clone setup), **and**
   `docs/system-design-tradeoffs.md` (the cited decision record). Also update
   `docs/cto-functions.md` whenever the CTO-function ↔ corpus mapping changes. If a commit
   changes `scripts/`, `docker-compose.yml`, `hermes/`, or `egress/`, the matching doc(s) —
   including `README.md` — change in the SAME commit, not a deferred closeout.
7. **Snapshot filed Linear tickets into `tickets/`.** Every `[Brownfield]`/`[Product]`/
   `[Full-Build]` ticket filed is persisted to `tickets/<ID>.md` (via
   `scripts/snapshot_tickets.py` / `scripts/snapshot_after_run.sh`) so the repo's
   decision record is self-contained — git history, not an external tracker, is the
   source of truth.
8. **gitleaks-clean, public-repo-safe, before every commit.** Run `gitleaks` (enforced by
   the tracked `.githooks/pre-commit` hook — enable once per clone with
   `git config core.hooksPath .githooks`). Never stage secrets, symlink targets, or
   large binaries; the repo is public.
9. **AGPLv3 attribution header on every source file.** This repo is licensed under the GNU
   AGPL v3.0 (see `LICENSE`); the copyright holder is **dyrtyData**. AGPL §4–§5 only protect
   copyright notices that are actually present in a file, so **every `.py`/`.sh` you create
   under `scripts/`, `hermes/`, `egress/`, or `recorder/` MUST carry the 3-line SPDX header**
   (after the shebang, before the PEP 723 block / docstring):
   ```
   # SPDX-License-Identifier: AGPL-3.0-or-later
   # Copyright (C) 2026 dyrtyData
   # Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.
   ```
   Don't hand-add it — run `python3 scripts/apply_license_headers.py` (idempotent; it inserts
   the header into any missing file). The tracked `.githooks/pre-commit` hook **blocks the
   commit** if a staged in-scope file lacks the header (`apply_license_headers.py --check
   --staged`). This rule is load-bearing for the "any duplication credits the author" goal —
   carry it into every subagent/implementer prompt.

## Memory

mem0 runs as the SDK on the host against the `mem0-postgres` pgvector service (OSS mode);
Platform mode is the fallback via `MEM0_API_KEY`. Facts are scoped by `user_id`/`agent_id`
(see `hermes/mem0.json`).
