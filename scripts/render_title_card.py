#!/usr/bin/env python3
"""render_title_card.py — self-contained HTML title cards for the showcase montage.

The Phase-6 hybrid montage (design Q6) stitches per-segment .mp4s with short
title cards between them. A title card is just a self-contained single-file HTML
surface painted onto :99 (the recorder's virtual display) — exactly the
`render_service_graph.py` house style: a module-level f-string template + inlined
`json.dumps` payload + one CDN `<script>`, no build step, opens standalone by
path. The recorder captures it for a few seconds and `build_showcase_video.py`
turns the captured (or directly ffmpeg-rendered) frame into a clip.

Each card carries:
  - a kicker (e.g. "Sovereign CTO Stack — P1"),
  - a headline (e.g. "Deny-by-default egress"),
  - 1–3 bullet "proof" lines (the load-bearing fact the next segment shows),
  - an optional footer (the gate that proves it).

It is data-driven so `build_showcase_video.py` can render one card per landed
segment without bespoke HTML per segment.

Usage:
  # render one card to HTML (then the recorder/ffmpeg paints it):
  python3 scripts/render_title_card.py \
      --kicker "Sovereign CTO Stack — P1" \
      --headline "Deny-by-default egress" \
      --bullet "A non-allow-listed CONNECT is REFUSED (403)" \
      --bullet "api.linear.app:443 still succeeds" \
      --footer "gate: scripts/assert_egress_policy.py" \
      --out recordings/_titlecards/p1.html

  # or render straight to a PNG frame with the bundled libraries (no recorder):
  python3 scripts/render_title_card.py --headline "Showcase" --png recordings/_titlecards/p1.png
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# One CDN script keeps the house style identical to render_service_graph.py; the
# card renders fine without it (pure CSS), but we keep the single-<script> shape
# so the surface is byte-for-byte the same family of self-contained HTML files.
FONT_CDN = "https://unpkg.com/@fontsource/jetbrains-mono@5.0.18/index.css"

# Default canvas matches the recorder's :99 geometry (SCREEN_W x SCREEN_H).
DEFAULT_W = 1280
DEFAULT_H = 720

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<link rel="stylesheet" href="{cdn}" />
<style>
  html, body {{ margin: 0; height: 100%; width: 100%; background: #0f1721;
                color: #e7eef6; overflow: hidden;
                font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular,
                             Menlo, monospace; }}
  #wrap {{ box-sizing: border-box; height: 100%; width: 100%;
           display: flex; flex-direction: column; justify-content: center;
           padding: 0 9%; }}
  #kicker {{ color: #e8543f; font-size: 26px; letter-spacing: 3px;
             text-transform: uppercase; font-weight: 700; }}
  #headline {{ font-size: 64px; line-height: 1.08; margin: 14px 0 28px;
               font-weight: 800; }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  li {{ font-size: 28px; line-height: 1.7; color: #cdd9e5; }}
  li::before {{ content: "→ "; color: #f0b429; font-weight: 700; }}
  #footer {{ margin-top: 34px; font-size: 20px; color: #9fb3c8; }}
  #footer b {{ color: #8fd19e; }}
  #rule {{ height: 5px; width: 132px; background: #e8543f; border-radius: 3px;
           margin: 0 0 8px; }}
</style>
</head>
<body>
  <div id="wrap">
    <div id="rule"></div>
    <div id="kicker">{kicker}</div>
    <div id="headline">{headline}</div>
    <ul id="bullets"></ul>
    <div id="footer"></div>
  </div>
<script>
  const data = {payload};
  const ul = document.getElementById('bullets');
  (data.bullets || []).forEach((b) => {{
    const li = document.createElement('li');
    li.textContent = b;
    ul.appendChild(li);
  }});
  const f = document.getElementById('footer');
  if (data.footer) {{ f.innerHTML = data.footer; }}
</script>
</body>
</html>
"""


def render_html(kicker: str, headline: str, bullets: list[str],
                footer: str, width: int, height: int) -> str:
    payload = {"bullets": bullets, "footer": footer}
    return HTML.format(
        title=headline or "Sovereign CTO Stack",
        cdn=FONT_CDN,
        kicker=kicker,
        headline=headline,
        payload=json.dumps(payload),
    )


def render_png(html_path: Path, png_path: Path, width: int, height: int,
               seconds: float = 1.0) -> bool:
    """Render the title card HTML to a PNG using a headless browser if present.

    Optional convenience for `build_showcase_video.py`'s no-recorder path. Tries
    chromium/chrome --headless --screenshot; returns False if none is available
    (the caller then falls back to an ffmpeg-drawn solid card so the build never
    hard-depends on a host browser).
    """
    png_path.parent.mkdir(parents=True, exist_ok=True)
    for exe in ("chromium", "chromium-browser", "google-chrome", "chrome",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium"):
        path = exe if Path(exe).exists() else shutil.which(exe)
        if not path:
            continue
        rc = subprocess.run(
            [path, "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--window-size={width},{height}",
             f"--screenshot={png_path}", f"file://{html_path.resolve()}"],
            capture_output=True, text=True,
        ).returncode
        if rc == 0 and png_path.is_file():
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kicker", default="Sovereign CTO Stack")
    ap.add_argument("--headline", required=True)
    ap.add_argument("--bullet", dest="bullets", action="append", default=[],
                    help="a proof bullet (repeatable)")
    ap.add_argument("--footer", default="")
    ap.add_argument("--width", type=int, default=DEFAULT_W)
    ap.add_argument("--height", type=int, default=DEFAULT_H)
    ap.add_argument("--out", help="write the title-card HTML here")
    ap.add_argument("--png", help="also try to render a PNG (headless browser)")
    args = ap.parse_args()

    html = render_html(args.kicker, args.headline, args.bullets, args.footer,
                       args.width, args.height)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"render_title_card: wrote {out}")
    else:
        # default: a temp file so --png alone still works
        tf = Path(tempfile.mkstemp(suffix=".html")[1])
        tf.write_text(html, encoding="utf-8")
        out = tf

    if args.png:
        ok = render_png(out, Path(args.png), args.width, args.height)
        print(f"render_title_card: PNG {'written' if ok else 'SKIPPED (no headless browser)'} "
              f"-> {args.png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
