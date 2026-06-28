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
  fuses a real **SonarQube** code-quality scan (DETECT) with graphify coupling (KEEP), consults
  the RAG brain (JUDGMENT), and files a `[Brownfield]` Linear ticket precise enough for HumanLayer,
  naming a remediation back-end (Codegen / Moderne).
- **PMF loop** — the `CTO-Market` profile ranks multiple opportunities by **RICE/ICE**, grounded
  in the corpus + **real Stripe (test-mode) MRR/churn/cohort** data + a prior-decisions consult
  (self-hosted mem0 + git history), with a shipped-bet feedback ledger.
- **Deny-by-default egress (sovereign safety)** — sub-tools run inside a real **NVIDIA
  OpenShell / NemoClaw** sandbox enforcing an allow-list `egress/policy.yaml`; a non-allow-listed
  CONNECT is refused (the load-bearing negative test).
- **Recording** — an external Xvfb + ffmpeg sidecar captures autonomous runs to `.mp4`, stitched
  into a hybrid-montage showcase video.

## Build phases

The build is **strictly sequential and gated** — each phase is a thin vertical slice that boots
and is verifiable before the next begins.

**Original build (GLO-13 Part A — shipped):**

- **Phase 0** — Public-safe repo skeleton, prerequisites gate & docs scaffolding.
- **Phase 1** — Hermes orchestrator boots end-to-end (Portal + mem0 + Telegram).
- **Phase 2** — CTO knowledge RAG brain (corpus -> Vector MCP -> `query_cto_knowledge`).
- **Phase 3** — Tech-debt auditor loop (graphify -> grounded `[Brownfield]` Linear ticket).
- **Phase 4** — PMF research profile + autonomous-run `.mp4` recording.
- **Phase 5** — Documentation finalization + comprehensive "full-build" Linear ticket (GLO-13).

**Prioritized backlog (GLO-13 Part B, P0–P4 + closeout — shipped):**

- **P0** — Demo authenticity: the recorded run streams **real** `[live] tool … completed` events
  (sourced from the Hermes session store), gated by `assert_demo_authenticity.py`.
- **P1** — Deny-by-default egress via a real **NVIDIA OpenShell/NemoClaw** sandbox; the gate's
  load-bearing assertion is a **negative test** (non-allow-listed CONNECT refused) —
  `assert_egress_policy.py`.
- **P2** — **Stripe**-grounded AARRR Revenue/Retention from real test-mode data —
  `assert_stripe_grounding.py`.
- **P3** — **SonarQube** DETECT fused with graphify coupling -> Hermes JUDGMENT -> Codegen/Moderne
  remediation — `assert_sonar_fusion.py`.
- **P4** — Full PMF loop: **RICE/ICE-ranked** opportunities + mem0/git prior-decisions consult +
  shipped-bet feedback — `assert_pmf_ranked.py`.
- **Closeout** — hybrid-montage **showcase video** (`assert_showcase_video.py`) + the next
  full-build epic (**GLO-14**) authored and snapshotted.

**GLO-14 (in progress — the system learns and reviews):**

- **P1** — mem0 OSS pinned to **`mem0ai[nlp]>=2.0.0`** (native entity-linking, no Neo4j; spaCy
  lemmatized lexical index), gated by the extended round-trip — `mem0_roundtrip.py`.
- **P2** — **Close the mem0 write path:** both agent loops now record the just-filed decision into
  the unified **`memories`** collection (`mem0_record_decision.py`, `infer=True`) at the canonical
  "after `save_issue`, before snapshot" position, so memory genuinely **accumulates run-over-run**;
  the PMF consult reads the same collection. Gated by `assert_memory_accumulates.py` (two runs grow
  the count, run 2 recalls run 1, and the recall is **not** re-seeded from `tickets/`); the
  non-gating `diagnose_hermes_mem0_write.py` probes whether the Hermes binary writes mem0 natively.
- **P3** — **Greptile PR review as a standing ticket instruction:** every filed ticket body now ends
  with a standing line — _"After you open a PR for this ticket, run Greptile on it (/greptile) and
  address the findings before requesting merge."_ Fully decoupled (design D-3/D-4): the only in-repo
  deliverable is that line + the gate `assert_greptile_instruction.py` (reads it back from BOTH the
  live Linear ticket and the `tickets/<ID>.md` snapshot). No in-repo Greptile code/MCP/webhook — the
  CLI / `/greptile` command live globally in `~/.claude`, outside this repo.
- **P5** — **Close the PMF North Star loop:** a recorded, **Stripe-grounded** shipped-result flips a
  `pmf_ledger.json` row `shipped: false → true` so "shipped" means a *measured* outcome
  (`pmf_shipped_results.py` — a deterministic, atomic joiner; design D-5 Option C). The flip is
  refused unless the recorded metric value equals a real value in `recordings/stripe_metrics.json`
  (no fabricated outcome), and each flip is recorded into `memories` as its own decision (depends on
  P2). Gated by `assert_shipped_flip.py` (flips a known bet on an isolated temp copy, cross-reads the
  metric against real Stripe data, and proves unrelated rows stay false — the real ledger untouched).

