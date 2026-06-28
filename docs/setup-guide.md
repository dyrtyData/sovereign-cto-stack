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

mem0 OSS is **pinned to `mem0ai[nlp]>=2.0.0,<3.0.0`** (GLO-14 P1/P2, design D-1; tested against
`2.0.10`). v2.0.0 standardised the SDK return shape (`add()`/`search()` always return a dict
with a `results` list) and ships **native entity-linking** baked into `infer=True` fact
extraction — so the "graph logic" is handled under the hood with **no external graph DB and no
Neo4j**. We do not configure `graph_store`, so there is nothing to remove and `hermes/mem0.json`
loads unchanged under v2.0.0. The pin lives in the PEP 723 inline-dependency headers of the
`scripts/mem0_*.py` scripts (`mem0_roundtrip.py`, `mem0_pmf_decisions.py`, and the GLO-14 P2
`mem0_record_decision.py` / `assert_memory_accumulates.py` / `diagnose_hermes_mem0_write.py`);
`uv` resolves it per-run.

**Why the `[nlp]` extra (GLO-14 P2):** mem0 `>= v2.0.0` builds a hybrid LEXICAL index — a Postgres
`gin to_tsvector(... payload->>'text_lemmatized')` over a *lemmatized* copy of each memory. Without
spaCy, mem0 logs `Failed to load spaCy lemma model` and falls back to a simpler tokenizer (weaker
keyword recall). The `mem0ai[nlp]` extra pulls spaCy; the scripts warm mem0's own lemma loader,
which downloads the `en_core_web_sm` model once on first run and otherwise **degrades with a logged
note** (a missing model never hard-fails the gate — same self-skip philosophy as the Ollama path).
After this, the logs read `spaCy lemma model loaded` and persisted rows carry a populated
`text_lemmatized`. The first `uv run` of these scripts will download spaCy + `en_core_web_sm`.

Prove persistence (add a fact → `search()` returns it with a score), the v2.0.0 return-shape
contract, and — when the local Ollama fact-extractor is reachable — the `infer=True` native
entity-linking pass:

```bash
docker compose up -d mem0-postgres    # the pgvector backend the round-trip persists into
uv run scripts/mem0_roundtrip.py      # exit 0 on a successful round-trip
```

The round-trip's entity-linking assertion **self-skips** (logs `SKIP`, still exits 0) when
Ollama is absent, so CI never depends on a local LLM while a dev box with Ollama proves the
link automatically.

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

## Backlog P1 — Deny-by-default egress hardening (the sovereign safety layer)

The headline "sovereign"/safety layer: a reviewable allow-list (`egress/policy.yaml`)
enforced out-of-process by a **real NVIDIA OpenShell sandbox** that **refuses every outbound
destination not on the list**. This turns the sovereignty claim into an enforced property
whose load-bearing proof is a **denial you can watch happen** (design Q3-sub, Option β).

> **Prerequisite — OpenShell + Docker.** The egress layer is enforced by NVIDIA OpenShell
> (verified against `0.0.71`) with a Connected gateway (`openshell status`) and a running
> Docker daemon (OpenShell builds + runs the confined sandbox image through it). Verified on
> Docker Engine 28.1.1 (Docker Desktop 4.41.2) / Apple Silicon. No external account or API
> key is required — the layer is fully local (`openshell` + `egress/policy.yaml`).

### 1. Review the allow-list

`egress/policy.yaml` is the single auditable artifact: each `network_policies` block
(`linear_api`, `telegram_api`, `nous_inference`, `web_scrape`) names the exact `host:port`
endpoints permitted, with `enforcement: enforce`. The `filesystem_policy` / `landlock`
blocks confine reads/writes. Everything not listed on the network allow-list is denied.

### 2. Confine a workload in the sandbox

OpenShell builds the `egress/` Dockerfile and runs the workload INSIDE a sandbox bound to
the policy. The supervisor (PID 1) auto-injects `HTTPS_PROXY` and routes every outbound TLS
CONNECT through the gateway's OPA proxy:

