# Setup Guide — Sovereign CTO Stack

A repeatable, end-to-end setup of the stack from a clean clone. Each phase section is filled
in incrementally as that phase is built and verified.

> Before anything: complete the **Manual Prerequisites** checklist in the [README](../README.md)
> and run `bash scripts/preflight.sh` to confirm required `.env` keys are present.

## Phase 0 — Repo skeleton & prerequisites gate

1. Clone and enter the repo, then enable the tracked secret-gate hook:
   ```bash
   git clone https://github.com/dyrtyData/sovereign-cto-stack.git
   cd sovereign-cto-stack
   git config core.hooksPath .githooks   # enables .githooks/pre-commit (gitleaks gate)
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

## Phase 3 — Tech-debt auditor loop (graphify → grounded `[Brownfield]` Linear ticket)

The hackathon hero loop: map the audit target with graphify, derive its service-level
coupling, have the `CTO-Architecture` profile consult the RAG brain, and file a
HumanLayer-ready `[Brownfield]` Linear ticket on a cron.

### 1. Map the audit target with graphify

```bash
bash scripts/run_graphify.sh
```

This clones `GoogleCloudPlatform/microservices-demo` (Online Boutique) into
`workspaces/` (**gitignored — never deployed; K8s-only upstream, source-graph only**),
prunes non-code assets (READMEs / images / html / txt) so the run needs **no LLM API
key** (a code-only corpus runs fully local via tree-sitter), and writes:

- `graphify-out/graph.json` — the NetworkX AST/call graph (2.5k nodes).
- `graphify-out/GRAPH_REPORT.md` + `graphify-out/graph.html` — the "god nodes" report
  and the interactive viz (generated via `graphify cluster-only --no-label`, no LLM).
- `graphify-out/service-coupling.json` — the **deterministic service-level coupling
  map** (`scripts/service_topology.py`). The raw graphify graph is file/symbol-level, so
  the service-to-service topology (how many distinct gRPC backends each service dials)
  is derived from the gRPC client wiring in the source. Online Boutique's hubs:
  **frontend = 7 outbound gRPC edges, checkoutservice = 6** (research §13).

> `GRAPHIFY_DEEP=1 bash scripts/run_graphify.sh` adds the semantic/community layer via a
> configured backend (needs an LLM key). The default AST-only path is offline + deterministic.

Verify the topology, then open the **legible** service-level graph:

```bash
python3 scripts/assert_graph_topology.py    # PASS: frontend=7, checkoutservice=6
open graphify-out/service-graph.html        # clean ~11-node service graph (use this)
```

> `graphify-out/graph.html` is graphify's **raw** file/symbol graph (hundreds of
> nodes) — accurate but unreadable. `scripts/render_service_graph.py` (run as step 5
> of `run_graphify.sh`) reads the derived `service-coupling.json` and emits
> `graphify-out/service-graph.html`: ~11 service nodes, directed gRPC edges, with
> `frontend` (7 outbound) and `checkoutservice` (6) emphasized by size/color/label.
> It is self-contained (vis-network from CDN, data embedded), opens standalone in a
> browser, and is the surface the Phase-4 screen recording captures. Like the other
> `graphify-out/` outputs it is gitignored; the renderer script is tracked.

### 2. Create the `CTO-Architecture` auditor profile

```bash
hermes profile create cto-architecture --clone \
  --description "Tech-debt & architecture auditor: reads the graphify coupling map, consults query_cto_knowledge, files HumanLayer-ready [Brownfield] Linear tickets."
