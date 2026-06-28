#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#   "mem0ai[nlp]>=2.0.0,<3.0.0",
#   "sentence-transformers",
#   "vecs",
#   "psycopg2-binary",
#   "ollama",
# ]
# ///
"""render_memory_card.py — a read-only visual view of the mem0 `memories` collection.

GLO-14 P3 / D-2 demo surface. P1 closed the mem0 write path so the unified
`memories` collection now ACCUMULATES run-over-run; this is the cheap visual proof
of that growth for the showcase montage. It queries the live `memories` rows (the
deterministic-helper writes, tagged `source:"agent_run"`, plus any seeded rows) +
their mem0-native entity links and renders them to a self-contained `file://` HTML
card the recorder can open by path with NO auth — exactly the
`render_ticket_card.py:51-107` marked.js template/screenshot pattern (a module-level
f-string template + an inlined `json.dumps` payload + one CDN <script>, no build
step). Reuses `mem0_record_decision._config()` so the connection/collection/user are
identical to the writer's (design Q2: one unified collection, read where we wrote).

Two modes:
  * default (a single snapshot): render the collection's current rows once.
  * --baseline <path>: write a JSON baseline of the current row ids/count to <path>
    so a later `--against <baseline>` render can highlight which rows are NEW since
    that baseline — the "before/after a loop" view D-2 asks for. The card title bar
    shows `before N → after M (+K new)` when a baseline is supplied. This is also the
    machine-readable hook `assert_memory_view_grows.py` parses to assert growth.

The card is intentionally read-only: it never writes to mem0. It self-skips
gracefully if pgvector is unreachable (prints a note, still emits a valid HTML card
saying "collection unreachable") so a montage build never hard-fails on a missing
backend — the accumulation GATE (`assert_memory_accumulates.py`) is the load-bearing
proof; this card is the visualization.

Usage:
  uv run scripts/render_memory_card.py --out recordings/memory_<ts>.html
  uv run scripts/render_memory_card.py --baseline recordings/mem_before.json   # snapshot ids
  uv run scripts/render_memory_card.py --against recordings/mem_before.json \
      --out recordings/memory_after.html                                       # highlight new

Emits a one-line JSON receipt on stdout:
  {"rendered": true, "rows": M, "new_rows": K, "out": "recordings/memory_<ts>.html"}
"""
from __future__ import annotations

import argparse
import datetime
import html as _html
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import mem0_record_decision as W  # noqa: E402  (reuse _config/COLLECTION/USER_ID)

MARKED_CDN = "https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"


def _results(res):
    if isinstance(res, dict):
        return res.get("results", [])
    return res or []


def _row_id(r: dict) -> str:
    """A stable identity for a mem0 row across renders.

    Prefer mem0's own row id; fall back to the decision_id metadata; finally to the
    memory text. (Two renders of the SAME collection return the same ids — that is
    what lets us highlight what is NEW since a baseline.)
    """
    return str(r.get("id") or (r.get("metadata") or {}).get("decision_id") or r.get("memory") or "")


def _entity_links(r: dict) -> list[str]:
    """Best-effort surface of mem0 v2.0.0 native entity links for a row.

    mem0 OSS >= v2.0.0 replaced external graph stores with built-in entity linking.
    The shape varies by version; we look in the obvious places and return a flat
    list of entity strings (empty if the build does not expose them inline)."""
    out: list[str] = []
    for key in ("entities", "entity_links", "links"):
        v = r.get(key)
        if isinstance(v, list):
            for e in v:
                if isinstance(e, str):
                    out.append(e)
                elif isinstance(e, dict):
                    name = e.get("name") or e.get("entity") or e.get("source") or e.get("destination")
                    if name:
                        out.append(str(name))
    md = r.get("metadata") or {}
    for g in md.get("grounded_in") or []:
        out.append(str(g))
    # de-dup preserving order
    seen, uniq = set(), []
    for e in out:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    return uniq


def fetch_rows() -> tuple[list[dict], str | None]:
    """Return (rows, error). rows are the collection's memories for our user_id."""
    try:
        from mem0 import Memory

        mem = Memory.from_config(W._config())
        res = mem.get_all(filters={"user_id": W.USER_ID}, top_k=500)
        rows = _results(res)
        return rows, None
    except Exception as e:  # noqa: BLE001 — read-only view degrades gracefully
        return [], str(e)