```bash
git config core.hooksPath .githooks                       # (Phase 0) tracked secret gate
openshell status                                          # gateway must be Connected
openshell sandbox create --no-keep --policy egress/policy.yaml --from egress/ \
  -- sh -c 'curl -sS https://api.linear.app'              # allow-listed: tunnels through
```

### 3. Verify deny-by-default (negative + positive)

```bash
python3 scripts/assert_egress_policy.py    # PASS: non-allow-listed CONNECT refused; api.linear.app:443 allowed
```

The gate's **load-bearing** assertion is the **negative** test — a CONNECT to a host that
is *not* on the allow-list is **refused** (`curl: (56) CONNECT tunnel failed, response 403`)
— plus a positive-path check that `api.linear.app:443` **succeeds** (http `200`). A
positive-only check would be satisfiable by a sandbox that blocks nothing, so the negative
test is what makes the assertion meaningful. The network CONNECT layer is independent of
the Landlock filesystem layer, so this assertion holds even where Landlock `best_effort`
degrades on macOS (see [system-design-tradeoffs.md](./system-design-tradeoffs.md)).

You can watch the denial by hand (the dramatic beat captured for the showcase video):

```bash
openshell sandbox create --no-keep --policy egress/policy.yaml --from egress/ \
  -- sh -c 'curl -sS https://example.com'       # curl: (56) CONNECT tunnel failed, response 403
openshell sandbox create --no-keep --policy egress/policy.yaml --from egress/ \
  -- sh -c 'curl -sS -o /dev/null -w "%{http_code}\n" https://api.linear.app'   # 200 — allow-listed
```

> **Confining sub-tools:** any sub-tool is policy-evaluated by running it inside the sandbox
> (the supervisor injects `HTTPS_PROXY` automatically) so all its outbound HTTPS is checked
> against the allow-list. The default stack does not route through it; the sandbox + gate
> exist to *prove and enforce* the allow-list, and to ship the reviewable `policy.yaml`.

## Backlog P2 — Stripe-grounded AARRR Revenue/Retention

Grounds the PMF brief's AARRR **Revenue/Retention** cells in **real Stripe test-mode** MRR / churn
/ cohort data instead of web-scraped competitor pricing assumptions (design Q4, Option B). A
stdlib-only reference client (the `linear_mcp.py` pattern) reads Stripe and writes a JSON artifact
the brief cites.

> **Prerequisite — a Stripe TEST key.** Put `STRIPE_API_KEY` (a `sk_test_…` / `rk_test_…` key) in
> `.env`. It is **optional + ungated** (`preflight.sh` is unchanged — the stack runs without it;
> only the Stripe grounding is unavailable). The client **REFUSES** any `sk_live_`/`rk_live_` key
> and **fails loudly** (never fabricates) if the key is absent/invalid or the sandbox is empty.

### 1. Seed + read the test-mode sandbox

```bash
python3 scripts/stripe_seed.py          # idempotent (metadata tag seed:sovereign-cto-stack); TEST-key-guarded
python3 scripts/stripe_client.py        # -> recordings/stripe_metrics.json {mrr, arr, churn, cohorts[…]}
```

The fresh sandbox is seeded (12 subscriptions, 3 canceled, 3 monthly cohorts) so MRR/churn/cohorts
are genuinely real test-mode data: e.g. **MRR $1,281/mo, 25% lifetime churn, cohorts at
60%/75%/100% retention** (`recordings/stripe_metrics.json`, gitignored).

### 2. Ground the brief + verify

The `pmf_brief` skill reads `recordings/stripe_metrics.json` and grounds the AARRR
Revenue/Retention cells in it (citing the artifact, preserving the `Grounded in:` lines the gates
require). The `NO_AGENT=1` stub refreshes the metrics and injects the real numbers.

```bash
NO_AGENT=1 bash scripts/pmf_kanban_run.sh                 # writes a Stripe-grounded brief
python3 scripts/assert_stripe_grounding.py                # PASS: Revenue/Retention cite real MRR/churn
```

