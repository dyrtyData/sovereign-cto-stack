#!/usr/bin/env python3
"""assert_showcase_video.py — gate the Phase-6 showcase montage (exit-0-on-pass).

The closeout deliverable (design Q6) is the hybrid-montage showcase video. This
gate asserts two checkable properties of the FINAL concat, in the repo's
established assert_*.py shape:

  (A) scripts/verify_recording.py PASSES on recordings/showcase_<ts>.mp4 — it is a
      real, playable, non-blank, NON-STATIC .mp4 (valid container, duration>0,
      moov present, rendered surface, frames differ over time); AND
  (B) it contains AT LEAST the minimum guaranteed segments — the visual hero
      loop(s) — read from the showcase_manifest.json that build_showcase_video.py
      writes next to the output. The montage degrades gracefully (design Q6): the
      non-visual proof segments (egress / Stripe / SonarQube / ranked-PMF) are
      included only when their artifact is present, so the GUARANTEED minimum the
      gate enforces is the visual hero loop that is always captured. Set
      SHOWCASE_MIN_HERO / SHOWCASE_MIN_SEGMENTS to raise the bar.

Exit 0 on PASS, 1 on FAIL, 2 on harness error (no montage / no manifest / missing
ffprobe) — distinct from a silent pass, mirroring the other gates.

Usage:
  python3 scripts/assert_showcase_video.py                       # newest showcase_*.mp4
  python3 scripts/assert_showcase_video.py recordings/showcase_<ts>.mp4
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RECORDINGS = REPO_ROOT / "recordings"
MANIFEST_NAME = "showcase_manifest.json"

MIN_HERO = int(os.environ.get("SHOWCASE_MIN_HERO", "1"))
MIN_SEGMENTS = int(os.environ.get("SHOWCASE_MIN_SEGMENTS", "1"))


def _newest_showcase() -> Path | None:
    matches = sorted(RECORDINGS.glob("showcase_*.mp4"), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


def main(argv: list[str]) -> int:
    if shutil.which("ffprobe") is None:
        print("HARNESS ERROR: ffprobe not on PATH (brew install ffmpeg)")
        return 2

    path = Path(argv[0]) if argv else _newest_showcase()
    if path is None or not path.is_file():
        print("HARNESS ERROR: no showcase_<ts>.mp4 found "
              "(run scripts/build_showcase_video.py first)")
        return 2

    print(f"showcase: {path}  ({path.stat().st_size} bytes)")

    ok = True

    # (A) verify_recording.py passes on the final concat
    rc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_recording.py"), str(path)],
        capture_output=True, text=True,
    )
    sys.stdout.write(rc.stdout)
    if rc.returncode == 0:
        print("PASS - verify_recording.py passes on the final concat")
    else:
        print("FAIL - verify_recording.py did NOT pass on the final concat")
        ok = False

    # (B) minimum guaranteed segments present (from the manifest)
    manifest_path = path.parent / MANIFEST_NAME
    if not manifest_path.is_file():
        print(f"HARNESS ERROR: manifest {manifest_path.name} missing next to the montage")
        return 2
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception as e:  # noqa: BLE001
        print(f"HARNESS ERROR: cannot parse {manifest_path.name}: {e}")
        return 2

    segments = manifest.get("segments", [])
    hero = sum(1 for s in segments if s.get("kind") == "hero")
    total = len(segments)
    print(f"manifest: {total} segment(s) — {hero} visual hero loop(s): "
          f"{', '.join(s.get('id', '?') for s in segments)}")

    if hero >= MIN_HERO:
        print(f"PASS - at least {MIN_HERO} visual hero loop present ({hero})")
    else:
        print(f"FAIL - fewer than {MIN_HERO} visual hero loop(s) ({hero})")
        ok = False

    if total >= MIN_SEGMENTS:
        print(f"PASS - at least {MIN_SEGMENTS} segment(s) in the montage ({total})")
    else:
        print(f"FAIL - fewer than {MIN_SEGMENTS} segment(s) ({total})")
        ok = False

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
