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

## Phase 2 — CTO knowledge RAG brain (`query_cto_knowledge`)

Builds the textbook-grounded CTO brain **before** any grounded CTO function (design Q5):
convert the corpus to Markdown, stand up the local Vector MCP sidecar, index the corpus, and
bind it to Hermes so the agent can call `query_cto_knowledge` and get cited chunks.

### 0. Prerequisite — install the MCP client SDK into Hermes (one-time)

Hermes v0.17.0 ships **without** the `mcp` Python SDK, so out of the box it cannot connect to
an HTTP MCP server (`hermes mcp add` fails with _"requires HTTP transport but
mcp.client.streamable_http is not available"_). Add it (and keep Telegram) to the Hermes uv
tool environment:

```bash
uv tool install hermes-agent --with mcp --with python-telegram-bot
hermes --version    # still v0.17.0; now mcp.client.streamable_http is importable
```

### 1. Convert the textbook corpus to Markdown

```bash
bash scripts/convert_corpus.sh
```

- PDFs → **docling** (Apple MPS, ~0.1–0.4s/page). OCR is disabled: these are born-digital
  textbooks, and docling 2.68's bundled RapidOCR engine fails to initialize on this host
  (`Unsupported configuration: torch.PP-OCRv6.det.small`). Text + table extraction is all we need.
- EPUBs → **pandoc** (docling has no EPUB support; research §15).
- **Dedupe:** when both a PDF and an EPUB of the same title exist, the PDF wins (a stable slug
  maps both to the same `corpus/<slug>.md`; the PDF converts first, the EPUB is skipped).
- **Idempotent / resumable:** a source is skipped if its non-empty `corpus/<slug>.md` exists.
  The pass over many large PDFs is long-running (expected) — re-run to resume. Keep the laptop
  plugged in + lid open.
- Output lands in `corpus/` (**gitignored** — copyrighted content stays local; this script is
  tracked).

### 2. Build + start the RAG sidecar

```bash
docker compose --profile rag up -d --build rag-sidecar
curl -s localhost:8080/health            # {"status":"ready","chunks":N,"sources":M}
```

The sidecar (`rag/`) is a local Vector MCP server: **MiniLM** embeddings (all-MiniLM-L6-v2,
384 dims — same model as the mem0 round-trip, no external key) + embedded **LanceDB**, served
by **FastMCP** over Streamable HTTP at `/mcp`. On boot it ingests the mounted `corpus/` into a
persisted `rag-index` volume. The embedding model is baked into the image, so it runs offline.

Validate retrieval (ranked, cited chunks + grounding integrity):

```bash
uv run scripts/rag_smoke.py              # exit 0 on PASS
# or by hand:
curl -s -X POST localhost:8080/search -H 'content-type: application/json' \
  -d '{"query":"microservices coupling","k":3}' | jq '.results[].source_file'
```

### 3. Bind `query_cto_knowledge` to Hermes

```bash
hermes mcp add cto_knowledge --url http://localhost:8080/mcp   # answer: no auth, enable tools
hermes mcp test cto_knowledge            # ✓ Connected, 1 tool: query_cto_knowledge
hermes mcp list                          # cto_knowledge → enabled
```

The tracked reference is in `hermes/config.yaml` (`mcp_servers.cto_knowledge`). The tool appears
to the agent as `mcp_cto_knowledge_query_cto_knowledge`. `hermes/AGENTS.md` rule #1 instructs
every profile to consult it before any CTO function and cite the returned `source_file`(s).

### 4. Sync the standing instruction into `HERMES_HOME` (required for the supervised gateway)

The "always consult `query_cto_knowledge` first, then cite the grounding book(s)" rule must be
loaded by **every** surface — including the launchd/systemd-**supervised** Telegram gateway. That
matters because of how Hermes discovers context files (verified against the v0.17.0 prompt
builder, `agent/prompt_builder.py`):

- **`SOUL.md` is always loaded from `HERMES_HOME` (`~/.hermes/SOUL.md`)** — independent of the
  working directory. This is the reliable, cwd-agnostic identity slot.
- **`AGENTS.md` is loaded from the current working directory only** (no parent walk). An
  interactive `hermes`/`hermes -z` run from the repo root picks up the repo's `hermes/AGENTS.md`
  via the cwd, **but the supervised gateway's working directory is locked to `~/.hermes`**, so it
  never reads the repo's `AGENTS.md`.

The repo stays the source of truth. Sync both canonical files from `hermes/` into `HERMES_HOME`
so the supervised gateway loads the rule (the standing instruction itself lives in
`hermes/SOUL.md` — the always-loaded slot — so it applies even on the bare gateway cwd):

```bash
cp hermes/SOUL.md   ~/.hermes/SOUL.md      # always-loaded identity slot (carries the rule)
cp hermes/AGENTS.md ~/.hermes/AGENTS.md    # operating contract at the gateway cwd (~/.hermes)
chmod 600 ~/.hermes/SOUL.md ~/.hermes/AGENTS.md
```

Then restart the supervised gateway so it reloads the updated identity/context:

```bash
hermes gateway restart
```

> Re-run this sync whenever `hermes/SOUL.md` or `hermes/AGENTS.md` changes in the repo. (A clean
> clone reproduces it via these two `cp`s; the files in `~/.hermes/` are not tracked.)

> **Human-gated step (manual verification):** ask Hermes in Telegram
> _"what does the corpus say about service coupling?"_ (without naming the tool) and confirm the
> reply **proactively called `query_cto_knowledge`** and **cites the grounding book** (e.g.
> `sam-newman-building-microservices.md`). New sessions pick up the tool after binding.

## Phase 3 — Tech-debt auditor loop

_To be filled in during Phase 3._

## Phase 4 — PMF research profile + `.mp4` recording

_To be filled in during Phase 4._

## Phase 5 — Documentation finalization

_To be filled in during Phase 5._