## Backlog P3 — SonarQube DETECT + graphify KEEP → Hermes JUDGMENT → Codegen/Moderne

Augments the tech-debt loop with a code-quality signal and a remediation back-end. **SonarQube
Community (DETECT)** supplies issues/measures; **graphify (KEEP)** supplies cross-service coupling
(SonarQube has no coupling metric); **Hermes (JUDGMENT)** synthesizes both, prioritizes the
**billing path**, and files one `[Brownfield]` ticket routed to **Codegen** (novel fixes) or
**Moderne/OpenRewrite** (recipe-amenable debt).

> **Prerequisite — SonarQube + a scan token.** A profile-gated SonarQube Community service runs in
> compose (port 9000, H2, ES bootstrap checks disabled). Generate a user token in the SonarQube UI
> and put it in the gitignored `.sonar-token` (Bearer auth). `CODEGEN_API_KEY` (optional) lives in
> `.env`. Neither appears in any tracked file (`gitleaks` clean).

### 1. Boot SonarQube + scan the audit target

```bash
docker compose --profile sonar up -d sonarqube          # community 26.x; healthcheck on /api/system/status
# scan the gitignored workspaces/microservices-demo clone (Go/Python/JS/C#; Java excluded — needs binaries):
docker run --rm --network host -v "$PWD/workspaces/microservices-demo:/usr/src" \
  sonarsource/sonar-scanner-cli -Dsonar.token="$(cat .sonar-token)"
python3 scripts/sonarqube_client.py                     # -> graphify-out/sonar-issues.json (240 issues here)
```

`sonarqube_client.py` pulls `/api/issues/search` + `/api/measures/component` (Bearer token) and
**fails loudly** if SonarQube is unreachable/unscanned (no fabrication).

### 2. Fuse the signals + file the routed ticket + verify

```bash
python3 scripts/fuse_signals.py                         # merges SonarQube onto service-coupling.json (static_analysis block)
python3 scripts/assert_graph_topology.py                # PASS: graphify coupling preserved (frontend=7, checkout=6)
# run the auditor (it now cites a SonarQube issue + a coupling hub + names a back-end), then:
python3 scripts/assert_sonar_fusion.py                  # PASS: static_analysis block + GLO-16 cites issue+hub+Codegen
python3 scripts/assert_brownfield_ticket.py             # PASS: multi-angle grounding + src/<service>/ path intact
```

The fused `static_analysis` block carries the SonarQube totals/measures, a per-service fusion
(coupling degree × issue count, `billing_path` flag), and an `exemplar_issue` selected on the
billing-path hub (`src/checkoutservice/main.go`). GLO-16 cites the real issue key, the degree-6
hub, and **Codegen** on a `Proposed refactor` line (Moderne evaluation → GLO-14).

## Backlog P4 — Full PMF loop: RICE/ICE-ranked opportunities + prior-decisions consult

Extends the thin PMF loop to the full version: **multiple opportunities ranked RICE/ICE**, grounded
in real usage + Stripe data (P2), with a `shipped`-bet feedback ledger (North Star: opportunities
shipped). Before ranking it **consults prior decisions** so it neither re-proposes a decided idea
nor loses past rationale — two real local sources: **self-hosted mem0** (pgvector `mem0-postgres`,
the unified **`memories`** collection — GLO-14 P2 repointed the consult here from the old
`pmf_decisions` silo, so it now recalls the decisions the agent loops actually accumulate, plus the
idempotent seed of the tracked `tickets/[Product]` snapshots) and **git/GitHub history** (`git log`
over `tickets/`). **No graceful degradation:** if mem0 can't persist/retrieve, the run FAILS rather
than fabricating "no prior decisions".

```bash
docker compose up -d mem0-postgres                      # the mem0 backend the consult round-trips
NO_AGENT=1 bash scripts/pmf_kanban_run.sh               # >=2 RICE-ranked opportunities + recordings/pmf_ledger.json
python3 scripts/assert_pmf_ranked.py                    # PASS: >=2 scored, ranked, grounded + a non-empty "Prior decisions consulted"
python3 scripts/assert_pmf_run.py                       # PASS: Kanban created->claimed->completed + handoff invariants
```