```

`--clone` copies the orchestrator's `config.yaml` (so the profile inherits the
`cto_knowledge` **and** `linear` MCP bindings), `.env`, SOUL.md and skills. Then install
the repo-tracked auditor identity + skill into the profile home:

```bash
PROF=~/.hermes/profiles/cto-architecture
cp hermes/profiles/cto-architecture/SOUL.md "$PROF/SOUL.md"     # always-loaded identity slot
mkdir -p "$PROF/skills/file_brownfield_ticket"
cp hermes/skills/file_brownfield_ticket.md "$PROF/skills/file_brownfield_ticket/SKILL.md"
chmod 600 "$PROF/SOUL.md" "$PROF/skills/file_brownfield_ticket/SKILL.md"
```

> **Re-sync after any edit (same pattern as Phase 2 §4).** The repo is the source of
> truth; the `~/.hermes` copies are not tracked. Whenever `hermes/SOUL.md`,
> `hermes/profiles/cto-architecture/SOUL.md`, or `hermes/skills/file_brownfield_ticket.md`
> changes in the repo, re-run the three `cp`s above **plus** `cp hermes/SOUL.md
> ~/.hermes/SOUL.md` (the orchestrator identity slot), `chmod 600` them, and restart any
> running gateway so the supervised surface reloads. The grounding rule — *decompose the
> question, issue multiple angle queries, cite the union of returned `source_file`s* —
> lives in all three (orchestrator SOUL, auditor SOUL, the skill) so it holds in every
> surface and generalizes to the Phase-4 PMF profile.

### 3. Bind Linear to the auditor profile  ⚠️ one-time browser OAuth

```bash
hermes mcp install linear        # device-code OAuth -> approve in the browser
hermes mcp test linear           # ✓ Connected, 38 tools
```

> **Per-profile token gotcha (v0.17.0):** OAuth tokens cache per `HERMES_HOME`. If you
> approved Linear on the `default` profile but run the auditor as `cto-architecture`, copy
> the cached token across (same Linear account, already approved) so the auditor can reach
> Linear in non-interactive (cron / one-shot) runs:
>
> ```bash
> mkdir -p ~/.hermes/profiles/cto-architecture/mcp-tokens
> cp -p ~/.hermes/mcp-tokens/linear*.json ~/.hermes/profiles/cto-architecture/mcp-tokens/
> chmod 600 ~/.hermes/profiles/cto-architecture/mcp-tokens/*.json
> ```
>
> **`save_issue`, not `create_issue`:** this Linear MCP server exposes `save_issue` /
> `list_issues` and uses `team` / `labels` (the human forms of GraphQL `teamId`/`labelIds`).
> The `Brownfield` label is created once in the workspace (`create_issue_label`), then
> `save_issue(labels=["Brownfield"])` resolves it by name.

### 4. Run the hero loop (audit → consult RAG → file ticket)

```bash
hermes -p cto-architecture -z "Run the tech-debt audit loop: read graphify-out/service-coupling.json, identify the highest-degree coupling hub, then GROUND it by issuing MULTIPLE query_cto_knowledge calls — one per dimension (coupling; technical-debt economics/interest; service decomposition & granularity tradeoffs; delivery/throughput performance) — and cite the UNION of the distinct source_file(s) those queries return. Then file ONE HumanLayer-ready [Brownfield] Linear ticket (team 'Global South Ai Safety', labels ['Brownfield'], priority 2) naming the concrete src/<service>/ file(s) with one 'Grounded in:' line per cited source_file. Use the file_brownfield_ticket skill." \
  --skills file_brownfield_ticket --yolo
```

The auditor consults `query_cto_knowledge` **before** filing (design Q5), and does so by
**multi-angle querying**: it decomposes the finding into its dimensions, issues a
separate query per dimension, and cites the **union** of the distinct corpus
`source_file`s those queries return — never one query / one citation, never a
pre-curated title list (let retrieval decide). The resulting ticket names exact files
(`src/frontend/main.go`, `src/checkoutservice/main.go`, `protos/demo.proto`), the
measured signal, a refactor proposal, a `Grounded in:` line per cited source, and
acceptance criteria. For the Online Boutique hub the union includes (among others)
`software-architecture.md`, `managing-technical-debt.md`,
`sam-newman-building-microservices.md`, `balancing-coupling-in-software-design.md`,
`strategic-monoliths-and-microservices.md`, and `accelerate.md`. Verify the filed ticket:

```bash
python3 scripts/assert_brownfield_ticket.py   # PASS: label + concrete file + multi-source citations
```

### 5. Schedule the loop on a cron

```bash
hermes -p cto-architecture cron create "0 9 * * *" \
  "Run the tech-debt audit loop ... file a [Brownfield] Linear ticket ..." \
  --name brownfield-tech-debt-audit \
  --skill file_brownfield_ticket \
  --workdir "$PWD" \
  --deliver telegram
hermes -p cto-architecture cron list           # shows the registered job
```

> The cron job fires only while the **`cto-architecture` profile's gateway is running**
> (`hermes -p cto-architecture gateway start`, or `hermes gateway install` as a user
> service). The job is registered/persisted (`~/.hermes/profiles/cto-architecture/cron/jobs.json`)
> regardless; the gateway is what ticks it. Keep the laptop plugged in + lid open for
> scheduled runs.

## Phase 4 — PMF research profile + `.mp4` recording

Stands up the second use-case profile (`CTO-Market`, PMF research) coordinating with the
orchestrator over the **shared single-host Kanban board** (`~/.hermes/kanban.db`, design Q4),
and the external **Xvfb + ffmpeg** recorder sidecar that captures an autonomous run to
`recordings/run_<ts>.mp4` for the hackathon submission.

> ⚠️ **Keep the laptop PLUGGED IN with the LID OPEN for any recorded run.** `caffeinate -dimsu`
> blocks idle sleep, but on battery it cannot beat lid-close sleep — a closed lid will kill the
> capture + the live agent mid-run. Only you can satisfy this (Manual Prerequisite #5).

### 1. Create the `CTO-Market` PMF profile

```bash
hermes profile create cto-market --clone \
  --description "PMF / growth researcher: scrapes the web, cross-references query_cto_knowledge growth/PMF texts, emits a textbook-cited strategic brief, hands off via the shared Kanban board."
```

`--clone` copies the orchestrator's `config.yaml` (so the profile inherits the `cto_knowledge`
**and** `linear` MCP bindings), `.env`, SOUL.md, and skills. All profiles share the one
`~/.hermes/kanban.db` (design Q4) — that is how the orchestrator and the specialists coordinate
on a single host. Install the repo-tracked identity + skill into the profile home (same
re-sync pattern as Phase 2 §4 / Phase 3 §2 — the repo is the source of truth; the `~/.hermes`
copies are not tracked):

```bash
PROF=~/.hermes/profiles/cto-market
cp hermes/profiles/cto-market/SOUL.md "$PROF/SOUL.md"          # always-loaded identity slot
mkdir -p "$PROF/skills/pmf_brief"
cp hermes/skills/pmf_brief.md "$PROF/skills/pmf_brief/SKILL.md"
chmod 600 "$PROF/SOUL.md" "$PROF/skills/pmf_brief/SKILL.md"
hermes -p cto-market mcp list   # cto_knowledge + linear both ✓ enabled (inherited via --clone)
```

> The PMF SOUL + `pmf_brief` skill carry the **same multi-angle grounding discipline** as the
> orchestrator and the auditor: decompose the question into dimensions, issue **one
> `query_cto_knowledge` call per dimension** (problem/solution fit; target customer & sizing;
> experimentation/validated learning; growth loops), and cite the **union** of the distinct
> `source_file`s retrieval returns — never one query, never a pre-curated title list.

### 2. Run the PMF research task through the shared Kanban board

`scripts/pmf_kanban_run.sh` drives the full board lifecycle around a PMF run so it is
deterministic and verifiable — **create (ready) → claim (running) → run the agent → complete
(done) with a structured handoff** (`--summary` + `--metadata` JSON):

```bash
bash scripts/pmf_kanban_run.sh "Is there product-market fit for an autonomous AI tech-debt auditor for Series-A engineering teams?"
```

The `cto-market` agent (pmf_brief skill) scrapes the web, multi-angle-queries
`query_cto_knowledge`, and writes a textbook-cited strategic brief to
`recordings/pmf_brief_run_<ts>.md`. The script derives the handoff summary/metadata from the
brief and closes the task with `kanban complete`, producing a `task_runs` row anyone (the
orchestrator, a downstream task) can read.

> **Long run — detach it.** A live brief takes several minutes of model + web time. Launch it
> detached so it survives a closed terminal (and keep the lid open):
> ```bash
> ( nohup caffeinate -dimsu bash scripts/pmf_kanban_run.sh "<question>" > recordings/pmf.log 2>&1 < /dev/null & )
> ```
> `NO_AGENT=1 bash scripts/pmf_kanban_run.sh` writes a deterministic stub brief instead — it
> still exercises the full Kanban lifecycle + the citation artifact (useful for CI / a dry run).

Verify the brief artifact (textbook citation) **and** the Kanban handoff:

```bash
python3 scripts/assert_pmf_run.py    # PASS: brief cites a real corpus *.md; task ready->running->done + handoff row
```

### 3. Build + start the recorder sidecar

```bash
docker compose --profile record up -d --build recorder
docker compose exec -T recorder xdpyinfo -display :99   # display :99 up == healthy
```

The recorder (`recorder/`) bundles **Xvfb** (virtual X display `:99`), **ffmpeg** (`x11grab`),
a minimal WM (fluxbox), and **chromium** (the visible browser surface). It runs `idle` to keep
the display up and HEALTHY; `scripts/record_run.sh` drives capture via `docker exec`. The
`recordings/` and `graphify-out/` directories are **host bind-mounts** (not named volumes) so
the host (`ffprobe`, the non-blank frame check, the browser surface source) can read the `.mp4`
and the `service-graph.html` directly. Both are gitignored.

### 4. Record an autonomous run to `.mp4`

```bash
bash scripts/run_graphify.sh          # ensure graphify-out/service-graph.html exists (hero surface)
bash scripts/record_run.sh hero       # default: the Phase-3 tech-debt hero loop
# or:  bash scripts/record_run.sh pmf "<question>"   # record the PMF research run
```

`record_run.sh`, in order: (1) brings the recorder up healthy; (2) **paints the visible
surface onto `:99` BEFORE capture** — for `hero` a browser showing
`graphify-out/service-graph.html` (the legible `frontend=7` / `checkout=6` coupling graph),
for `pmf` the PMF brief / research surface; (3) **guards** with a non-blank check (a client
window must be mapped — never records black); (4) starts ffmpeg
(`-pix_fmt yuv420p -movflags +faststart`); (5) triggers the chosen agent job; (6) stops the
recorder **gracefully** (writes `q` to ffmpeg's stdin, then SIGINT — both finalize the moov
atom); (7) verifies the output.

> **Why a visible surface (review decision):** `x11grab` records PIXELS, so a text-only/headless
> agent run would record a black frame. The browser graph (hero) or the PMF browser session is
> rendered onto `:99` first, and `record_run.sh` refuses to start capture if no window is mapped.

> **Long run — detach it** (same as the PMF run; keep the lid open):
> ```bash
> ( nohup caffeinate -dimsu env PATH="$HOME/.local/bin:$PATH" RECORD_SECONDS=300 \
>     bash scripts/record_run.sh hero > recordings/record.log 2>&1 < /dev/null & )
> ```
> `NO_AGENT=1 RECORD_SECONDS=10 bash scripts/record_run.sh hero` records the surface only
> (no live model call) — a fast way to validate the capture pipeline.

Verify the recording (valid container, duration>0, moov present, non-blank mid-run frame):

```bash
python3 scripts/verify_recording.py recordings/run_hero_<ts>.mp4   # RESULT: PASS
```

> **Tooling notes (this host):** the recorder image installs `chromium` + `fonts-dejavu`/
> `fonts-liberation` so the surface text/labels are legible. `service-graph.html` pulls
> `vis-network` from a CDN — chromium in the container reaches it (the graph renders fully); the
> page's dark header/legend text alone already makes the frame non-blank if the CDN were
> unreachable. The non-blank check uses ffmpeg `signalstats`: it reads `YSTDEV` when the build
> exposes it, else the `YMAX-YMIN` luma range (a flat/black frame ~0; a rendered surface spans
> wide).

> **Human-gated (manual verification):** play `recordings/run_<ts>.mp4` and confirm it visibly
> shows the run (1–3 min, hackathon-suitable); read the PMF brief and confirm it is coherent
> with sensible citations; confirm the laptop stayed plugged in + lid open for the recorded run.

## End-to-end setup from a clean clone (the full walkthrough)

This section is the single coherent path a new operator follows to bring the whole stack up
from a fresh `git clone`. It threads together every phase above plus the two human-gated OAuth
approval points and the `~/.hermes` sync steps. Run it top to bottom.

### 0. Prerequisites (do these by hand first — the build halts until they are done)

Complete the **Manual Prerequisites** checklist in the [README](../README.md). In brief:

1. **Nous Portal key** — put `NOUS_PORTAL_API_KEY` in `.env` (from
   <https://portal.nousresearch.com/>).
2. **Telegram bot** — message **@BotFather** (`/newbot`), then **@userinfobot** for your numeric
   id; put `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USERS` in `.env`.
3. **Laptop plugged in + lid open** for any long-running or recorded run (only you can satisfy
   this; `caffeinate -dimsu` blocks idle sleep but not lid-close on battery).

Two browser OAuth approvals happen *during* the build, not now — they are flagged inline below
with :warning: and require **your click**:

- **Portal login** — `hermes portal login` (== `hermes setup --portal`), in **step 2** (Phase 1).
- **Linear MCP** — `hermes mcp install linear`, in **step 5** (Phase 3); separate from
  HumanLayer's Linear connection.

```bash
git clone https://github.com/dyrtyData/sovereign-cto-stack.git
cd sovereign-cto-stack
cp .env.example .env          # then fill in the real values from the prerequisites
bash scripts/preflight.sh     # HALTS until NOUS_PORTAL_API_KEY + TELEGRAM_* are present
docker compose config -q      # validate the full compose stack
```

### 1. Hermes + memory + Telegram (Phase 1)

```bash
uv tool install hermes-agent --with mcp --with python-telegram-bot   # mcp SDK needed in step 4
hermes --version                                  # v0.17.0+
docker compose up -d mem0-postgres                # pgvector backend (host port 5433)
hermes portal login                               # :warning: APPROVE IN BROWSER (Portal OAuth)
hermes model                                      # pick a Nous model
hermes config set memory.provider mem0
uv run scripts/mem0_roundtrip.py                  # exit 0 == memory persistence proven
# copy TELEGRAM_* into ~/.hermes/.env (or `hermes gateway setup`), then:
hermes gateway start
```

### 2. CTO RAG brain (Phase 2)

```bash
bash scripts/convert_corpus.sh                    # docling (PDF) + pandoc (EPUB) -> corpus/*.md
docker compose --profile rag up -d --build rag-sidecar
curl -s localhost:8080/health                     # {"status":"ready","chunks":N,"sources":M}
uv run scripts/rag_smoke.py                        # exit 0 == cited-chunk retrieval works
hermes mcp add cto_knowledge --url http://localhost:8080/mcp
hermes mcp test cto_knowledge                     # ✓ Connected, 1 tool: query_cto_knowledge
```

**Sync the standing instruction into `HERMES_HOME`** so the supervised gateway loads it
(detailed reasoning in *Phase 2 → §4* above — `SOUL.md` is always loaded from `~/.hermes`,
`AGENTS.md` only from the cwd, and the supervised gateway's cwd is locked to `~/.hermes`):

```bash
cp hermes/SOUL.md   ~/.hermes/SOUL.md      # always-loaded identity slot (carries the rule)
cp hermes/AGENTS.md ~/.hermes/AGENTS.md
chmod 600 ~/.hermes/SOUL.md ~/.hermes/AGENTS.md
hermes gateway restart
```

### 3. Tech-debt auditor profile + Linear (Phase 3 — the hero loop)

```bash
bash scripts/run_graphify.sh                      # -> graphify-out/service-coupling.json (frontend=7, checkout=6)
hermes profile create cto-architecture --clone    # inherits cto_knowledge MCP binding
# sync the auditor identity + skill into the profile home (repo is source of truth):
PROF=~/.hermes/profiles/cto-architecture
cp hermes/profiles/cto-architecture/SOUL.md "$PROF/SOUL.md"
mkdir -p "$PROF/skills/file_brownfield_ticket"
cp hermes/skills/file_brownfield_ticket.md "$PROF/skills/file_brownfield_ticket/SKILL.md"
chmod 600 "$PROF/SOUL.md" "$PROF/skills/file_brownfield_ticket/SKILL.md"

hermes mcp install linear                         # :warning: APPROVE IN BROWSER (Linear OAuth)
# per-profile token gotcha (v0.17.0): copy the approved token into the profile cache
mkdir -p "$PROF/mcp-tokens"
cp -p ~/.hermes/mcp-tokens/linear*.json "$PROF/mcp-tokens/"
chmod 600 "$PROF/mcp-tokens/"*.json
```

Run the hero loop (audit → multi-angle ground → file `[Brownfield]` ticket), then snapshot it
into git (see *Ticket tracking* below), and schedule it on cron — all documented in **Phase 3**
above.

### 4. PMF profile + recording (Phase 4)

```bash
hermes profile create cto-market --clone
PROF=~/.hermes/profiles/cto-market
cp hermes/profiles/cto-market/SOUL.md "$PROF/SOUL.md"
mkdir -p "$PROF/skills/pmf_brief"; cp hermes/skills/pmf_brief.md "$PROF/skills/pmf_brief/SKILL.md"
mkdir -p "$PROF/mcp-tokens"; cp -p ~/.hermes/mcp-tokens/linear*.json "$PROF/mcp-tokens/"
chmod 600 "$PROF/SOUL.md" "$PROF/skills/pmf_brief/SKILL.md" "$PROF/mcp-tokens/"*.json

bash scripts/pmf_kanban_run.sh "<your PMF question>"   # brief + [Product] ticket via Kanban
docker compose --profile record up -d --build recorder
bash scripts/run_graphify.sh                           # ensure the hero surface exists
bash scripts/record_run.sh hero                        # -> recordings/run_hero_<ts>.mp4
```

> Keep the laptop **plugged in with the lid open** for the recorded run (Manual Prerequisite).

## Ticket tracking (git is the authoritative decision record)

Every Linear ticket the agents file is **snapshotted into the tracked `tickets/<ID>.md`** so the
decision record lives in git, not only in Linear (design "Desired End State": git history is
authoritative; mem0 is a complement). The tracked `scripts/snapshot_tickets.py` reads each ticket
back over the same Linear MCP endpoint Hermes uses (via `scripts/linear_mcp.py`, OAuth token from
the gitignored Hermes cache) and writes title / identifier / url / labels / priority / full
description + a `snapshot captured:` timestamp.

**This is wired into the filing workflow, not a one-off:**

- The auditor and PMF skills (`hermes/skills/file_brownfield_ticket.md`,
  `hermes/skills/pmf_brief.md`) end with a **"persist into git"** step instructing the operator
  to run the snapshot after a ticket is filed.
- `scripts/snapshot_after_run.sh` is the convenience wrapper: it snapshots the explicit ids you
  pass, or (with none) **discovers every `[Brownfield]`/`[Product]` ticket on the team and
  snapshots them all**. The Phase-4 run scripts call it as a post-step so a recorded/cron run
  leaves the git snapshot up to date automatically.

```bash
# after any filed ticket (one or more ids):
python3 scripts/snapshot_tickets.py GLO-13
# or discover + snapshot all agent-filed tickets in one go:
bash scripts/snapshot_after_run.sh
git add tickets/ && git commit -m "snapshot filed Linear tickets"
```

> `tickets/` is intentionally **not** gitignored (ticket bodies are non-secret;
> `gitleaks protect --staged` is clean over them). Re-running the snapshot is idempotent — it
> overwrites `tickets/<ID>.md` with the current Linear state.

## Final public-readiness pass (before sharing the repo)

```bash
gitleaks detect --no-banner                       # no secret committed (also: gitleaks protect --staged)
docker compose config -q                          # full stack still valid
python3 scripts/check_doc_links.py                # no broken internal links across docs/**
bash scripts/fresh_clone_smoke.sh                 # clone path: cp .env.example .env (stubs) -> preflight HALTS
```

The two browser OAuth steps (Portal, Linear) and the Telegram hello-world remain the only
human-gated points; everything else is scripted and reproducible from this guide.