- **Demo (D-2)** — **Fuller multi-component montage + read-only memory view + optional authenticated
  Linear ending.** `build_showcase_video.py`'s catalogue now carries the D-2 segment story (the
  visual hero loop + Stripe/egress/PMF data surfaces + four always-rendered title-carded chapters:
  the **mem0 memory view**, the **Kanban** create→claim→complete lifecycle, the **Greptile** PR-review
  instruction, and the **Linear ticket ending**); `assert_showcase_video.py` raises the manifest
  minima to require those D-2 segments. A new read-only **`render_memory_card.py`** renders the
  `memories` rows + mem0-native entity links to a self-contained `file://` HTML (the marked.js card
  pattern), and **`assert_memory_view_grows.py`** scripts the "visibly more rows after a loop" claim.
  The recorded demo's **default ending stays the reproducible `file://` ticket snapshot** (no auth);
  an **optional** authenticated ending (`TICKET_LIVE_URL=1` + a mounted, gitignored persistent
  Chromium profile — `recorder-profile/`) ends on the **real** logged-in Linear ticket UI. The
  persistent-profile **wiring** is gated by `assert_persistent_profile_wiring.py` (asserts the recorder
  launches Chromium WITH `--user-data-dir`), independent of any real Linear session.

- **P4** — **Host-orchestrator MicroVM confinement spike (scoped, not built — design Q9 Option A).**
  The host Hermes orchestrator runs *outside* any sandbox today (the GLO-13 egress slice only confines
  containerized sub-tools). `scripts/microvm_spike.sh` stands up OpenShell's opt-in `vm` compute driver
  (libkrun + Apple Hypervisor.framework) far enough to record a dated **go/no-go**, capturing the
  evidence to `recordings/microvm_spike_<ts>.log` and the four macOS limitations (Landlock `best_effort`
  no-op on XNU, mDNS `.local` non-traversal, no CUDA, case-sensitive-APFS virtio-fs) into
  `docs/system-design-tradeoffs.md`. It degrades gracefully (always exit 0, no sudo, never disturbs the
  running egress gateway). Gated by `assert_microvm_spike.py` (tolerant: asserts the log + dated go/no-go
  exist, and runs the per-bug probes only when a future spike boots an in-guest workload — each probe
  self-skips otherwise). The spike found the `vm` driver **boots** on this host (it binds
  Hypervisor.framework); the **go/no-go is NO-GO** for a default build this epic — the fragile remainder
  (gateway reconfigure + guest bootstrap + virtio-fs sharing) is deferred. Acceptance #4 = "scoped".

The rest of **GLO-14** rolls forward: a Moderne paid-tier evaluation and the remaining Part C deferrals.

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
- [ ] *(Optional, GLO-14 P3)* **Authenticated Linear demo ending** — the recorded demo ends on the
      reproducible `file://` ticket snapshot by **default** (no setup). To instead end on the **real**
      logged-in Linear ticket UI, populate the gitignored persistent Chromium profile once
      (`chromium --user-data-dir=$PWD/recorder-profile` → log in to Linear), then record with
      `TICKET_LIVE_URL=1`. :warning: **Needs your click** — and the profile holds a live session, so it
      is **never committed** (`recorder-profile/` is gitignored).

## Repository layout

```
.
├── .env.example              # credential template (copy to .env)
├── AGENTS.md / CLAUDE.md     # agent conventions + Standing rules (single source of truth)
├── docker-compose.yml        # mem0-postgres / rag-sidecar / recorder / sonarqube (profiled)
├── README.md                 # this file
├── egress/                    # deny-by-default egress (OpenShell/NemoClaw) — policy.yaml + sandbox Dockerfile
├── scripts/
│   ├── preflight.sh          # halts if required .env keys are missing
│   ├── assert_*.py           # per-slice exit-0-on-pass gates (egress / stripe / sonar / pmf / showcase / …)
│   ├── stripe_client.py / stripe_seed.py        # real Stripe test-mode metrics
│   ├── sonarqube_client.py / fuse_signals.py    # SonarQube DETECT + graphify fusion
│   ├── build_showcase_video.py / render_*.py    # hybrid-montage showcase video + title/ticket/memory cards
│   ├── render_memory_card.py                     # read-only mem0 `memories` view (file:// HTML, marked.js)
│   ├── assert_memory_view_grows.py / assert_persistent_profile_wiring.py  # GLO-14 P3 demo gates
│   ├── microvm_spike.sh / assert_microvm_spike.py  # GLO-14 P4 host-MicroVM confinement spike + tolerant gate
│   └── file_fullbuild_ticket.py / snapshot_tickets.py  # author + snapshot the full-build epic
├── docs/
│   ├── setup-guide.md         # repeatable setup (full clean-clone walkthrough)
│   ├── system-design-tradeoffs.md  # textbook-cited decision record (Q1–Q8b + per-phase findings + deferred work)
│   └── cto-functions.md       # "teach me to think like a CTO" — functions + grounding texts
├── tickets/                   # git-tracked snapshots of every filed Linear ticket
├── graphify-out/              # service-coupling graph + fused static_analysis (gitignored)
└── corpus/                   # converted textbooks (gitignored — stays local)
```

> **Documentation policy:** git history is the authoritative decision record; mem0 is a
> complement, not a dependency. `docs/system-design-tradeoffs.md` cites the named textbooks
> behind every locked decision, and every Linear ticket the agents file is snapshotted into the
> tracked `tickets/<ID>.md` (`scripts/snapshot_tickets.py` / `scripts/snapshot_after_run.sh`) so
> the decision record lives in git. `docs/cto-functions.md` maps each CTO function to the corpus
> texts that ground it.
