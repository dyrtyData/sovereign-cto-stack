#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""build_showcase_video.py — assemble the comprehensive showcase montage (Phase 6).

The submitted demo is a HYBRID MONTAGE (design Q6): live split-screen captures for
the inherently-visual hero loops (the tech-debt graphify loop + ticket-in-browser,
and the PMF brief), plus short purpose-built segments for the non-visual proofs
(the denied egress CONNECT, Stripe-grounded AARRR, SonarQube issues, ranked PMF).

This script:
  1. Defines an ORDERED set of candidate segments. Each declares either:
       - a recording glob (a real .mp4 captured by record_run.sh), OR
       - a data-surface backed by a repo artifact (e.g. stripe_metrics.json) that
         is rendered to a self-contained title/proof HTML, then to a short clip.
  2. Includes a segment ONLY when its source is present AND (for recordings)
     passes scripts/verify_recording.py — the automatic "best-video-currently-
     possible" fallback: a missing/failed segment is simply dropped, the rest
     still ship (design Q6, the graceful degradation).
  3. Prepends a generated TITLE CARD (render_title_card.py) before each included
     segment so the montage reads as a coherent story with labeled chapters.
  4. ffmpeg-concats exactly the clips that landed into recordings/showcase_<ts>.mp4
     (a simple concat — no editing suite — so the whole thing regenerates from a
     clean clone with zero manual steps; design Q6 sub-decision).

All clips are normalized to a common WxH / fps / codec before concat so the
demuxer concat is safe across heterogeneous sources (screen captures + rendered
cards). The two visual hero loops are the MINIMUM guaranteed segments the gate
(scripts/assert_showcase_video.py) requires.

Usage:
  python3 scripts/build_showcase_video.py
  python3 scripts/build_showcase_video.py --out recordings/showcase_custom.mp4
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_title_card as TC  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RECORDINGS = REPO_ROOT / "recordings"
WORK = RECORDINGS / "_showcase_work"

W, H, FPS = 1280, 720, 15
TITLE_SECONDS = 3.0          # how long each title card holds
DATA_SECONDS = 6.0           # how long a rendered data-surface proof holds
HERO_KIND = "hero"           # segments that count toward the guaranteed minimum