The brief carries a **"Prior decisions consulted"** section citing mem0 hits + git commits; the
ledger records `rice_score`, `shipped`, and `prior_decisions_consulted`. The loop correctly does
**not** re-propose the already-decided GLO-12 autonomous-remediation bet.

## GLO-14 P2 — Close the mem0 write path: `memories` accumulates every run

The headline GLO-14 slice (the user's explicit request). Both agent loops now **record the
just-filed decision into the unified `memories` collection** at the canonical position — AFTER
`save_issue` returns a ticket id and BEFORE `snapshot_after_run.sh` — via
`scripts/mem0_record_decision.py` (full agent turn, `infer=True`, self-skipping to `infer=False`
when Ollama is down). The collection genuinely accumulates run-over-run, and the PMF consult above
reads the same collection, so recall is real. Git history stays the authoritative record; mem0 is
the recall complement.

```bash
docker compose up -d mem0-postgres                      # the pgvector backend the writer persists into
uv run scripts/assert_memory_accumulates.py             # PASS: two runs both grow the count; run 2 recalls run 1; not re-seeded from tickets/
uv run scripts/diagnose_hermes_mem0_write.py            # NON-GATING Q3 probe: does hermes-agent write `memories` natively? (machine-readable verdict)
```

`assert_memory_accumulates.py` runs the writer twice in an isolated `memacc_<uuid>` collection and
asserts: each run grows the `source:"agent_run"` count; a `search()` recalls *this* run's
`decision_id`; run 2 *also* recalls run 1's decision (accumulation, not overwrite); and the recalled
text is **not a substring of any `tickets/*.md`** (the "accumulated via the write path, not
re-seeded from the snapshots" proof). `diagnose_hermes_mem0_write.py` is a diagnostic, not a gate —
it runs one loop with the deterministic helper disabled and reports whether the closed-source binary
writes `memories` on its own (the deterministic helper stays load-bearing regardless).

> mem0 OSS ≥ v2.0.0's hybrid lexical index uses spaCy lemmas via the `mem0ai[nlp]` extra (see the
> Phase-1 mem0 note above); the writer warms the lemma model so the `Failed to load spaCy lemma
> model` warning is cleared.

## GLO-14 P3 — Greptile PR review as a standing ticket-instruction line

Fully decoupled (design D-3/D-4). Every ticket the loop files now **ends its body with a standing
instruction line** so whoever picks it up runs a Greptile review on the resulting PR before merge:

> After you open a PR for this ticket, run Greptile on it (/greptile) and address the findings
> before requesting merge.

The **only** in-repo deliverable is that line — appended by the filing skills
(`hermes/skills/file_brownfield_ticket.md`, `pmf_brief.md`, `pmf_rank.md`) and the epic filer
(`scripts/file_fullbuild_ticket.py`) — plus the gate below. There is **no in-repo Greptile code,
MCP, or webhook**: the Greptile CLI, the Claude Code skill, and the `/greptile` command are set up
**globally in `~/.claude`, outside this repo** (a separate, project-agnostic task — not a GLO-14
repo deliverable). The Greptile **GitHub App** is the no-code fallback (auto-reviews on PR-open).

```bash
uv run scripts/assert_greptile_instruction.py            # PASS: newest filed ticket body + tickets/<ID>.md snapshot both carry the line
uv run scripts/assert_greptile_instruction.py GLO-14     # or check a specific identifier
```

`assert_greptile_instruction.py` mirrors `assert_brownfield_ticket.py`: it reads the newest filed
ticket back over the same Linear MCP endpoint Hermes uses **and** reads the tracked
`tickets/<ID>.md` snapshot, asserting **both** carry the instruction line (proving it survives the
full path — agent files it into Linear → `snapshot_tickets.py` persists it into git). The match is
tolerant of trivial wording-around (it keys on "run Greptile … (/greptile) … address the
findings"). The appended line is additive, so `assert_brownfield_ticket.py` /
`assert_product_ticket.py` stay exit-0.

## GLO-14 P5 — Close the PMF North Star loop (Stripe-grounded shipped-bet flip)

The Backlog-P4 PMF loop ranks opportunities into `recordings/pmf_ledger.json`, each born
`shipped: false`, and the North Star metric is `opportunities_shipped` — but nothing flipped a row,
so the loop never *closed*. P5 adds the feedback edge (design D-5 Option C): a small, deterministic,
**Stripe-grounded** joiner flips a row `false → true` from a recorded, *measured* outcome.

```bash
# 1. record a shipped-result for a bet — the metric VALUE must match real Stripe data
#    (run scripts/stripe_client.py first to refresh recordings/stripe_metrics.json)
python3 scripts/pmf_shipped_results.py record --bet 1 --metric mrr --value 1281.0
# 2. flip every recorded shipped-result onto the ledger (atomic, additive, idempotent)
python3 scripts/pmf_shipped_results.py flip
# the gate — seeds a known bet, flips an ISOLATED temp copy, cross-reads the metric vs Stripe
uv run scripts/assert_shipped_flip.py                    # PASS: target flips true; grounded in real Stripe; others stay false
python3 scripts/assert_pmf_ranked.py                     # still PASS: shipped/shipped_result are additive fields
```

`scripts/pmf_shipped_results.py` reads/writes `recordings/shipped_results.json` (bet id + measured
metric + the `stripe_metrics.json` grounding ref) and exposes `flip_shipped(ledger, results,
stripe_metrics) -> int`: it joins records onto the ledger by bet id (the opportunity **title** or
its **rank**), flips matching rows `shipped false → true`, and stamps `grounded_in +=
["stripe_metrics.json"]` — reading the whole ledger and writing it back via `os.replace` so **no
other ledger key is clobbered** (the `fuse_signals.py` atomic/additive pattern). A result is
**refused** unless its metric value equals a value actually present in `recordings/stripe_metrics.json`
(the no-fabrication contract — "shipped" must be a *measured* Stripe outcome, not a hand-set flag);
no new Stripe surface or egress endpoint is added (it reuses the already-computed metrics artifact via
`stripe_client.load_metrics()`). The joiner is wired into `scripts/pmf_kanban_run.sh` right after the
ledger write (a no-op when nothing is recorded), and each flip — itself a decision — is recorded into
the unified `memories` collection via `mem0_record_decision.py` (depends on P2's write path).
`assert_shipped_flip.py` operates on an **isolated temp copy** of the ledger (mirroring
`assert_memory_accumulates.py`'s throwaway collection) so the tracked `recordings/pmf_ledger.json`
stays all-false and the working tree stays clean.

## Closeout — the comprehensive showcase montage (hybrid montage, design Q6)

The submitted demo is a **hybrid montage**: live split-screen captures for the inherently-visual
hero loops (tech-debt graphify + ticket-in-browser; PMF brief) plus short purpose-built segments
for the non-visual proofs (denied egress CONNECT, Stripe-grounded AARRR, SonarQube issues, ranked
PMF). A **simple `ffmpeg concat`** (no editing suite — so it regenerates from a clean clone)
stitches exactly the segments that pass `verify_recording.py`, with generated title cards between
them. A missing/failed segment is simply dropped — the automatic best-video-currently-possible
fallback.

```bash
# (optional) capture a named segment live onto :99 (each P-slice can emit its own):
bash scripts/record_run.sh egress-denial                # SEG_LIVE=1 drives the real OpenShell denial
bash scripts/record_run.sh hero                         # the visual hero loop (real tool calls + ticket-in-browser ending)

# assemble + gate the montage (reads whatever segments/artifacts are present):
python3 scripts/build_showcase_video.py                 # -> recordings/showcase_<ts>.mp4 (+ showcase_manifest.json)
python3 scripts/assert_showcase_video.py                # PASS: valid non-static concat + >= the guaranteed hero loop(s)
```

> **P0 ticket-in-browser ending (the reproducible default).** The throwaway container Chromium has
> no Linear session, so navigating to the live ticket URL hit Linear's **auth wall**.
> `scripts/render_ticket_card.py` renders the tracked local `tickets/<ID>.md` snapshot to a
> self-contained `file://` HTML, and `record_run.sh` ends the hero capture on **that** page — the
> filed ticket visible in the browser, no auth. This stays the **default** ending; the optional
> authenticated live-Linear ending is the GLO-14 P3 add-on below.

> **Title cards** are self-contained single-file HTML (`scripts/render_title_card.py`, the
> `render_service_graph.py` house style) painted onto `:99`; `build_showcase_video.py` renders them
> to short clips (headless-browser PNG, with an ffmpeg-drawtext fallback) and normalizes every clip
> to a common WxH/fps/codec so the demuxer concat is safe across heterogeneous sources.

### GLO-14 P3 — fuller multi-component montage, memory view, optional authenticated ending

`build_showcase_video.py`'s catalogue now tells the **D-2 segment story**: the visual hero loop +
the Stripe/egress/PMF data surfaces (included when their artifact exists) + **four always-rendered
title-carded chapters** — the **mem0 memory view**, the **Kanban** create→claim→complete lifecycle,
the **Greptile** PR-review instruction, and the **Linear ticket ending**. `assert_showcase_video.py`
now requires those D-2 segments (`SHOWCASE_MIN_SEGMENTS=5` + a required-id check; override via
`SHOWCASE_REQUIRED_IDS` for a deliberately smaller montage).

**Read-only memory view (P1 made visible).** `scripts/render_memory_card.py` queries the unified
`memories` rows + mem0-native entity links and renders them to a self-contained `file://` HTML
(the `render_ticket_card.py` marked.js card pattern — read-only, no auth, no writes):

```bash
docker compose up -d mem0-postgres
uv run scripts/render_memory_card.py --out recordings/memory_<ts>.html   # the read-only view
uv run scripts/assert_memory_view_grows.py                               # scripts "more rows after a loop"
```

`assert_memory_view_grows.py` renders the card with `--baseline` (BEFORE), runs one decision
through the real `mem0_record_decision` write path, renders again `--against` that baseline
(AFTER), and asserts the parsed row count **strictly grew** and the after-card highlights the new
row. It runs against a throwaway isolated collection (never pollutes the live `memories`).

**Optional authenticated live-Linear ending.** The default ending stays the `file://` snapshot.
To end instead on the **real** logged-in Linear ticket UI:

```bash
# 1. populate the gitignored persistent Chromium profile ONCE (needs your click — log in to Linear):
chromium --user-data-dir="$PWD/recorder-profile"          # then sign in to Linear in that window, quit
# 2. record with the live ending enabled (a persistent profile is bind-mounted into the recorder):
TICKET_LIVE_URL=1 bash scripts/record_run.sh hero
```

`docker-compose.yml` bind-mounts `./recorder-profile` → `/recorder-profile` (gitignored — it holds
a live session, **never committed**, AGENTS.md rule 3/8); `record_run.sh`'s `TICKET_LIVE_URL=1`
block resolves the filed ticket URL and launches the right-pane browser **with**
`--user-data-dir=/recorder-profile` so the session carries into the capture. Without a populated
profile Chromium still hits the auth wall, so the snapshot ending remains the safe default.

> **What is automated vs. human here.** The default `file://` path and the persistent-profile
> **wiring** are both gated: `assert_persistent_profile_wiring.py` drives the real `launch_browser`
> path with a throwaway `--user-data-dir` and asserts the recorder launched Chromium **with** the
> flag (no real Linear session needed). Two things stay genuinely human: eyeballing that a
> *real-session* recording ends on the actual authenticated Linear page, and the collaborative final
> montage segment ordering (design D-2 micro-detail).

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
