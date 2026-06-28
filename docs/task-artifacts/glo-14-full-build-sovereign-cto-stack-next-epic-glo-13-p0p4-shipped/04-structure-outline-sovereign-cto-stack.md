---
task: glo-14-full-build-sovereign-cto-stack-next-epic-glo-13-p0p4-shipped
type: structure-outline
repo: GS_AISafetyHackathon
branch: main
sha: 1697a21e9bdfd8b224f834ad6ce8a53f19a1ff96
---

# GLO-14 — Sovereign CTO Stack: close the memory/review/feedback loops + harden + author next epic

The next full-build epic for the Sovereign CTO Stack. GLO-13 shipped the phased build plus the
P0–P4 backlog as thin, gated slices; GLO-14 makes the system actually *learn and review* — close
mem0's write path so `memories` accumulates run-over-run (P1), have every ticket prompt a Greptile
PR review (P2), flip the PMF North Star from real outcomes (P5), tell a fuller authenticated demo
(P3), spike host-orchestrator MicroVM confinement (P4), then capture Part C deferrals and author
the next epic (Part C/D). Each phase ships an `assert_*.py` exit-0 gate, the codebase's falsifiable
per-slice contract.

> **Where this is implemented.** The GLO-13 P0–P4 work lives only on the worktree branch
> `glo-13-...` under `sovereignCTO/` (`main`'s `sovereignCTO/` is an earlier snapshot — research §1).
> All paths below are **relative to `sovereignCTO/`**. The `/rpi:setup-worktree` step will create the
> implementation worktree from the branch that carries the P0–P4 build.

## Desired End State

- **A system that learns (mem0 as designed).** After N runs, a fresh `mem0.search()` against the
  `memories` collection returns prior-run decisions that were *never* seeded from `tickets/` — using
  mem0 OSS ≥ v2.0.0 `infer=True` extraction + native entity-linking (no Neo4j). Git stays the
  authoritative record; mem0 is the recall complement. (Acceptance #1.)
- **Agents that ship *and* review.** Every ticket Hermes files carries a standing instruction to run
  Greptile on the resulting PR. No in-repo Greptile code beyond that line + its gate; the CLI/skill
  live globally in `~/.claude`, outside this repo.
- **A closed North Star loop.** A recorded shipped-bet result, grounded in real Stripe data, flips a
  `pmf_ledger.json` row `shipped:false → true`.
- **A fuller, more convincing demo.** The montage surfaces more components and *can* end on the real
  authenticated Linear ticket UI (persistent Chromium profile), with the `file://` snapshot retained
  as the reproducible default; a read-only memory view shows the collection growing.
- **Stronger confinement, honestly scoped.** Host-orchestrator MicroVM confinement spiked and the
  macOS-bug tradeoffs + go/no-go recorded in `docs/system-design-tradeoffs.md`. (Acceptance #4.)
- **Closeout.** Moderne/OpenRewrite + the other deferrals captured in Part C with scope+rationale;
  the next full-build epic authored and snapshotted to `tickets/`. (Acceptance #5, #6.)

## Implementation Overview

- [x] Phase 1: mem0 OSS ≥ v2.0.0 upgrade, gated by the extended round-trip smoke
- [x] Phase 2: Close the mem0 write path — `memories` accumulates every run (P1)
- [x] Phase 3: Greptile ticket-instruction line + gate (P2)
- [x] Phase 4: PMF shipped-bet feedback flip, Stripe-grounded (P5)
- [x] Phase 5: Fuller multi-component demo + authenticated Linear ending + memory view (P3 / D-2)
- [x] Phase 6: Host-orchestrator MicroVM confinement spike + tradeoffs doc (P4)
- [ ] Phase 7: Closeout — Part C deferral capture + author the next full-build epic (Part C / D)

---

## ✅ Phase 1: mem0 OSS ≥ v2.0.0 upgrade, gated by the extended round-trip smoke

Foundation slice that de-risks the version bump *before* anything is built on it. Pin mem0 to a
tested OSS ≥ v2.0.0, rely on native entity-linking (no external graph store — none is configured, so
removed `graph_store` keys are simply ignored), and extend the existing CI smoke to assert the new
`add()`/`search()` return shape. Vertical because it touches the dependency pins, the runtime config,
the gate, and the docs (D-1).

### File Changes

- **`scripts/mem0_roundtrip.py`**: bump the PEP 723 inline dependency `mem0ai` (unpinned today,
  lines 4–10) to a pinned `mem0ai>=2.0.0` tested version; extend the smoke beyond the `infer=False`
  persistence proof to assert the v2.0.0 return-shape contract and, when Ollama is reachable,
  exercise `infer=True` + native entity-linking on two related facts.

```python
# /// script  -> dependencies: ["mem0ai>=2.0.0", "sentence-transformers", "vecs", "psycopg2-binary", "ollama"]
def _assert_v2_shape(add_res, search_res) -> None: ...   # results[], ids, entity links present
```

- **`scripts/mem0_pmf_decisions.py`**: bump the same inline `mem0ai` pin (behaviour unchanged here;
  the collection repoint happens in Phase 2).
- **`hermes/mem0.json`**: confirm the OSS config (`mode:"oss"`, pgvector, MiniLM, Ollama) loads
  unchanged under v2.0.0; no `graph_store` key exists to remove.
- **`docs/setup-guide.md`** / **`docs/system-design-tradeoffs.md`**: record the pinned version and
  that native entity-linking replaces external graph DBs (no Neo4j), with the low-risk rationale.

### Validation

#### Automated Verification

- [x] `docker compose up -d mem0-postgres` then `uv run scripts/mem0_roundtrip.py` exits 0 on the
      pinned ≥ v2.0.0 (persistence + new return-shape assertions pass). _Verified: resolved
      `mem0ai==2.0.10`; `[shape] PASS` + persistence round-trip, exit 0._
- [x] The round-trip's `infer=True` + native-entity-linking assertion passes when Ollama is
      reachable, and prints a logged `SKIP` (still exit 0) when it is not — so CI never depends on a
      local LLM, but a dev box with Ollama proves the entity link automatically. _Verified both
      paths: Ollama up → `[link] PASS` (2 facts extracted, entity observable in recall); Ollama
      unreachable (`OLLAMA_BASE_URL=http://localhost:1`) → `[link] SKIP`, exit 0._
- [x] `docker compose config -q` still parses; `gitleaks`/preflight unaffected. _Verified:
      `compose config -q` OK; `gitleaks detect` → no leaks found; `.githooks/pre-commit` intact._

#### Manual Verification

_None — fully automated (the entity-link proof is asserted inside the round-trip, self-skipping when
Ollama is absent)._

---

## ✅ Phase 2: Close the mem0 write path — `memories` accumulates every run (P1)

The load-bearing slice. Insert a deterministic "record this decision" write at the single canonical
position research pins in **both** loops — after `save_issue` returns a ticket ID and before
`snapshot_after_run.sh` — writing the just-filed decision into the unified `memories` collection via
mem0's intended `infer=True` path, and repoint the PMF consult's *read* to the same collection so
recall is real (Q2). Gated by a count-delta accumulation assertion tolerant of `infer=True` phrasing
(Q5). Vertical: new helper + both loop scripts + the consult read path + a new gate + docs.

### File Changes

- **`scripts/mem0_record_decision.py`** (NEW): reusable CLI helper; connection/config mirrors
  `mem0_pmf_decisions.py:58-94` but `collection_name="memories"`, `user_id="sovereign-cto"`. Writes
  the full agent turn with `infer=True` so mem0 extracts/dedups/entity-links (Q3 deterministic
  writer is load-bearing; Q4 `infer=True`).

```python
def record_decision(*, profile, run_id, ticket_id, kind,
                    grounding_question, grounded_summary, grounded_in: list[str]) -> dict:
    # mem.add([{role:user, content:grounding_question},
    #          {role:assistant, content:f"{ticket_title}\n{grounded_summary}"}],
    #         user_id="sovereign-cto", agent_id=profile, run_id=run_id, infer=True,
    #         metadata={decision_id:ticket_id, kind, ticket_id, grounded_in, source:"agent_run", ts})
    ...
```

- **`scripts/record_run.sh`**: in the hero loop, invoke `mem0_record_decision.py` between the
  ticket-filing return and `snapshot_after_run.sh` (research pins `record_run.sh:401`).
- **`scripts/pmf_kanban_run.sh`**: same insertion in the PMF loop (research pins line ~368), after
  the ledger/Kanban-complete write and before snapshot.
- **`scripts/mem0_pmf_decisions.py`**: repoint the read `collection_name`/filters from
  `pmf_decisions` → `memories` (Q2 unify) so the consult reads what the new writer writes.
- **`scripts/assert_memory_accumulates.py`** (NEW): runs the loop **twice**, asserting after each
  that the `source:"agent_run"` row count in `memories` grew, that a `search(this_run_topic)` returns
  a hit carrying this run's `metadata.decision_id`, and — proving accumulation rather than re-seeding
  — that run 2's `search()` *also* surfaces run 1's decision **and** that the recalled decision text
  is **not a substring of any `tickets/*.md`** (the cross-check is scripted, not eyeballed).
- **`scripts/diagnose_hermes_mem0_write.py`** (NEW, non-gating diagnostic): runs one loop with the
  deterministic helper disabled and reports whether any new `memories` rows appear (i.e. whether the
  closed-source `hermes-agent` binary writes via `mem0.json` on its own — Q3 bonus). Prints a
  machine-readable verdict; the deterministic helper stays load-bearing regardless of the result.
- **`docs/system-design-tradeoffs.md`**: note the write path is closed; paste the
  `diagnose_hermes_mem0_write.py` verdict as the recorded Q3 finding.

### Validation

#### Automated Verification

- [x] `uv run scripts/assert_memory_accumulates.py` exits 0 — two runs both grow the count, run 2
      recalls run 1's decision, and the recalled text is absent from every `tickets/*.md` (the
      "accumulated, not seeded" proof, fully scripted). _Verified: run 1 grew 0→2, run 2 grew 2→4,
      both decision ids recalled, no ticket-substring leak, `infer=True` + spaCy lemma loaded, exit 0._
- [x] `uv run scripts/assert_pmf_ranked.py` still exits 0 — `prior_decisions_consulted.mem0_hits`
      stays populated after the read is repointed to `memories`. _Verified: NO_AGENT PMF loop wrote
      the ledger; gate PASS with `mem0_hits=4` read from the unified `memories` collection (seeded
      GLO-12 + the loop's own `agent_run` writes)._
- [x] `uv run scripts/diagnose_hermes_mem0_write.py` runs clean and emits its Q3 verdict (diagnostic,
      not a pass/fail gate). _Verified: emits one-line JSON, exit 0; verdict `INCONCLUSIVE` in this
      worktree (self-skips — no `graphify-out/` to drive a real hero loop); pasted in the tradeoffs doc._

#### Manual Verification

_None — the two-run accumulation, the cross-check against `tickets/`, and the Q3 Hermes-native probe
are all scripted._

---

## ✅ Phase 3: Greptile ticket-instruction line + gate (P2)

Fully decoupled per D-3/D-4: the *only* in-repo deliverable is a standing instruction that Hermes'
filing skills append to every ticket body, plus a gate that reads it back. The Greptile CLI + Claude
Code skill + `/greptile` command are set up globally in `~/.claude` **outside this repo** (a
separate, project-agnostic task — not tracked here). Thin but vertical: skill text + epic filer +
gate + a tradeoffs note naming the out-of-repo dependency.

### File Changes

- **`hermes/skills/file_brownfield_ticket.md`**: append the standing line to the composed ticket
  body (mirror the existing body-composition at `:46-118`).

```text
After you open a PR for this ticket, run Greptile on it (/greptile) and
address the findings before requesting merge.
```

- **`hermes/skills/pmf_brief.md`** (and `pmf_rank.md` if it files): append the same line so PMF/
  `[Product]` tickets carry it too.
- **`scripts/file_fullbuild_ticket.py`**: include the line in the epic body for consistency.
- **`scripts/assert_greptile_instruction.py`** (NEW): read back the newest filed ticket via the
  Linear MCP (mirror `assert_brownfield_ticket.py`) **and** the `tickets/GLO-NN.md` snapshot; assert
  both contain the instruction line.
- **`docs/system-design-tradeoffs.md`**: document the decoupling — the global Greptile setup is an
  out-of-repo prerequisite, not a GLO-14 repo deliverable; the GitHub App is the no-code fallback.

### Validation

#### Automated Verification

- [x] `uv run scripts/assert_greptile_instruction.py` exits 0 (newest ticket body + snapshot both
      carry the instruction line). _Verified: default path PASS on the newest filed ticket GLO-18
      (live Linear body + `tickets/GLO-18.md` snapshot both carry the line), exit 0; also PASS on
      the `[Full-Build]` GLO-14 (filed in place via `file_fullbuild_ticket.py --next-epic`)._
- [x] `uv run scripts/assert_brownfield_ticket.py` and `assert_product_ticket.py` still exit 0
      (grounding/label invariants intact after the body change). _Verified: brownfield gate PASS
      (8 distinct grounding sources, `src/<service>/` files, Brownfield label intact); product gate
      PASS (Product label, capability gap, market URL, 4 grounding citations). The appended line is
      purely additive._

#### Manual Verification

- [ ] Human judgment only: confirm the final instruction **wording reads naturally** to a human
      executor (the gate already proves the line is present in both the live ticket and the snapshot).

---

## ✅ Phase 4: PMF shipped-bet feedback flip, Stripe-grounded (P5)

Close the North Star loop the GLO-13 P4 slice scaffolded: today every `pmf_ledger.json` opportunity
is permanently `shipped:false`. Wire a small shipped-result record (bet id + measured metric) that a
deterministic joiner uses to flip the matching row `false → true`, grounded in real Stripe data so
"shipped" means a *measured* outcome (D-5 Option C). Sequenced after P1 (the flip is itself a
decision recorded to `memories`). Additive/atomic writes (the `fuse_signals.py` pattern).

### File Changes

- **`scripts/pmf_shipped_results.py`** (NEW): reads/writes `recordings/shipped_results.json`
  (bet id + measured metric + Stripe grounding ref) and a deterministic joiner that flips matching
  `pmf_ledger.json[].shipped` and stamps `grounded_in` with `stripe_metrics.json`. Atomic
  `os.replace`, never clobbering other ledger keys.

```python
def flip_shipped(ledger_path, results_path, stripe_metrics_path) -> int:  # returns rows flipped
    ...   # join on bet id; set shipped=true + grounded_in += ["stripe_metrics.json"]; atomic write
```

- **`scripts/pmf_kanban_run.sh`**: after the ledger write (`:154-224`), invoke the joiner so a
  recorded shipped-result flips its row in the same run; record the flip decision via Phase-2
  `mem0_record_decision.py`.
- **`scripts/stripe_client.py`**: reuse existing `recordings/stripe_metrics.json`; add a small
  read helper if a per-bet metric delta is needed (no new Stripe surface).
- **`scripts/assert_shipped_flip.py`** (NEW): seed a `shipped_results.json` for a known bet, run the
  joiner, assert that bet's `shipped` is now `true`, its `grounded_in` cites `stripe_metrics.json`,
  and — proving "measured real outcome" — that the recorded metric value **equals a value actually
  present in `stripe_metrics.json`** (MRR/churn cross-read, scripted), while unrelated rows stay
  `false`.

### Validation

#### Automated Verification

- [x] `uv run scripts/assert_shipped_flip.py` exits 0 (target bet flips true; grounded metric equals
      a real `stripe_metrics.json` value; others untouched). _Verified: exit 0 — rank-1 bet flips
      `false→true` on an isolated temp ledger copy; recorded `mrr=1281.0` cross-reads to the real
      `stripe_metrics.json` value; the 2 unrelated rows stay `false`; all other ledger keys preserved
      byte-for-byte; the real `recordings/pmf_ledger.json` is untouched. The no-fabrication contract
      also verified: `record --value 99999.99` is REFUSED, a real value accepted._
- [x] `uv run scripts/assert_pmf_ranked.py` still exits 0 (ledger schema + ranking invariants hold).
      _Verified: exit 0 — `shipped`/`shipped_result` are additive; 3 RICE-ranked, grounded
      opportunities + a non-empty "Prior decisions consulted" section all still pass._

#### Manual Verification

_None — the flip, the Stripe grounding, and the "metric matches real Stripe data" trace are all
asserted by the gate._

---

## ✅ Phase 5: Fuller multi-component demo + authenticated Linear ending + memory view (P3 / D-2)

Make the recording show more of the stack and *be able* to end on the real authenticated Linear
ticket UI, while keeping the `file://` snapshot as the reproducible default. Adds a cheap read-only
memory view (reusing the marked.js card pattern) that visually proves `memories` grew (depends on
P1), and extends the montage catalogue to the D-2 segment list (Telegram → coupling graph →
SonarQube → Kanban → Stripe → RICE ledger incl. the P5 flip → egress 403 → Greptile output card →
authenticated Linear ending). Vertical: renderer + recorder + compose mount + montage + gate.

### File Changes

- **`scripts/render_memory_card.py`** (NEW): query `memories` rows + entity links and render
  before/after HTML to `recordings/memory_<ts>.html` (reuse `render_ticket_card.py:51-107` marked.js
  template/screenshot pattern).
- **`recorder/entrypoint.sh`**: support a mounted `--user-data-dir` (persistent, authenticated
  Chromium profile) in `launch_browser`; add a `surface-html` path for the memory card.
- **`scripts/record_run.sh`**: wire the persistent-profile path through the guarded
  `TICKET_LIVE_URL=1` block (`:349-381`) so the live authenticated Linear ticket renders when the
  profile is present; default stays the `file://` snapshot.
- **`docker-compose.yml`**: add a gitignored bind-mount for the recorder user-data-dir.
- **`.gitignore`**: ignore the mounted profile directory (no session secrets committed).
- **`scripts/build_showcase_video.py`**: extend `catalogue()` (`:126-201`) with the new D-2 segments
  (memory view, Stripe MRR, Kanban transitions, egress 403, Greptile output title card, authenticated
  Linear ending); lower-signal components become title-carded segments.
- **`scripts/assert_showcase_video.py`**: raise the manifest segment minima to require the new
  segments.
- **`scripts/assert_memory_view_grows.py`** (NEW): render the memory card before and after a loop and
  assert the parsed row count strictly grew (scripts the "visibly shows more rows" check).

### Validation

#### Automated Verification

- [x] `uv run scripts/verify_recording.py` passes on a fresh **default** run (no profile): valid mp4,
      non-blank, non-static, and the `file://` snapshot ending renders — proving the default path.
      _Verified: a fresh default `NO_AGENT=1 RECORD_SECONDS=12` hero capture against the REBUILT
      recorder (no `CHROMIUM_USER_DATA_DIR`, no `TICKET_LIVE_URL`) → `verify_recording.py` RESULT:
      PASS (valid mp4/h264, dur>0, moov, non-blank YMAX-YMIN=217, non-static delta=1.14). The default
      `file://` snapshot ending is untouched by this phase (only a NEW `TICKET_LIVE_URL=1`-guarded
      block was added); `render_ticket_card.py` still renders the snapshot HTML (7807 bytes)._
- [x] `uv run scripts/assert_showcase_video.py` exits 0 with the expanded segment minima. _Verified:
      built an 8-segment montage (hero + egress/stripe/pmf data surfaces + the 4 D-2 title segments);
      gate PASS — valid non-static concat (161.8s), ≥1 hero, ≥5 segments (8), and all required D-2
      segments present (memory-view, kanban-transitions, greptile-review, linear-ending)._
- [x] `uv run scripts/render_memory_card.py` writes a non-empty `recordings/memory_*.html`, and
      `uv run scripts/assert_memory_view_grows.py` exits 0 (after-run row count > before-run).
      _Verified: `render_memory_card.py` wrote a 3213-byte card off the LIVE `memories` collection
      (4 rows, rendered table + entity links). `assert_memory_view_grows.py` RESULT: PASS — isolated
      collection grew 0→1 over the real `mem0_record_decision` write path (full `infer=True` + spaCy
      lemma loaded), and the after-card highlighted 1 NEW row._
- [x] Persistent-profile code-path smoke: with `TICKET_LIVE_URL=1` and a throwaway user-data-dir, a
      gate asserts the recorder launched Chromium **with `--user-data-dir`** (the wiring is exercised,
      independent of whether a real Linear session is present). _Verified via NEW
      `scripts/assert_persistent_profile_wiring.py`: drove the real `launch_browser` path inside the
      rebuilt recorder with a throwaway `CHROMIUM_USER_DATA_DIR` + a harmless local file:// target →
      RESULT: PASS (Chromium launched WITH `--user-data-dir=<throwaway>`, the entrypoint logged the
      persistent-profile path, and Chromium populated the dir); the throwaway profile was cleaned up._

#### Manual Verification

- [x] Truly human (live authenticated session): with a real logged-in profile mounted, eyeball that
      the recording ends on the **actual** Linear ticket page (not the auth wall). _Verified: the
      human logged into Linear via a one-time VNC `login` verb (x11vnc bridge added to the recorder);
      the session persisted to the gitignored `recorder-profile/`. The `auth_ending_*.mp4` clip and
      the final montage (`showcase_20260628_171700.mp4`, 3:07) both render the REAL authenticated
      GLO-19 ticket UI (confirmed by eye), not the auth wall._
- [x] Collaborative decision: pick the final montage segment ordering together (D-2 micro-detail).
      _Settled: hero → PMF → egress-403 → Stripe MRR → RICE ledger → memory view → Kanban → Greptile
      → authenticated Linear ending; recording-backed segments fall back to title cards when a clip
      is absent (user-blessed)._

---

## ✅ Phase 6: Host-orchestrator MicroVM confinement spike + tradeoffs doc (P4)

The host Hermes orchestrator runs *outside* any sandbox today; the egress slice only confines
containerized sub-tools. Spike OpenShell's `vm` driver (libkrun + Apple Hypervisor.framework) far
enough to hit/clear the known macOS bugs and record a go/no-go — satisfying acceptance #4
("scoped or built") without committing to a fragile default build (Q9 Option A). Sequenced late:
highest moving-parts/DNS risk, after the load-bearing layers ship.

### File Changes

- **`scripts/microvm_spike.sh`** (NEW): stand up the OpenShell `vm` driver
  (`OPENSHELL_DRIVERS=vm` / gateway TOML), attempt to run the host orchestrator (or a stand-in)
  inside a MicroVM, and capture `openshell status` + driver output to
  `recordings/microvm_spike_<ts>.log`. Inference stays cloud (no CUDA on Apple Silicon).
- **`docs/system-design-tradeoffs.md`**: record the spike outcome, the four macOS limitations
  (Landlock `best_effort` no-op on XNU, mDNS `.local` non-traversal, no CUDA, case-sensitive-APFS
  virtio-fs), and the go/no-go decision.
- **`scripts/assert_microvm_spike.py`** (NEW, tolerant): assert the spike log exists and the
  tradeoffs doc carries a dated go/no-go section (criterion #4 = scoped or built). **When the VM
  reaches boot**, also run deterministic per-bug probes and assert each behaves as documented —
  `.local` mDNS CONNECT fails (non-traversal), Landlock reports `best_effort`/no-op on the guest,
  and a virtio-fs case-sensitivity check resolves as recorded; each probe self-skips (logged
  `SKIP`, still exit 0) if the VM did not get far enough, so the gate degrades gracefully.

### Validation

#### Automated Verification

- [x] `uv run scripts/assert_microvm_spike.py` exits 0: spike log present, tradeoffs go/no-go section
      recorded, and every reached macOS-bug probe matched its documented behaviour (unreached probes
      log `SKIP`). _Verified: `bash scripts/microvm_spike.sh` ran on this Apple-Silicon host and exits 0
      — the opt-in `vm` driver (`openshell-driver-vm`, OpenShell 0.0.71) is installed, carries the
      `com.apple.security.hypervisor` entitlement, and **boots** (binds its gRPC socket → libkrun got
      Hypervisor.framework): `VM_DRIVER_PRESENT=yes VM_DRIVER_BOOTED=yes` in
      `recordings/microvm_spike_<ts>.log`. The spike is non-destructive (standalone driver to a private
      socket, then torn down — the running egress gateway stays Connected). The gate then PASS'd: log
      present + a DATED (2026-06-28) go/no-go section in `docs/system-design-tradeoffs.md` naming all
      four macOS limitations; the three per-bug probes (`.local` mDNS, Landlock `best_effort`,
      virtio-fs case) self-`SKIP` (still exit 0) because Q9 deliberately stops at the driver-binds
      layer (no in-guest workload). Also verified the spike exits 0 with `openshell` absent from PATH
      (graceful degradation)._
- [x] `uv run scripts/check_doc_links.py` passes (new tradeoffs links resolve). _Verified: PASS, exit
      0 (4 markdown files checked, all internal links resolve) after adding the GLO-14 P4 sections to
      `README.md`, `docs/setup-guide.md`, and `docs/system-design-tradeoffs.md`. gitleaks: no leaks
      found (Rule 8)._

#### Manual Verification

- [x] Truly human (exploratory spike): make the **go/no-go call** from how far the VM actually got,
      and decide whether it reached a demoable state for the optional P3 segment #20. _Decided
      (2026-06-28): the `vm` driver boots to the driver-binds layer but the fragile remainder is
      deferred → **NO-GO** (scope only, defer the build to a future hardening epic). Optional montage
      segment #20 **declined** (the montage tells the story without it). Recorded in tradeoffs._

---

## Phase 7: Closeout — Part C deferral capture + author the next full-build epic (Part C / D)

Capture the rolled-forward deferrals with scope+rationale, keep remediation routing "named-only"
(Codegen) with Moderne staged as a deferred config stub (Q11), then author the *next* full-build
epic — rolling forward the remainder and anything discovered this cycle — and snapshot it to
`tickets/` (AGENTS.md rule 7; D-6 closeout boundary). Self-perpetuating roadmap; git stays the
authoritative record.

### File Changes

- **`docs/system-design-tradeoffs.md`**: Part C section — Moderne/OpenRewrite (no account; OSS-pilot
  preserved as an option), mem0 OSS server + Next.js dashboard, OpenHands via Portal/LiteLLM, the
  second-account walkthrough — each with scope + rationale (acceptance #5).
- **`hermes/config.yaml`**: keep Codegen registered "named-only"; add a **commented** Moderne local
  `mcp_servers` stub documenting `mod config agent-tools install` (deferred, not registered — Q11).
- **`scripts/file_fullbuild_ticket.py`**: author the next full-build epic (GLO-NN+1) body, rolling
  forward Moderne + remaining deferrals + items discovered while building P1–P5; file via Linear MCP.
- **`tickets/GLO-NN.md`** (NEW snapshot): snapshot the newly-authored epic on filing.
- **`scripts/assert_fullbuild_ticket.py`**: extend to assert the next epic mentions the rolled-
  forward items (Moderne, mem0 dashboard, OpenHands) and was snapshotted to `tickets/`.
- **`scripts/assert_closeout_ready.py`** (NEW): the D-6 boundary gate — runs every prior-phase gate
  (`assert_memory_accumulates`, `assert_greptile_instruction`, `assert_shipped_flip`,
  `assert_showcase_video`, `assert_microvm_spike`) and requires all exit 0, and asserts the GLO-14
  acceptance checklist in `tickets/GLO-14.md` is fully ticked — so "substantially actioned" is
  measured, not asserted by feel, *before* the next epic is authored.
- **`tickets/GLO-14.md`**: tick the GLO-14 acceptance checklist as criteria are met.

### Validation

#### Automated Verification

- [x] `uv run scripts/assert_closeout_ready.py` exits 0 — all prior-phase gates pass and the GLO-14
      checklist is complete (the closeout boundary, scripted). _Verified: exit 0 — the five prior
      gates (`assert_memory_accumulates`, `assert_greptile_instruction`, `assert_shipped_flip`,
      `assert_showcase_video`, `assert_microvm_spike`) each exit 0 (run via `uv run`, services up),
      and all 6 GLO-14 acceptance items in `tickets/GLO-14.md` are ticked. SKIP→FAIL under
      `CLOSEOUT_STRICT=1`; default tolerates a down service gracefully._
- [x] `uv run scripts/assert_fullbuild_ticket.py` exits 0 (next epic body carries rolled-forward
      items + a `tickets/` snapshot exists). _Verified: `--next-epic` PASS on the newly-filed
      **GLO-20** — body rolls forward Moderne/OpenRewrite, the mem0 OSS server + Next.js dashboard,
      OpenHands via Portal/LiteLLM; captures the Greptile global prerequisite, the live-profile
      skill-deploy step, and the duplicate-finding dedupe; `[Full-Build]` label + `tickets/GLO-20.md`
      snapshot present. (Default `assert_fullbuild_ticket.py` GLO-13 structural checks unaffected.)_
- [x] `uv run scripts/check_doc_links.py` passes; `docker compose config -q` parses the Moderne
      stub comment cleanly. _Verified: doc-link check PASS (4 markdown files, all internal links
      resolve) after the Part C closeout section + README/setup-guide updates; `docker compose
      config -q` exit 0 (the commented `moderne` `mcp_servers` stub in `hermes/config.yaml` is a YAML
      comment; `docker-compose.yml` is untouched). gitleaks: no leaks found (Rule 8)._

#### Manual Verification

- [ ] Human judgment only: the next full-build epic **reads coherently** as a roadmap (editorial
      quality). The closeout boundary itself is now gated by `assert_closeout_ready.py` above.

---

## Open Questions

These are build-time micro-details (all *design* questions are resolved in `03-design-discussion`):

- **Greptile instruction wording (D-4):** confirm the exact standing line (proposed in Phase 3) —
  human copy judgment.
- **Final montage segment ordering (D-2):** collaborative call during Phase 5.
- **MicroVM go/no-go (P4):** the human judgment call on the Phase 6 spike result (the bug-by-bug
  behaviour is now auto-probed; demoability for segment #20 follows from that call).

(Q3 — whether `hermes-agent` writes `memories` on its own — is now answered by the automated
`diagnose_hermes_mem0_write.py` diagnostic in Phase 2, not left as an open question.)
