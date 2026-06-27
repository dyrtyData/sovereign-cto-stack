#!/usr/bin/env python3
"""render_ticket_card.py — render a local ticket snapshot to self-contained HTML.

P0 ending fix (deferred from Phase 1). The recorded demo wants to END on the
filed Linear ticket appearing in the browser — but the throwaway container
Chromium has no Linear session, so navigating to the live ticket URL hits
Linear's AUTH WALL (the login page renders, not the ticket). The fix: render the
tracked, public, local `tickets/<ID>.md` snapshot to a self-contained file://
HTML the recorder can open by path with NO auth (the real-Linear-UI ending — a
persistent authenticated Chromium profile — is rolled forward to GLO-14).

It follows the render_service_graph.py house style: a module-level f-string
template + inlined payload, one CDN <script> (marked.js to render the snapshot's
Markdown), no build step, opens standalone in any browser.

Source selection (no Linear call — reads the git-tracked snapshot):
  - --id GLO-16            : render tickets/GLO-16.md
  - --prefix "[Brownfield]": render the newest tickets/<ID>.md whose title starts
                             with that prefix (default: the most recently modified)
  - default                : the newest tickets/<ID>.md by mtime

Usage:
  python3 scripts/render_ticket_card.py --prefix "[Brownfield]" --out recordings/ticket.html
  python3 scripts/render_ticket_card.py --id GLO-16 --out recordings/ticket.html
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TICKETS_DIR = REPO_ROOT / "tickets"

MARKED_CDN = "https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"

# Pull the title + identifier + url + labels out of the snapshot front-matter the
# snapshot_tickets.py renderer writes (a `# <ID> — <title>` heading + a bullet
# list with **identifier:** / **url:** / **labels:** lines).
_RE_TITLE = re.compile(r"^#\s+(.*)$", re.M)
_RE_FIELD = re.compile(r"^\-\s+\*\*(\w+):\*\*\s+(.*)$", re.M)


def _parse(md: str) -> dict:
    title = (_RE_TITLE.search(md) or [None, ""])[1] if _RE_TITLE.search(md) else ""
    fields = {k.lower(): v.strip() for k, v in _RE_FIELD.findall(md)}
    return {"title": title, **fields}


def pick(args: argparse.Namespace) -> Path | None:
    if args.id:
        p = TICKETS_DIR / f"{args.id}.md"
        return p if p.is_file() else None
    candidates = sorted(TICKETS_DIR.glob("GLO-*.md"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    if args.prefix:
        for p in candidates:
            head = p.read_text(encoding="utf-8")[:400]
            # snapshot heading is "# GLO-NN — [Prefix] ..."; match the bracket tag
            if args.prefix in head:
                return p
    return candidates[0] if candidates else None


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<script src="{cdn}"></script>
<style>
  html, body {{ margin: 0; min-height: 100%; background: #0f1721; color: #e7eef6;
                font-family: -apple-system, Segoe UI, Roboto, sans-serif; }}
  #bar {{ background: #131c28; border-bottom: 2px solid #e8543f; padding: 14px 26px;
          display: flex; align-items: center; gap: 16px; position: sticky; top: 0; }}
  #bar .id {{ color: #e8543f; font-weight: 800; font-size: 22px;
              font-family: ui-monospace, Menlo, monospace; }}
  #bar .lbl {{ background: #e8543f22; color: #f3b8ab; border: 1px solid #e8543f55;
               border-radius: 5px; padding: 3px 10px; font-size: 13px; }}
  #bar .src {{ margin-left: auto; color: #8fd19e; font-size: 13px;
               font-family: ui-monospace, Menlo, monospace; }}
  #doc {{ max-width: 1000px; margin: 0 auto; padding: 26px 40px 60px;
          line-height: 1.6; }}
  #doc h1 {{ font-size: 27px; border-bottom: 1px solid #25313f; padding-bottom: 8px; }}
  #doc h2 {{ font-size: 21px; color: #f0b429; margin-top: 30px; }}
  #doc code {{ background: #1b2735; padding: 1px 6px; border-radius: 4px;
               font-size: 14px; color: #9fd0ff; }}
  #doc a {{ color: #6cb6ff; }}
  #doc li {{ margin: 4px 0; }}
</style>
</head>
<body>
  <div id="bar">
    <span class="id">{ident}</span>
    <span class="lbl">{labels}</span>
    <span class="src">tickets/{ident}.md · git-tracked snapshot (no auth)</span>
  </div>
  <div id="doc"></div>
<script>
  const md = {payload};
  document.getElementById('doc').innerHTML =
    (window.marked ? marked.parse(md.body) : ('<pre>' + md.body + '</pre>'));
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--id", help="render this ticket id (tickets/<ID>.md)")
    ap.add_argument("--prefix", help='render newest ticket whose title carries this tag, e.g. "[Brownfield]"')
    ap.add_argument("--out", required=True, help="output HTML path")
    args = ap.parse_args()

    src = pick(args)
    if src is None:
        print("render_ticket_card: no matching tickets/<ID>.md snapshot found")
        return 1
    md = src.read_text(encoding="utf-8")
    meta = _parse(md)
    ident = meta.get("identifier") or src.stem

    html = HTML.format(
        title=meta.get("title", ident),
        cdn=MARKED_CDN,
        ident=ident,
        labels=meta.get("labels", ""),
        payload=json.dumps({"body": md}),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"render_ticket_card: wrote {out} (from {src.relative_to(REPO_ROOT)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
