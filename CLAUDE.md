# CLAUDE.md — read AGENTS.md first

This repo's agent conventions and **Standing rules** live in [`AGENTS.md`](./AGENTS.md).
Claude Code auto-loads this file; Codex auto-loads `AGENTS.md`. They are the **same
contract** — `AGENTS.md` is the single source of truth. Read it before doing any work,
and **carry its Standing rules into every subagent/implementer prompt** (they do not
auto-load this file's intent — you must pass it).

## Non-negotiable per-phase / per-commit checklist (from AGENTS.md Standing rules)

Before EVERY commit in this repo — including each phase of a multi-phase build:

- [ ] **Rule 6 — Living docs every phase/commit.** Update the living docs for the slice you
      just built: **`README.md`** (front-door overview), **`docs/setup-guide.md`** (repeatable
      clean-clone setup), **`docs/system-design-tradeoffs.md`** (cited decision record), and
      `docs/cto-functions.md` when the CTO-function↔corpus map changes. If you touched
      `scripts/`, `docker-compose.yml`, `hermes/`, or `egress/`, the matching docs (incl.
      `README.md`) change in the SAME commit — NOT deferred to a closeout phase.
- [ ] **Rule 7 — Snapshot filed tickets.** Persist every `[Brownfield]`/`[Product]`/
      `[Full-Build]` Linear ticket to `tickets/<ID>.md` (via `scripts/snapshot_tickets.py`
      / `scripts/snapshot_after_run.sh`) and **commit it** — git history, not an external
      tracker, is the decision record. Ticket snapshots are deliverables, not noise.
- [ ] **Rule 8 — gitleaks-clean before every commit.** The tracked `.githooks/pre-commit`
      hook enforces this (`git config core.hooksPath .githooks`). Never stage secrets.
- [ ] **Rule 1 — ground CTO functions** in `query_cto_knowledge` and cite the source(s).
- [ ] **Rule 2 — record decisions** in the commit message and `docs/system-design-tradeoffs.md`.

See `AGENTS.md` for the full list (rules 1–8) and project/profile context.
