#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

"""check_doc_links.py — internal markdown link check across docs/** (Phase 5).

Validates that every *internal* (relative) link target referenced from a docs/*.md
file resolves to a real file on disk. This is the public-readiness gate from the
Phase-5 validation: "Markdown link check across docs/** passes (no broken internal
links)."

What it checks:
  - Markdown links `[text](target)` and image links `![alt](target)`.
  - Only INTERNAL targets: skips http(s)://, mailto:, #anchors-only, and tel:.
  - Strips a trailing #anchor from the target before resolving the file part.
  - Resolves relative to the file the link appears in.
  - A link target that is gitignored-but-expected (e.g. ../corpus/) is allowed if the
    DIRECTORY exists; otherwise reported.

Exit 0 if all internal links resolve, 1 otherwise.

Usage:
  python3 scripts/check_doc_links.py            # checks docs/**.md (+ README.md)
  python3 scripts/check_doc_links.py docs/foo.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")


def md_files(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(a) if Path(a).is_absolute() else REPO_ROOT / a for a in argv]
    files = sorted((REPO_ROOT / "docs").rglob("*.md"))
    readme = REPO_ROOT / "README.md"
    if readme.is_file():
        files.append(readme)
    return files


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for m in LINK_RE.finditer(text):
        target = m.group(1).strip()
        # Markdown allows `(url "title")`; drop any title part.
        target = target.split(" ", 1)[0]
        # Markdown autolink syntax inside a link, e.g. `[t](<https://…>)`: the
        # angle brackets are delimiters, not part of the path — strip them so the
        # SKIP_PREFIXES check sees the real scheme.
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        if not target or target.startswith(SKIP_PREFIXES):
            continue
        # Strip a trailing #anchor; we validate the file part only.
        file_part = target.split("#", 1)[0]
        if not file_part:
            continue  # pure in-page anchor
        resolved = (path.parent / file_part).resolve()
        if not (resolved.exists() or resolved.is_dir()):
            errors.append(f"{path.relative_to(REPO_ROOT)} -> {target} (missing: {resolved})")
    return errors


def main(argv: list[str]) -> int:
    files = md_files(argv)
    all_errors: list[str] = []
    checked = 0
    for f in files:
        if not f.is_file():
            print(f"WARN: not a file, skipping: {f}", file=sys.stderr)
            continue
        checked += 1
        all_errors.extend(check_file(f))

    if all_errors:
        print(f"BROKEN INTERNAL LINKS ({len(all_errors)}):", file=sys.stderr)
        for e in all_errors:
            print(f"  {e}", file=sys.stderr)
        print("RESULT: FAIL", file=sys.stderr)
        return 1

    print(f"checked {checked} markdown file(s); all internal links resolve.")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
