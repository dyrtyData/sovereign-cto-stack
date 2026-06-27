#!/usr/bin/env python3
"""verify_recording.py — assert a Phase-4 capture is a real, playable .mp4.

Phase-4 automated checks (outline §"Automated Verification"):

  1. valid container  — ffprobe parses the file as an mp4/mov with a video stream;
  2. duration > 0     — ffprobe reports a positive duration;
  3. moov present     — the moov atom exists (clean ffmpeg finalize, not truncated);
  4. non-blank frame  — sample a mid-run frame and assert it is NOT a single flat
                        color (the visible surface actually rendered on :99);
  5. non-static       — sample >=2 frames at DIFFERENT timestamps and assert they
                        DIFFER (the surface CHANGES over time — a live agent run,
                        not a still page). This is the TASK-1 demonstrative check.

Exit 0 on PASS, 1 on FAIL. Uses the host ffprobe/ffmpeg (Homebrew). The non-blank
check measures a frame's color spread via ffmpeg's signalstats (YAVG/UAVG/VAVG +
per-plane stddev): a flat (black/single-color) frame has ~zero luma stddev, a real
rendered surface (graph nodes, text, browser chrome) has meaningful spread. The
non-static check extracts two frames at different times and measures their
inter-frame difference (mean absolute luma delta): a still page is ~0, a live
scrolling terminal pane is well above the floor.

Usage:
  python3 scripts/verify_recording.py recordings/run_hero_<ts>.mp4
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# A real rendered surface has luma variation; a flat color frame has ~0 spread.
# Some ffmpeg builds expose signalstats.YSTDEV; many only expose YMIN/YMAX/YAVG.
# We use whichever is available and require the frame to span a meaningful luma
# range (a flat/black frame has YMAX-YMIN ~= 0 and YSTDEV ~= 0).
MIN_LUMA_STDDEV = 3.0   # if YSTDEV is available
MIN_LUMA_RANGE = 24.0   # YMAX-YMIN; flat frame ~0, a rendered surface spans wide

# Non-static: two frames at different timestamps must differ. We blend frame B
# negated onto frame A (blend=difference) and read the result's mean luma — a
# static page yields ~0, a live scrolling pane yields a clearly positive delta.
MIN_FRAME_DELTA = 1.0   # mean absolute luma difference between the two frames


def _run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def ffprobe_json(path: Path) -> dict:
    rc, out, err = _run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ])
    if rc != 0:
        raise RuntimeError(f"ffprobe failed: {err.strip()}")
    return json.loads(out or "{}")


def has_moov(path: Path) -> bool:
    """Check the moov atom is present (clean finalize).

    `ffprobe -show_format` only parses successfully when the moov is found, so a
    valid duration already implies moov for fragmented/faststart mp4. We
    additionally scan the container box list to be explicit.
    """
    # ffprobe traces box parsing on the debug log; grep for the moov box.
    rc, out, err = _run([
        "ffprobe", "-v", "trace", "-i", str(path),
    ])
    blob = (out + err)
    if "moov" in blob:
        return True
    # Fallback: a successful -show_format parse implies moov was located.
    try:
        fmt = ffprobe_json(path).get("format", {})
        return bool(fmt.get("duration"))
    except Exception:  # noqa: BLE001
        return False


def mid_frame_variation(path: Path, duration: float) -> tuple[bool, str]:
    """Extract a mid-run frame and decide whether it is NOT a flat color.

    Returns (is_non_blank, detail). Uses signalstats: YSTDEV when the build
    exposes it, otherwise the YMAX-YMIN luma range. A flat/black frame has both
    ~0; a real rendered surface (graph nodes, text, browser chrome) spans wide.
    """
    ts = max(0.0, duration / 2.0)
    with tempfile.TemporaryDirectory() as td:
        frame = Path(td) / "mid.png"
        rc, _, err = _run([
            "ffmpeg", "-v", "error", "-y", "-ss", f"{ts:.2f}",
            "-i", str(path), "-frames:v", "1", str(frame),
        ])
        if rc != 0 or not frame.is_file():
            raise RuntimeError(f"failed to extract mid frame: {err.strip()}")
        rc, _, err = _run([
            "ffmpeg", "-v", "info", "-i", str(frame),
            "-vf", "signalstats,metadata=print", "-f", "null", "-",
        ])
        blob = err  # signalstats prints to stderr

        def _g(key: str) -> float | None:
            m = re.search(rf"lavfi\.signalstats\.{key}=([0-9.]+)", blob)
            return float(m.group(1)) if m else None

        ystd = _g("YSTDEV")
        if ystd is not None:
            return ystd >= MIN_LUMA_STDDEV, f"luma stddev={ystd:.2f} (>= {MIN_LUMA_STDDEV})"
        ymax, ymin = _g("YMAX"), _g("YMIN")
        if ymax is not None and ymin is not None:
            rng = ymax - ymin
            return rng >= MIN_LUMA_RANGE, f"luma range YMAX-YMIN={rng:.0f} (>= {MIN_LUMA_RANGE})"
        raise RuntimeError("could not read luma stats from signalstats")


def _extract_frame(path: Path, ts: float, dst: Path) -> None:
    rc, _, err = _run([
        "ffmpeg", "-v", "error", "-y", "-ss", f"{ts:.2f}",
        "-i", str(path), "-frames:v", "1", str(dst),
    ])
    if rc != 0 or not dst.is_file():
        raise RuntimeError(f"failed to extract frame @ {ts:.2f}s: {err.strip()}")


def frames_differ(path: Path, duration: float) -> tuple[bool, str]:
    """Sample two frames at DIFFERENT timestamps and assert they differ.

    Returns (is_non_static, detail). We take a frame at ~1/4 and ~3/4 of the
    duration, then compute the mean absolute luma difference via the ffmpeg
    `blend=all_mode=difference` filter + signalstats YAVG of the blended result.
    A still page -> ~0; a live scrolling agent pane -> well above MIN_FRAME_DELTA.
    """
    t_a = max(0.0, duration * 0.25)
    t_b = max(t_a + 0.1, duration * 0.75)
    with tempfile.TemporaryDirectory() as td:
        fa = Path(td) / "a.png"
        fb = Path(td) / "b.png"
        _extract_frame(path, t_a, fa)
        _extract_frame(path, t_b, fb)
        # blend the two stills (difference) and read the mean luma of the diff.
        rc, _, err = _run([
            "ffmpeg", "-v", "info", "-i", str(fa), "-i", str(fb),
            "-filter_complex",
            "[0:v][1:v]blend=all_mode=difference,signalstats,metadata=print",
            "-f", "null", "-",
        ])
        blob = err
        m = re.search(r"lavfi\.signalstats\.YAVG=([0-9.]+)", blob)
        if m is None:
            raise RuntimeError("could not read blended-frame luma stats")
        delta = float(m.group(1))
        ok = delta >= MIN_FRAME_DELTA
        return ok, (f"mean inter-frame luma delta={delta:.3f} "
                    f"(>= {MIN_FRAME_DELTA}) between t={t_a:.1f}s and t={t_b:.1f}s")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: verify_recording.py <recording.mp4>")
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"FAIL: file not found: {path}")
        return 1
    for tool in ("ffprobe", "ffmpeg"):
        if shutil.which(tool) is None:
            print(f"FAIL: {tool} not on PATH (brew install ffmpeg)")
            return 1

    ok = True
    print(f"recording: {path}  ({path.stat().st_size} bytes)")

    # 1 + 2: container + duration
    try:
        info = ffprobe_json(path)
    except RuntimeError as e:
        print(f"FAIL: invalid container — {e}")
        return 1
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    vstreams = [s for s in streams if s.get("codec_type") == "video"]
    fmt_name = fmt.get("format_name", "")
    if vstreams and ("mp4" in fmt_name or "mov" in fmt_name):
        print(f"PASS: valid container ({fmt_name}), {len(vstreams)} video stream(s), "
              f"codec={vstreams[0].get('codec_name')}")
    else:
        print(f"FAIL: not a valid mp4/mov with a video stream (format={fmt_name}, "
              f"video_streams={len(vstreams)})"); ok = False

    try:
        duration = float(fmt.get("duration") or vstreams[0].get("duration") or 0.0)
    except (ValueError, IndexError):
        duration = 0.0
    if duration > 0:
        print(f"PASS: duration > 0 ({duration:.2f}s)")
    else:
        print(f"FAIL: duration not positive ({duration})"); ok = False

    # 3: moov present (clean finalize)
    if has_moov(path):
        print("PASS: moov atom present (clean finalize)")
    else:
        print("FAIL: moov atom missing (truncated / not finalized)"); ok = False

    # 4: non-blank mid-run frame
    if duration > 0:
        try:
            non_blank, detail = mid_frame_variation(path, duration)
            if non_blank:
                print(f"PASS: mid-run frame is NOT flat ({detail}) — surface rendered")
            else:
                print(f"FAIL: mid-run frame looks flat/black ({detail}) — "
                      f"surface not rendered?"); ok = False
        except RuntimeError as e:
            print(f"FAIL: non-blank check error — {e}"); ok = False
    else:
        print("SKIP: non-blank check (no duration)")

    # 5: non-static — two frames at different timestamps must differ
    if duration > 0:
        try:
            non_static, detail = frames_differ(path, duration)
            if non_static:
                print(f"PASS: recording is NON-STATIC ({detail}) — the surface "
                      f"changes over time (live agent run, not a still page)")
            else:
                print(f"FAIL: recording looks STATIC ({detail}) — frames at "
                      f"different times are (near) identical"); ok = False
        except RuntimeError as e:
            print(f"FAIL: non-static check error — {e}"); ok = False
    else:
        print("SKIP: non-static check (no duration)")

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
