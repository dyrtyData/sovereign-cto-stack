#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""assert_pmf_run.py — verify the Phase-4 PMF run + Kanban handoff.

Phase-4 automated checks (outline §"Automated Verification"):

  A. The PMF run wrote a BRIEF artifact, and it contains a textbook CITATION
     string — a `Grounded in: <something>.md` line naming a real corpus source.
  B. The Kanban board (~/.hermes/kanban.db) shows the PMF task transitioning
     ready -> running -> done (the lifecycle events) AND a STRUCTURED HANDOFF row
     in task_runs: status=done / outcome=completed with non-empty summary +
     metadata (the summary+metadata kanban_complete handoff).

Exit 0 on PASS, 1 on FAIL.

Usage:
  python3 scripts/assert_pmf_run.py                 # auto-discover latest brief + task id
  python3 scripts/assert_pmf_run.py --task t_xxxx --brief recordings/pmf_brief_run_<ts>.md
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KANBAN_DB = Path.home() / ".hermes" / "kanban.db"

GROUNDED_RE = re.compile(r"Grounded in:[^\n]*?([A-Za-z0-9_\-]+\.md)", re.IGNORECASE)
# corpus source files that actually exist locally (the real grounding texts)
CORPUS_DIR = REPO_ROOT / "corpus"


def _latest_brief() -> Path | None:
    briefs = sorted(
        REPO_ROOT.glob("recordings/pmf_brief_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return briefs[0] if briefs else None


def _last_task_id() -> str | None:
    f = REPO_ROOT / "recordings" / ".last_pmf_task_id"
    if f.is_file():
        return f.read_text().strip() or None
    return None


def _corpus_sources() -> set[str]:
    if CORPUS_DIR.is_dir():
        return {p.name.lower() for p in CORPUS_DIR.glob("*.md")}
    return set()


def check_brief(brief: Path) -> bool:
    print(f"brief artifact: {brief}")
    if not brief.is_file():
        print("FAIL: brief artifact not found"); return False
    text = brief.read_text(errors="ignore")
    sources = {s.lower() for s in GROUNDED_RE.findall(text)}
    if not sources:
        print("FAIL: no 'Grounded in: ...*.md' citation string in the brief"); return False
    print(f"PASS: brief contains textbook citation(s): {sorted(sources)}")

    corpus = _corpus_sources()
    if corpus:
        real = sources & corpus
        if real:
            print(f"PASS: at least one citation maps to a real corpus text: {sorted(real)}")
            return True
        print(f"FAIL: none of the cited sources exist in corpus/ ({sorted(sources)})")
        return False
    # corpus/ not present (clean clone) — citation string presence is enough
    print("NOTE: corpus/ not present locally; accepting citation-string presence")
    return True


def check_kanban(task_id: str | None) -> bool:
    if not KANBAN_DB.is_file():
        print(f"FAIL: kanban DB not found at {KANBAN_DB}"); return False
    con = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        if task_id is None:
            # newest PMF task on the board
            row = con.execute(
                "SELECT id,title,status FROM tasks WHERE title LIKE '[PMF]%' "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                print("FAIL: no [PMF] task found on the Kanban board"); return False
            task_id = row["id"]
        task = con.execute(
            "SELECT id,title,status FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        if not task:
            print(f"FAIL: task {task_id} not found"); return False
        print(f"kanban task: {task['id']} — {task['title']}  (status={task['status']})")

        ok = True
        # final status DONE
        if task["status"] == "done":
            print("PASS: task status is 'done'")
        else:
            print(f"FAIL: task status is '{task['status']}', expected 'done'"); ok = False

        # lifecycle events: created (ready) -> claimed (running) -> completed (done)
        kinds = [r["kind"] for r in con.execute(
            "SELECT kind FROM task_events WHERE task_id=? ORDER BY id", (task_id,)
        ).fetchall()]
        print(f"lifecycle events: {kinds}")
        need = ["created", "claimed", "completed"]
        if all(k in kinds for k in need) and \
                kinds.index("created") < kinds.index("claimed") < kinds.index("completed"):
            print("PASS: ready -> running -> done transition recorded "
                  "(created -> claimed -> completed)")
        else:
            print(f"FAIL: lifecycle did not progress created->claimed->completed ({kinds})")
            ok = False

        # structured handoff row in task_runs
        run = con.execute(
            "SELECT status,outcome,summary,metadata FROM task_runs "
            "WHERE task_id=? ORDER BY id DESC LIMIT 1", (task_id,)
        ).fetchone()
        if not run:
            print("FAIL: no task_runs row (no handoff recorded)"); return False
        print(f"handoff run: status={run['status']} outcome={run['outcome']}")
        if run["status"] == "done" and (run["outcome"] in (None, "completed")):
            print("PASS: closing run is done/completed")
        else:
            print(f"FAIL: closing run not done/completed "
                  f"(status={run['status']}, outcome={run['outcome']})"); ok = False
        if run["summary"]:
            print(f"PASS: structured handoff summary present -> "
                  f"{run['summary'][:120]!r}")
        else:
            print("FAIL: handoff summary empty"); ok = False
        if run["metadata"]:
            try:
                md = json.loads(run["metadata"])
                print(f"PASS: structured handoff metadata present -> keys={sorted(md)}")
            except (TypeError, ValueError):
                print(f"PASS: handoff metadata present (non-JSON) -> {run['metadata'][:80]!r}")
        else:
            print("FAIL: handoff metadata empty"); ok = False
        return ok
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", help="Kanban task id (default: auto-discover latest [PMF])")
    ap.add_argument("--brief", help="brief artifact path (default: latest recordings/pmf_brief_*.md)")
    args = ap.parse_args()

    brief = Path(args.brief) if args.brief else _latest_brief()
    task_id = args.task or _last_task_id()

    if brief is None:
        print("FAIL: no PMF brief artifact found (run scripts/pmf_kanban_run.sh)")
        return 1

    print("--- A. brief artifact + citation ---")
    a = check_brief(brief)
    print("--- B. kanban lifecycle + handoff ---")
    b = check_kanban(task_id)

    print("RESULT:", "PASS" if (a and b) else "FAIL")
    return 0 if (a and b) else 1


if __name__ == "__main__":
    raise SystemExit(main())
