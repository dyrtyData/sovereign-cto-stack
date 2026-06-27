# Setup Guide — Sovereign CTO Stack

A repeatable, end-to-end setup of the stack from a clean clone. Each phase section is filled
in incrementally as that phase is built and verified.

> Before anything: complete the **Manual Prerequisites** checklist in the [README](../README.md)
> and run `bash scripts/preflight.sh` to confirm required `.env` keys are present.

## Phase 0 — Repo skeleton & prerequisites gate

1. Clone and enter the repo:
   ```bash
   git clone https://github.com/dyrtyData/sovereign-cto-stack.git
   cd sovereign-cto-stack
   ```
2. Create your local environment file and fill in real values:
   ```bash
   cp .env.example .env
   # edit .env — see README "Manual Prerequisites"
   ```
3. Run the preflight gate (halts on any missing required key):
   ```bash
   bash scripts/preflight.sh
   ```
4. Validate the compose skeleton:
   ```bash
   docker compose config -q   # exits 0 when valid
   ```

## Phase 1 — Hermes orchestrator boots (Portal + mem0 + Telegram)

_To be filled in during Phase 1._

## Phase 2 — CTO knowledge RAG brain

_To be filled in during Phase 2._

## Phase 3 — Tech-debt auditor loop

_To be filled in during Phase 3._

## Phase 4 — PMF research profile + `.mp4` recording

_To be filled in during Phase 4._

## Phase 5 — Documentation finalization

_To be filled in during Phase 5._
