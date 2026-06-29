#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.
"""apply_license_headers.py — keep the AGPLv3 attribution header on every source file.

The repo is AGPL-3.0 (see LICENSE). AGPL §4–§5 only *protect* copyright notices that are
actually PRESENT in the work — anyone who copies or forks a file is legally required to keep
the notices it carries, but a file with no header carries nothing to preserve. So every code
file gets a 3-line SPDX header asserting `Copyright (C) 2026 dyrtyData`; that is what makes a
duplicated file credit the author.

This script is the single source of truth for that header. It runs in two modes:

  apply  (default) — insert the header into any tracked .py/.sh file under the code dirs that
                     is missing it (idempotent; placed AFTER the shebang, before everything
                     else, so `uv`'s PEP 723 inline-script blocks are unaffected).
  --check          — exit non-zero (and list offenders) if any in-scope file is missing the
                     header. Used by .githooks/pre-commit and by humans/agents in CI.
  --check --staged — restrict --check to files git has staged (the fast pre-commit path).

Usage:
  python3 scripts/apply_license_headers.py            # apply to all in-scope files
  python3 scripts/apply_license_headers.py --check    # verify all in-scope files (CI)
  python3 scripts/apply_license_headers.py --check --staged   # verify staged files (hook)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The canonical attribution header (comment syntax is `#` for both Python and shell).
SPDX_LINE = "# SPDX-License-Identifier: AGPL-3.0-or-later"
HEADER_LINES = [
    SPDX_LINE,
    "# Copyright (C) 2026 dyrtyData",
    "# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.",
]

# Code directories whose .py/.sh files must carry the header. Docs, markdown skills, vendored
# corpus, and gitignored artifacts are intentionally out of scope.
SCOPE_DIRS = ("scripts", "hermes", "egress", "recorder")
SCOPE_SUFFIXES = (".py", ".sh")

# The marker we look for to decide a file already has the header (cheap + unambiguous).
MARKER = "SPDX-License-Identifier"


def _tracked_in_scope() -> list[Path]:
    """Every git-tracked .py/.sh file under the code dirs."""
    out = subprocess.run(
        ["git", "ls-files", *[f"{d}/**" for d in SCOPE_DIRS], *SCOPE_DIRS],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    files = []
    for rel in out:
        p = REPO_ROOT / rel
        if p.suffix in SCOPE_SUFFIXES and p.is_file():
            files.append(p)
    return sorted(set(files))


def _staged_in_scope() -> list[Path]:
    """Staged (added/copied/modified) .py/.sh files under the code dirs."""
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    files = []
    for rel in out:
        p = REPO_ROOT / rel
        if (
            p.suffix in SCOPE_SUFFIXES
            and p.is_file()
            and any(rel == d or rel.startswith(d + "/") for d in SCOPE_DIRS)
        ):
            files.append(p)
    return sorted(set(files))


def has_header(path: Path) -> bool:
    """True if the file already carries the SPDX header near the top."""
    try:
        head = path.read_text(errors="replace").splitlines()[:10]
    except OSError:
        return False
    return any(MARKER in line for line in head)


def apply_header(path: Path) -> bool:
    """Insert the header (after a shebang if present). Returns True if the file was changed."""
    if has_header(path):
        return False
    text = path.read_text()
    lines = text.split("\n")
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1  # keep the shebang on line 1
    block = HEADER_LINES + ([""] if (len(lines) > insert_at and lines[insert_at].strip()) else [])
    new_lines = lines[:insert_at] + block + lines[insert_at:]
    path.write_text("\n".join(new_lines))
    return True


def main(argv: list[str]) -> int:
    check = "--check" in argv
    staged = "--staged" in argv
    files = _staged_in_scope() if staged else _tracked_in_scope()

    if check:
        missing = [p for p in files if not has_header(p)]
        if missing:
            print("FAIL: these source files are missing the AGPLv3 attribution header:",
                  file=sys.stderr)
            for p in missing:
                print(f"  - {p.relative_to(REPO_ROOT)}", file=sys.stderr)
            print("\nFix: python3 scripts/apply_license_headers.py", file=sys.stderr)
            return 1
        print(f"OK: all {len(files)} in-scope source files carry the AGPLv3 header.")
        return 0

    changed = [p for p in files if apply_header(p)]
    for p in changed:
        print(f"header added: {p.relative_to(REPO_ROOT)}")
    print(f"\n{len(changed)} file(s) updated; {len(files) - len(changed)} already had the header.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
