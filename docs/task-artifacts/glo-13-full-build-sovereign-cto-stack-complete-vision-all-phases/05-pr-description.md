[GLO-13](https://linear.app/global-south-ai-safety/issue/GLO-13/full-build-sovereign-cto-stack-complete-vision-all-phases-prioritized) | [Artifacts](https://cloud.humanlayer.com/tasks/019f0a4f-ce31-7c1c-aabc-50b633b07331/artifacts) | [Task deep link](https://cloud.humanlayer.com/deep/tasks/019f0a4f-ce31-7c1c-aabc-50b633b07331) | [PR Walkthrough (alpha)](https://cloud.humanlayer.com/artifacts/019f0ba8-92f8-7abb-b95c-ea0ca3fa9a1a)

## What problems was I solving

Phases 0–5 of the Sovereign CTO Stack were already built and verified, but they left five
competition-relevant claims **asserted in docs rather than enforced and gated**. This PR executes the
GLO-13 deferred backlog (Part B, P0→P4) plus a closeout, building each as a thin, independently
verifiable vertical cut that ships its own `scripts/assert_*.py` gate in the repo's established
exit-0-on-pass pattern. After this PR:

- The recorded demo streams **real `query_cto_knowledge` / `save_issue` tool calls** drained from the
  Hermes session store — not a scripted ticker.
- Egress is **deny-by-default and proven by a negative test**: a non-allow-listed CONNECT is *refused*
  by a real NVIDIA OpenShell sandbox, with a reviewable `egress/policy.yaml` allow-list.
- The PMF brief grounds its AARRR **Revenue/Retention in real Stripe test-mode data** (MRR $1,281/mo,
  25% lifetime churn, 3 monthly cohorts) instead of competitor-pricing assumptions.
- The tech-debt loop **fuses SonarQube (240 real issues) with graphify coupling**, with Hermes as the
  judgment layer that prioritizes billing-path code and routes to a remediation back-end (Codegen).
- The PMF loop **RICE-ranks multiple opportunities** and **consults prior decisions** (mem0 + git) so it
  won't re-propose an already-decided bet.
- A multi-segment **showcase montage** closes the epic and **authors the next one (GLO-14)** — the
  self-perpetuating backlog where git history is the authoritative roadmap.

Success is measured qualitatively (the demo shows enforced safety, not claimed safety) and
quantitatively (14 `assert_*.py` gates exit 0 against real backends; gitleaks clean over 17 commits).

## What user-facing changes did I ship

- [scripts/record_run.sh](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-af4b9de42497d4775ccbbf9d5ffe0af92657dc6b05f2c54cfa54dfb9fa4bee0b) — P0: replace the scripted ticker with a drain of real tool calls into the recorded pane
- [egress/policy.yaml](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-34e760b2274254ec4efd117382818024d928872c8b1300d522c34322c73e9c0e) — P1: the auditable deny-by-default egress allow-list (OpenShell sandbox)
- [scripts/stripe_client.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-c0755eb5c4673b3728760bd42ad9ffbc5af2f387eaad9173e8a505fa5369ce44) — P2: fail-loud test-mode Stripe reader writing `recordings/stripe_metrics.json`
- [scripts/fuse_signals.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-29d88e63466f78754247cd5fa6eb283ac10b0476251a7ecf1db1f5b005ce945a) — P3: fuse SonarQube issues onto graphify coupling as an additive `static_analysis` block
- [scripts/mem0_pmf_decisions.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-7c0c3e620f29a6ecfdc6048415af2b8df3e507f3f6f26868439bab5a86d2202a) — P4: consult prior decisions (mem0 + git) before ranking
- [scripts/build_showcase_video.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-61ee434e564752c672ccd8a3cdbc9b3a91f554b9defdb8a65f622e480a9c3608) — Closeout: ffmpeg-concat the passing segments into one montage
- [scripts/file_fullbuild_ticket.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-34d942a5b2ebdca55571910f8ffe48bed4194e26289dd78141958375d58aa0b6) — Closeout: check off GLO-13 P0→P4 and author the next epic GLO-14

## How I implemented it

Six slices, built greedily in priority order. The [PR Walkthrough](https://cloud.humanlayer.com/artifacts/019f0ba8-92f8-7abb-b95c-ea0ca3fa9a1a) narrates each one with inline diffs.

### P0 — real tool-call events in the recorded demo
- [scripts/record_run.sh](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-af4b9de42497d4775ccbbf9d5ffe0af92657dc6b05f2c54cfa54dfb9fa4bee0b) — deleted `start_ticker`/`stop_ticker`; Hermes' `-z` path buffers output and doesn't stream per-tool-call lines, so the authoritative record is the per-profile session store (`~/.hermes/profiles/<p>/state.db`, `messages` table). A 2s heartbeat keeps the surface provably non-static during the run, then the store is drained into `$AGENT_LOG` as `[live] tool <name> completed` lines.
- [recorder/entrypoint.sh](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-d7c4e1098799e5721f597dab1bbbbcf90150f663ef21e63240170095d0371181) — added `rexec navigate`/`surface-html` verbs to drive the right-pane Chromium.
- [scripts/assert_demo_authenticity.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-59f238f28045e20cfe704238c01e39fca45dc36de2f88c2db87f12ebb384e1fd) — gate: ≥1 real tool-call line, distinguishing it from the old ticker string.

### P1 — deny-by-default egress hardening
- [egress/policy.yaml](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-34e760b2274254ec4efd117382818024d928872c8b1300d522c34322c73e9c0e) + [egress/Dockerfile](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-c3bc840a925626636727f28998514f1c3532345f350e7f22171989d949c592e5) — a real OpenShell 0.0.71 sandbox confines the workload; the OPA CONNECT proxy tunnels allow-listed hosts (200) and refuses everything else (403 / curl exit 56). Independent of the Landlock filesystem layer.
- [scripts/assert_egress_policy.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-7239cb911f3de593815b99ccc781a58883d778bc7c1d0603233630f96be06d6e) — the load-bearing **negative** test (`example.com:443` refused) + a positive check (`api.linear.app:443` succeeds). Exits 2 if OpenShell/Docker is absent.
- [docker-compose.yml](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-e45e45baeda1c1e73482975a664062aa56f20c03dd9d64a827aba57775bed0d3) — removed the fictional `egress-proxy` sidecar; enforcement is out-of-process.

### P2 — Stripe-grounded AARRR
- [scripts/stripe_client.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-c0755eb5c4673b3728760bd42ad9ffbc5af2f387eaad9173e8a505fa5369ce44) + [scripts/stripe_seed.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-8cca352900f01c09a439d106123c52dff5b83417ff4a8fab4624ae1af443c13f) — stdlib REST client; refuses `sk_live_`/`rk_live_` keys; raises on non-2xx. Idempotent seeder (`seed:sovereign-cto-stack` tag) populates 12 subs / 3 canceled / 3 cohorts.
- [hermes/skills/pmf_brief.md](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-0142da3e285a05df3f59d68bd278e89e7ace02c8718ff9176b213c548d0bc42c) + [scripts/assert_stripe_grounding.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-b42facfc9ecd964af335116741736e21e76fcfee6d991cad2c73ec3c0a9b7b36) — the brief cites real MRR/churn; the gate asserts it.

### P3 — SonarQube + graphify fusion
- [scripts/sonarqube_client.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-71ff35412f35b70bd60abedb8e58e0402762bec1abfa30a26a5ae9869f7b2a44) — real Community 26.6.0 scan: 240 issues. [scripts/fuse_signals.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-29d88e63466f78754247cd5fa6eb283ac10b0476251a7ecf1db1f5b005ce945a) joins issue counts × coupling degree and picks an exemplar at the billing-path hub `src/checkoutservice/main.go`.
- [hermes/skills/file_brownfield_ticket.md](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-7b0011104a329b363de7718db1f4c7f3c6e2b80efcc5e5e38ff4853702920502) + [hermes/config.yaml](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-12847f4b3040b142fd3c49e69d3d7de6614deeb3fd290901f3a5378f3f54de94) — ticket cites both signals + names Codegen; [scripts/assert_sonar_fusion.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-cca3e0afc6f27b9b627530551f864dbd1a62a2f1f3b1f75a7fd493cfd476ef9e) verifies GLO-16 over the Linear MCP.

### P4 — full PMF loop
- [hermes/skills/pmf_rank.md](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-999716f4b237f43a9a5fd808e675383f8295a81b6d2fcc24fb528c0980225c32) + [scripts/mem0_pmf_decisions.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-7c0c3e620f29a6ecfdc6048415af2b8df3e507f3f6f26868439bab5a86d2202a) — RICE-rank ≥2 opportunities; consult self-hosted mem0 (pgvector) + git history (returns GLO-12 @ 0.32, not re-proposed).
- [scripts/pmf_kanban_run.sh](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-c13a47f64f61d4b528edf1198ec7b17261ed010c457a4068ef54f3e20aa9e6d7) + [scripts/assert_pmf_ranked.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-60f4dd4a01932b994a749d53afbf971b90ade3678ef62c26a3e2b0c7910fb50a) — emit 3 ranked opportunities (RICE 67.5/32.4/10.0) + `recordings/pmf_ledger.json`.

### Closeout
- [scripts/build_showcase_video.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-61ee434e564752c672ccd8a3cdbc9b3a91f554b9defdb8a65f622e480a9c3608), [scripts/render_title_card.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-01e9e2d2bb207379d63fdbefcd17d7187dd412c433ee8bb9e31d31a7e4c5e2af), [scripts/render_ticket_card.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-85cfd52913be481b6fcdc0885f513aad780cc7707923cc242774d1088d489ac0) — hybrid montage (101.5s, 5 segments) + the auth-free `file://` ticket ending that finishes the P0 loop.
- [scripts/file_fullbuild_ticket.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-34d942a5b2ebdca55571910f8ffe48bed4194e26289dd78141958375d58aa0b6) + [scripts/assert_showcase_video.py](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-5ede6d46b4fd8126a00c0186d6f30fa864cc0b5813764ee7f47296ed863ea486) — author GLO-14, check off GLO-13, gate the montage.
- [docs/system-design-tradeoffs.md](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-318d44f9bb64abcee31c2fbfbf5df54f522a666e1f18326a1824869a06148b54), [docs/setup-guide.md](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-4fc7e78a455625ec3780f4d7a9d807b461b71cd4ee0c73cf9be551bfa397ec29), [docs/cto-functions.md](https://github.com/dyrtyData/sovereign-cto-stack/pull/1/files#diff-b94cba36c55c3ab13f81fd48d3fafcd123cb1bd6b315732745637e0154fa136e) — brought current for all five slices (AGENTS.md rule 6).

## Deviations from the plan

No formal `*plan*.md` exists for this task; the authoritative spec is the **structure outline**
(`.humanlayer/tasks/.../04-structure-outline-backlog-execution.md`), which records its own deviations
inline as each phase completed. Relative to the outline as first written:

### Implemented as planned
- All six slices (P0→P4 + closeout) shipped with their `assert_*.py` gates exit-0-on-pass.
- graphify coupling preserved (`frontend=7`/`checkout=6`); SonarQube fused additively.
- GLO-14 authored and snapshotted; GLO-13 P0→P4 checklist checked off.

### Deviations/surprises
- **P0 tool-call source changed.** The outline assumed tailing `~/.hermes/logs/agent.log`; that log
  carries only CLI startup lines for a `-z` run. The implementation instead drains the per-profile
  **session store** (`state.db` `messages` table) — the real authoritative record.
- **P1 reworked from a mock to a real sandbox.** Originally a stdlib CONNECT proxy / `egress-proxy`
  compose sidecar; reworked to a **real NVIDIA OpenShell 0.0.71 sandbox** and the fictional sidecar
  removed. The gate now drives a live sandbox.
- **P2 has NO graceful degradation** (user constraint). Unlike the outline's "optional/seeded"
  framing, the Stripe client **fails loud** on absent/invalid keys and **refuses** live keys.
- **P0 ticket-in-browser ending deferred and then fixed in closeout.** The live Linear URL hit an auth
  wall in the throwaway container browser; finished via `render_ticket_card.py` (`file://` snapshot).

### Additions not in plan
- `scripts/stripe_seed.py`, `scripts/render_ticket_card.py`, and the GLO-15/GLO-16 ticket snapshots
  (re-centered brownfield ticket on the billing-path hub).

### Items planned but not implemented (deferred by design)
- **Codegen named-only** (0 free runs burned) and **Moderne** remediation execution → rolled into GLO-14.
- Live visual-denial / brief-read / montage-watch **manual** beats remain unchecked (automated gates pass).

## How to verify it

### Worktree setup
```bash
git fetch origin
git worktree add /tmp/glo-13-review glo-13-full-build-sovereign-cto-stack-complete-vision-all-phases
cd /tmp/glo-13-review/sovereignCTO   # or repo root if cloned standalone
```

### Manual Testing
- [ ] Play `recordings/run_hero_*.mp4`: the left pane scrolls **real** `[live] tool … completed` lines.
- [ ] Run the egress negative test and confirm the refused CONNECT (`curl: (56) … 403`) is visibly logged.
- [ ] Read the latest `recordings/pmf_brief_run_*.md`: AARRR Revenue/Retention cite real MRR/churn, and
      "Prior decisions consulted" does not re-propose GLO-12.
- [ ] Confirm GLO-14 in Linear rolls forward Part C and the newly discovered items.

### Automated Tests
```bash
python scripts/assert_demo_authenticity.py recordings/agent_*.log
python scripts/assert_egress_policy.py
python scripts/assert_stripe_grounding.py
python scripts/assert_sonar_fusion.py
python scripts/assert_pmf_ranked.py
python scripts/assert_showcase_video.py
python scripts/assert_fullbuild_ticket.py GLO-14
docker compose config -q
gitleaks detect
```

## Description for the changelog

Execute the Sovereign CTO Stack deferred backlog: real-tool-call demo, deny-by-default OpenShell
egress, Stripe-grounded PMF, SonarQube+graphify fusion, RICE-ranked PMF with prior-decision memory,
and a showcase montage that authors the next epic (GLO-14).
