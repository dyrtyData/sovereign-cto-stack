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

Reproduces the orchestration core from a clean clone: install Hermes, authenticate to
Portal, stand up self-hosted mem0 on pgvector, wire mem0 as Hermes' memory provider, and
prove the loop with a Telegram "hello world."

### 1. Install Hermes

```bash
uv tool install hermes-agent          # provides `hermes`, `hermes-acp`, `hermes-agent`
hermes --version                      # -> Hermes Agent v0.17.0 (or later)
```

> The outline references `hermes setup --portal`; in v0.17.x this is the same as
> `hermes portal login` (the human-readable alias). Either works.

### 2. Stand up mem0's pgvector backend

```bash
docker compose up -d mem0-postgres
docker compose port mem0-postgres 5432    # confirm host mapping (default 0.0.0.0:5433)
```

The container publishes to **host port 5433** by default (the `MEM0_PG_HOST_PORT` var) to
avoid colliding with a host-native Postgres on 5432, common on dev machines. The pgvector
extension is created automatically on first init by `scripts/init-pgvector.sql`.

### 3. Authenticate to Nous Portal  ⚠️ needs your browser click

```bash
hermes portal login        # == `hermes setup --portal`
# device-code OAuth -> approve in the browser -> writes ~/.hermes/auth.json
hermes model               # pick a Nous model interactively (live /v1/models list)
```

### 4. Wire mem0 as the memory provider

The tracked reference config lives at `hermes/config.yaml` and `hermes/mem0.json`. The
provider is registered with:

```bash
hermes config set memory.provider mem0
```

mem0 runs as the **SDK on the host** against the `mem0-postgres` pgvector service (OSS mode;
review decision — the full mem0 OSS server + Next.js dashboard is deferred to Phase 5). The
default OSS config uses a **local HuggingFace embedder** (all-MiniLM-L6-v2, 384 dims) and the
local **Ollama** endpoint for fact extraction, so no external embedding/LLM key is required.
Platform mode is the fallback: set `MEM0_API_KEY` and switch `hermes/mem0.json` `mode` to
`platform` (design Q6).

Prove persistence (add a fact → `search()` returns it with a score):

```bash
uv run scripts/mem0_roundtrip.py      # exit 0 on a successful round-trip
```

### 5. Wire Telegram and start the gateway

Copy the `TELEGRAM_*` values from the repo `.env` into `~/.hermes/.env` (or run
`hermes gateway setup` interactively):

```bash
# the keys: TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, TELEGRAM_HOME_CHANNEL
hermes gateway start                  # or: hermes gateway run  (foreground)
```

Validate the bot token independently:

```bash
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"   # ok: true
```

### 6. Hello world  ⚠️ needs you to confirm in Telegram

Send a message to the bot (or have the orchestrator send one) and confirm it arrives to the
allowed user. A first chat turn also creates a session, after which
`hermes sessions export /tmp/sess.jsonl` produces a non-empty JSONL.

> **Human-gated steps:** the Portal browser OAuth (step 3) and confirming the Telegram
> hello-world (step 6) require your action. Everything else is scripted/automated.

## Phase 2 — CTO knowledge RAG brain

_To be filled in during Phase 2._

## Phase 3 — Tech-debt auditor loop

_To be filled in during Phase 3._

## Phase 4 — PMF research profile + `.mp4` recording

_To be filled in during Phase 4._

## Phase 5 — Documentation finalization

_To be filled in during Phase 5._