def _md_for_rows(rows: list[dict], new_ids: set[str]) -> str:
    """Render the rows as a Markdown table the marked.js card paints."""
    if not rows:
        return "_The `memories` collection is currently empty (no rows for this user)._"
    lines = [
        "| | decision | kind | source | entity links |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        md = r.get("metadata") or {}
        is_new = _row_id(r) in new_ids
        flag = "🟢 **NEW**" if is_new else "·"
        text = (r.get("memory") or r.get("text") or "").strip().replace("\n", " ")
        if len(text) > 160:
            text = text[:157] + "…"
        decision = md.get("decision_id") or md.get("ticket_id") or "—"
        kind = md.get("kind") or "—"
        source = md.get("source") or "—"
        links = ", ".join(_entity_links(r)[:6]) or "—"
        lines.append(
            f"| {flag} | **{decision}** — {text} | `{kind}` | `{source}` | {links} |"
        )
    return "\n".join(lines)


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>mem0 memories — read-only view</title>
<script src="{cdn}"></script>
<style>
  html, body {{ margin: 0; min-height: 100%; background: #0f1721; color: #e7eef6;
                font-family: -apple-system, Segoe UI, Roboto, sans-serif; }}
  #bar {{ background: #131c28; border-bottom: 2px solid #e8543f; padding: 14px 26px;
          display: flex; align-items: center; gap: 16px; position: sticky; top: 0; }}
  #bar .id {{ color: #e8543f; font-weight: 800; font-size: 22px;
              font-family: ui-monospace, Menlo, monospace; }}
  #bar .delta {{ background: #8fd19e22; color: #8fd19e; border: 1px solid #8fd19e55;
                 border-radius: 5px; padding: 3px 10px; font-size: 14px;
                 font-family: ui-monospace, Menlo, monospace; }}
  #bar .src {{ margin-left: auto; color: #9fb3c8; font-size: 13px;
               font-family: ui-monospace, Menlo, monospace; }}
  #doc {{ max-width: 1180px; margin: 0 auto; padding: 22px 36px 60px;
          line-height: 1.55; }}
  #doc table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
  #doc th, #doc td {{ border: 1px solid #25313f; padding: 7px 10px;
                      text-align: left; vertical-align: top; }}
  #doc th {{ background: #1b2735; color: #f0b429; }}
  #doc tr:nth-child(even) td {{ background: #131c28; }}
  #doc code {{ background: #1b2735; padding: 1px 6px; border-radius: 4px;
               font-size: 13px; color: #9fd0ff; }}
  #doc strong {{ color: #e7eef6; }}
</style>
</head>
<body>
  <div id="bar">
    <span class="id">mem0 · memories</span>
    <span class="delta">{delta}</span>
    <span class="src">collection {collection} · user {user} · read-only (no auth)</span>
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


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ap.add_argument("--out", default=str(REPO_ROOT / "recordings" / f"memory_{ts}.html"),
                    help="output HTML path")
    ap.add_argument("--baseline", help="write a JSON baseline (ids+count) of the CURRENT "
                                        "collection to this path (the 'before' snapshot)")
    ap.add_argument("--against", help="a baseline JSON written by --baseline; rows absent "
                                      "from it are highlighted as NEW (the 'after' view)")
    args = ap.parse_args(argv)

    rows, err = fetch_rows()
    ids = [_row_id(r) for r in rows]

    # --baseline mode: persist the current ids/count so a later --against render can
    # diff against it. Still renders a card so the 'before' frame exists for the montage.
    baseline_ids: set[str] = set()
    if args.against:
        try:
            base = json.loads(Path(args.against).read_text())
            baseline_ids = set(base.get("ids", []))
        except Exception as e:  # noqa: BLE001
            print(f"render_memory_card: could not read baseline {args.against} ({e}) — "
                  "rendering without NEW highlighting", file=sys.stderr)

    new_ids = {i for i in ids if i and i not in baseline_ids} if args.against else set()

    if args.baseline:
        Path(args.baseline).parent.mkdir(parents=True, exist_ok=True)
        Path(args.baseline).write_text(
            json.dumps({"ids": ids, "count": len(ids),
                        "collection": W.COLLECTION, "user_id": W.USER_ID,
                        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat()},
                       indent=2),
            encoding="utf-8",
        )

    # Delta badge for the title bar.
    if err:
        delta = "collection unreachable (read-only view)"
        body = (f"_The `memories` collection is currently unreachable: "
                f"`{_html.escape(err)}`._\n\n"
                "_Bring it up: `docker compose up -d mem0-postgres`. This view is "
                "read-only; the load-bearing accumulation proof is "
                "`scripts/assert_memory_accumulates.py`._")
    elif args.against:
        before = len(baseline_ids)
        delta = f"before {before} → after {len(rows)}  (+{len(new_ids)} new)"
        body = _md_for_rows(rows, new_ids)
    else:
        delta = f"{len(rows)} memories"
        body = _md_for_rows(rows, set())

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        HTML.format(cdn=MARKED_CDN, delta=delta, collection=W.COLLECTION,
                    user=W.USER_ID, payload=json.dumps({"body": body})),
        encoding="utf-8",
    )

    receipt = {
        "rendered": True,
        "rows": len(rows),
        "new_rows": len(new_ids),
        "collection": W.COLLECTION,
        "out": str(out.relative_to(REPO_ROOT)) if out.is_relative_to(REPO_ROOT) else str(out),
        "unreachable": bool(err),
    }
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