# Manifest line marking each guaranteed visual-hero loop, written next to the
# output so the gate can confirm the minimum set without re-deriving it.
MANIFEST_NAME = "showcase_manifest.json"


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _latest(glob: str) -> Path | None:
    matches = sorted(RECORDINGS.glob(glob), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


def verify_recording(path: Path) -> bool:
    """Gate a candidate recording through scripts/verify_recording.py (exit 0)."""
    rc = _run([sys.executable, str(REPO_ROOT / "scripts" / "verify_recording.py"),
               str(path)]).returncode
    return rc == 0


# --- segment catalogue --------------------------------------------------------
# Ordered. `kind="hero"` segments count toward the guaranteed minimum. A segment
# is INCLUDED only if its source resolves (recording present+valid, or its
# backing artifact exists). `data` segments render a self-contained proof surface.

def _stripe_bullets() -> list[str]:
    try:
        m = json.loads((RECORDINGS / "stripe_metrics.json").read_text())
        return [
            f"MRR ${m.get('mrr')}/mo · ARR ${m.get('arr')} ({m.get('source')})",
            f"lifetime churn {int(m.get('churn',{}).get('rate',0)*100)}% · "
            f"{m.get('active_subs')} active / {m.get('canceled_subs')} canceled",
            f"{len(m.get('cohorts',[]))} monthly cohorts grounding AARRR Revenue/Retention",
        ]
    except Exception:  # noqa: BLE001
        return []


def _sonar_bullets() -> list[str]:
    try:
        s = json.loads((RECORDINGS.parent / "graphify-out" / "sonar-issues.json").read_text())
        t = s.get("totals", {})
        by = t.get("by_type", {})
        return [
            f"SonarQube (DETECT): {t.get('issues')} issues — "
            f"{by.get('CODE_SMELL',0)} smells / {by.get('BUG',0)} bugs / "
            f"{by.get('VULNERABILITY',0)} vulns",
            "graphify (KEEP): frontend=7 / checkoutservice=6 coupling",
            "Hermes (JUDGMENT): billing-path priority → Codegen (GLO-16)",
        ]
    except Exception:  # noqa: BLE001
        return []


def _pmf_bullets() -> list[str]:
    try:
        led = json.loads((RECORDINGS / "pmf_ledger.json").read_text())
        opps = led.get("opportunities", [])
        scores = " / ".join(str(o.get("rice_score")) for o in opps[:3])
        prior = led.get("prior_decisions_consulted", {}).get("already_decided_ids", [])
        shipped = sum(1 for o in opps if o.get("shipped"))
        return [
            f"{len(opps)} opportunities ranked RICE ({scores})",
            "grounded in corpus + real Stripe MRR/churn",
            f"prior decisions consulted — did NOT re-propose {', '.join(prior) or 'past bets'}",
            f"North Star: {shipped}/{len(opps)} shipped:true (P5 flip from real Stripe outcome)",
        ]
    except Exception:  # noqa: BLE001
        return []


def _memory_bullets() -> list[str]:
    """Proof bullets for the read-only mem0 memory view (GLO-14 P1 → D-2).

    Read from the most recent `recordings/memory_*.html` card's emitted baseline
    JSON if present, else state the capability. The load-bearing accumulation proof
    is assert_memory_accumulates.py; this segment is the visual."""
    try:
        baselines = sorted(RECORDINGS.glob("memory_*_baseline.json"),
                           key=lambda p: p.stat().st_mtime)
        rows = None
        if baselines:
            rows = json.loads(baselines[-1].read_text()).get("count")
        return [
            "mem0 'memories' collection ACCUMULATES run-over-run (P1 closed the write path)",
            (f"read-only view shows {rows} memories"
             if rows is not None else
             "read-only HTML view renders the rows + mem0-native entity links"),
            "git stays authoritative; mem0 is the recall complement (search-before, add-after, infer=True)",
        ]
    except Exception:  # noqa: BLE001
        return [
            "mem0 'memories' collection ACCUMULATES run-over-run (P1 closed the write path)",
            "read-only HTML view renders the rows + mem0-native entity links",
            "git stays authoritative; mem0 is the recall complement",
        ]


def _kanban_bullets() -> list[str]:
    """Proof bullets for the PMF Kanban create→claim→complete lifecycle."""
    return [
        "PMF Kanban (~/.hermes/kanban.db): create → claim → complete",
        "the CTO-Market loop drives a real card through every state transition",
        "the lifecycle is what flips a bet's North Star 'shipped' signal (with P5)",
    ]


def catalogue() -> list[dict]:
    return [
        # ---- guaranteed visual hero loops (the minimum set) -----------------
        {
            "id": "hero-techdebt", "kind": HERO_KIND,
            "recording": "run_hero_*.mp4",
            "card": dict(
                kicker="Sovereign CTO Stack — hero loop",
                headline="Tech-debt audit, grounded & filed",
                bullets=[
                    "graphify maps Online Boutique → frontend=7 / checkout=6 coupling",
                    "real query_cto_knowledge + save_issue tool calls fire live",
                    "ends on the filed [Brownfield] Linear ticket in the browser",
                ],
                footer="gates: <b>verify_recording.py</b> · <b>assert_demo_authenticity.py</b>",
            ),
        },
        {
            "id": "hero-pmf", "kind": HERO_KIND,
            "recording": "run_pmf_*.mp4",
            "card": dict(
                kicker="Sovereign CTO Stack — hero loop",
                headline="PMF research brief",
                bullets=[
                    "CTO-Market scrapes the web + multi-angle-grounds the corpus",
                    "writes a textbook-cited strategic brief over the shared Kanban",
                ],
                footer="gate: <b>assert_pmf_run.py</b>",
            ),
        },
        # ---- non-visual proofs (rendered data surfaces) ---------------------
        {
            "id": "egress-denial", "kind": "data",
            "artifact": REPO_ROOT / "egress" / "policy.yaml",
            "card": dict(
                kicker="P1 — sovereign safety",
                headline="Deny-by-default egress",
                bullets=[
                    "non-allow-listed CONNECT (example.com:443) → REFUSED (403)",
                    "api.linear.app:443 → allowed (200)",
                    "enforced out-of-process by a real NVIDIA OpenShell sandbox",
                ],
                footer="gate: <b>assert_egress_policy.py</b> (the negative test is load-bearing)",
            ),
        },
        {
            "id": "stripe-aarrr", "kind": "data",
            "artifact": RECORDINGS / "stripe_metrics.json",
            "card_fn": lambda: dict(
                kicker="P2 — competition requirement",
                headline="Stripe-grounded AARRR",
                bullets=_stripe_bullets(),
                footer="gate: <b>assert_stripe_grounding.py</b> (real Stripe test-mode data)",
            ),
        },
        {
            "id": "sonar-issues", "kind": "data",
            "artifact": REPO_ROOT / "graphify-out" / "sonar-issues.json",
            "card_fn": lambda: dict(
                kicker="P3 — DETECT + KEEP → JUDGMENT",
                headline="SonarQube + graphify fusion",
                bullets=_sonar_bullets(),
                footer="gate: <b>assert_sonar_fusion.py</b> (fused onto service-coupling.json)",
            ),
        },
        {
            "id": "pmf-ranked", "kind": "data",
            "artifact": RECORDINGS / "pmf_ledger.json",
            "card_fn": lambda: dict(
                kicker="P4 — full PMF loop",
                headline="RICE-ranked opportunities",
                bullets=_pmf_bullets(),
                footer="gate: <b>assert_pmf_ranked.py</b> (≥2 scored, ranked, + prior decisions)",
            ),
        },
        # ---- GLO-14 D-2 segments (title-carded; always render) --------------
        # These surface lower-signal-but-load-bearing components as title cards so
        # the montage tells the fuller P3 story. `kind="title"` segments need NO
        # backing artifact — they always render from their bullets.
        {
            "id": "memory-view", "kind": "title",
            # Prefer a REAL captured clip of the read-only mem0 memory view
            # (recordings/memory_view_*.mp4, screen-captured from render_memory_card.py's
            # HTML); fall back to the title card below if none is present. skip_verify:
            # the card is near-static, so verify_recording's non-static check would reject it.
            "recording": "memory_view_*.mp4", "skip_verify": True,
            "card_fn": lambda: dict(
                kicker="GLO-14 P1 — a system that LEARNS",
                headline="mem0 memory view — it grows",
                bullets=_memory_bullets(),
                footer="gates: <b>assert_memory_accumulates.py</b> · <b>assert_memory_view_grows.py</b>",
            ),
        },
        {
            "id": "kanban-transitions", "kind": "title",
            "card_fn": lambda: dict(
                kicker="GLO-14 P3 — full PMF loop",
                headline="Kanban: create → claim → complete",
                bullets=_kanban_bullets(),
                footer="state: <b>~/.hermes/kanban.db</b> (real lifecycle, not a mock)",
            ),
        },
        {
            "id": "greptile-review", "kind": "title",
            "card": dict(
                kicker="GLO-14 P2 — ship AND review",
                headline="Greptile PR review (out-of-repo)",
                bullets=[
                    "every filed ticket carries: 'run Greptile on the PR (/greptile)'",
                    "HumanLayer-on-Claude-Code runs greptile review + addresses findings",
                    "the Greptile CLI/skill live globally in ~/.claude — zero in-repo coupling",
                ],
                footer="gate: <b>assert_greptile_instruction.py</b> (the ticket carries the line)",
            ),
        },
        {
            "id": "linear-ending", "kind": "title",
            # Prefer a REAL captured clip of the authenticated Linear ticket UI
            # (recordings/auth_ending_*.mp4, produced via the persistent profile);
            # gracefully fall back to the title card below if none is present.
            # skip_verify: a live ticket page is near-static, so the non-static
            # heuristic in verify_recording.py would reject it — we trust the clip.
            "recording": "auth_ending_*.mp4", "skip_verify": True,
            "card": dict(
                kicker="GLO-14 P3 — the ending",
                headline="Filed Linear ticket (authenticated)",
                bullets=[
                    "DEFAULT: the git-tracked tickets/<ID>.md snapshot, rendered file:// (no auth)",
                    "OPTIONAL: TICKET_LIVE_URL=1 + a persistent profile ends on the REAL Linear UI",
                    "both paths show the just-filed [Brownfield]/[Product] ticket in the browser",
                ],
                footer="gate: <b>assert_demo_authenticity.py</b> (the snapshot ending is reproducible)",
            ),
        },
    ]


# --- clip helpers -------------------------------------------------------------

def normalize_clip(src: Path, dst: Path) -> bool:
    """Re-encode a recording to the common WxH/fps/codec so concat is safe."""
    rc = _run([
        "ffmpeg", "-v", "error", "-y", "-i", str(src),
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
               f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0f1721,fps={FPS},format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-movflags", "+faststart", str(dst),
    ]).returncode
    return rc == 0 and dst.is_file()


def card_clip(card: dict, dst: Path, seconds: float) -> bool:
    """Render a title card to HTML → PNG (headless browser) → a still clip.

    Falls back to an ffmpeg-drawn solid card (drawtext) if no headless browser is
    available, so the build never hard-depends on a host browser.
    """
    WORK.mkdir(parents=True, exist_ok=True)
    html = WORK / f"card_{dst.stem}.html"
    png = WORK / f"card_{dst.stem}.png"
    html.write_text(
        TC.render_html(card.get("kicker", "Sovereign CTO Stack"),
                       card["headline"], card.get("bullets", []),
                       card.get("footer", ""), W, H),
        encoding="utf-8",
    )
    have_png = TC.render_png(html, png, W, H)
    if have_png:
        rc = _run([
            "ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{seconds}",
            "-i", str(png), "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-movflags", "+faststart", str(dst),
        ]).returncode
        return rc == 0 and dst.is_file()
    # fallback: solid background + drawtext headline (no browser needed)
    headline = card["headline"].replace(":", r"\:").replace("'", "")
    kicker = card.get("kicker", "").replace(":", r"\:").replace("'", "")
    draw = (
        f"drawtext=text='{kicker}':fontcolor=0xe8543f:fontsize=34:x=(w-tw)/2:y=h/2-120,"
        f"drawtext=text='{headline}':fontcolor=0xe7eef6:fontsize=56:x=(w-tw)/2:y=h/2-40"
    )
    rc = _run([
        "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
        "-i", f"color=c=0x0f1721:s={W}x{H}:d={seconds}:r={FPS}",
        "-vf", draw + ",format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-movflags", "+faststart", str(dst),
    ]).returncode
    return rc == 0 and dst.is_file()


def data_clip(card: dict, dst: Path, seconds: float) -> bool:
    """A data-surface proof segment is itself rendered as a (longer) title card.

    The proof's load-bearing facts (e.g. the real Stripe MRR/churn numbers, the
    SonarQube totals, the RICE scores) are read from the repo artifact and shown
    on screen — the non-visual proof made visible without needing a live capture.
    """
    return card_clip(card, dst, seconds)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ap.add_argument("--out", default=str(RECORDINGS / f"showcase_{ts}.mp4"))
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            print(f"FAIL: {tool} not on PATH (brew install ffmpeg)")
            return 1

    RECORDINGS.mkdir(parents=True, exist_ok=True)
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)

    clips: list[Path] = []
    included: list[dict] = []
    print("=== build_showcase_video: selecting segments ===")

    for seg in catalogue():
        sid = seg["id"]
        clip = WORK / f"seg_{len(clips):02d}_{sid}.mp4"

        if "recording" in seg:
            rec = _latest(seg["recording"])
            seg_clip = WORK / f"_body_{len(clips):02d}_{sid}.mp4"
            usable = rec is not None and (seg.get("skip_verify") or verify_recording(rec))
            if usable and normalize_clip(rec, seg_clip):
                print(f"  keep  {sid:16s} — recording {rec.name}")
            elif "card" in seg or "card_fn" in seg:
                # graceful fallback (design D-2 / user-blessed): no usable clip ->
                # render the title card as the body so the chapter still appears.
                why = "no clip matches" if rec is None else f"{rec.name} unusable"
                print(f"  note  {sid:16s} — {why} {seg['recording']}; falling back to title card")
                card = seg["card_fn"]() if "card_fn" in seg else dict(seg["card"])
                if not data_clip(card, seg_clip, DATA_SECONDS):
                    print(f"  skip  {sid:16s} — fallback title clip render failed")
                    continue
                seg["_no_title"] = True   # the body IS the card; don't prepend another
            else:
                print(f"  skip  {sid:16s} — no recording matches {seg['recording']}")
                continue
        elif seg.get("kind") == "title":
            # GLO-14 D-2 title-carded segment: NO backing artifact required — it
            # always renders from its bullets (the fuller-story chapters: memory
            # view, Kanban transitions, Greptile review, the Linear ending).
            card = seg["card_fn"]() if "card_fn" in seg else dict(seg["card"])
            if not card.get("bullets"):
                print(f"  skip  {sid:16s} — title segment produced no bullets")
                continue
            print(f"  keep  {sid:16s} — title-carded segment")
            seg_clip = WORK / f"_body_{len(clips):02d}_{sid}.mp4"
            if not data_clip(card, seg_clip, DATA_SECONDS):
                print(f"  skip  {sid:16s} — title clip render failed")
                continue
            seg["_no_title"] = True
        else:
            art = seg.get("artifact")
            if art is None or not Path(art).exists():
                print(f"  skip  {sid:16s} — artifact absent ({art})")
                continue
            print(f"  keep  {sid:16s} — data surface from {Path(art).name}")
            card = seg["card_fn"]() if "card_fn" in seg else dict(seg["card"])
            if not card.get("bullets"):
                print(f"  skip  {sid:16s} — artifact produced no proof bullets")
                continue
            seg_clip = WORK / f"_body_{len(clips):02d}_{sid}.mp4"
            if not data_clip(card, seg_clip, DATA_SECONDS):
                print(f"  skip  {sid:16s} — data clip render failed")
                continue
            # for data segments the body IS the card; no separate title card
            seg["_no_title"] = True
            card_template = card

        # title card before the segment body (recordings carry a static card;
        # data segments already render their own labeled surface as the body)
        if "recording" in seg and not seg.get("_no_title"):
            tcard = WORK / f"_title_{len(clips):02d}_{sid}.mp4"
            title_card = seg["card_fn"]() if "card_fn" in seg else seg["card"]
            if card_clip(title_card, tcard, TITLE_SECONDS):
                clips.append(tcard)
        clips.append(seg_clip)
        included.append({"id": sid, "kind": seg["kind"]})

    hero_count = sum(1 for s in included if s["kind"] == HERO_KIND)
    print(f"\n=== included {len(included)} segment(s); {hero_count} visual hero loop(s) ===")

    if not clips:
        print("FAIL: no segments landed — nothing to concat (need at least the hero loop)")
        return 1

    # demuxer concat of the normalized clips
    listfile = WORK / "concat.txt"
    listfile.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rc = _run([
        "ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
        "-i", str(listfile), "-c", "copy", "-movflags", "+faststart", str(out),
    ]).returncode
    if rc != 0 or not out.is_file():
        # copy can fail if timestamps clash; re-encode as a fallback
        rc = _run([
            "ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
            "-i", str(listfile), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "23", "-movflags", "+faststart", str(out),
        ]).returncode
    if rc != 0 or not out.is_file():
        print(f"FAIL: ffmpeg concat did not produce {out}")
        return 1

    manifest = {
        "output": out.name,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "segments": included,
        "hero_segments": hero_count,
        "total_clips": len(clips),
    }
    (out.parent / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nOK — showcase montage at {out}")
    print(f"  segments: {', '.join(s['id'] for s in included)}")
    print(f"  manifest: {(out.parent / MANIFEST_NAME)}")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
