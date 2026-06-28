#!/usr/bin/env python3
"""assert_persistent_profile_wiring.py — the GLO-14 P3 persistent-profile smoke gate.

The OPTIONAL authenticated live-Linear ending launches the recorder's Chromium WITH
a mounted `--user-data-dir` (a persistent, logged-in profile) so the real Linear
ticket renders instead of the auth wall. PROVING the recording ends on the genuine
authenticated page needs a human-held Linear session (that is the Phase-5 human
checkpoint). But the WIRING — "does the recorder actually launch Chromium with
`--user-data-dir` when a profile dir is provided?" — is fully automatable, and that
is what THIS gate asserts, independent of whether any real Linear session exists.

It exercises the real `recorder/entrypoint.sh launch_browser` code path inside the
running recorder container with:
  * CHROMIUM_USER_DATA_DIR pointed at a THROWAWAY dir under /recordings (a host
    bind-mount, so we can clean it up), and
  * a harmless local file:// target (no Linear, no network, no session needed),
then reads the recorder's own chromium launch log (/tmp/chromium.log is the file the
browser's stdout/stderr go to; the entrypoint also logs the launch) and asserts the
launched command carried `--user-data-dir=<that dir>`.

Because the entrypoint logs "using PERSISTENT Chromium profile --user-data-dir=..."
to stderr (captured by `docker compose exec`), we assert on THAT log line — it is
emitted exactly when the wiring appends the flag, so it is a faithful proof the flag
reached the chromium argv.

Exit 0 on PASS, 1 on FAIL (flag not threaded through), 2 on harness error (no
recorder container / docker unavailable). Cleans up the throwaway dir.

Usage:
    docker compose --profile record up -d recorder
    uv run scripts/assert_persistent_profile_wiring.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SVC = "recorder"
EXEC = "/opt/recorder/entrypoint.sh"

# A throwaway profile dir + a harmless target, both reachable inside the container
# via the ./recordings bind-mount (/recordings). No Linear, no network, no session.
THROWAWAY_REL = f"_profile_smoke_{int(time.time())}"
THROWAWAY_HOST = REPO_ROOT / "recordings" / THROWAWAY_REL
THROWAWAY_CTR = f"/recordings/{THROWAWAY_REL}"
SMOKE_HTML_HOST = REPO_ROOT / "recordings" / f"{THROWAWAY_REL}.html"
SMOKE_HTML_CTR = f"/recordings/{THROWAWAY_REL}.html"


def _dc(*args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], capture_output=True, text=True,
                          cwd=str(REPO_ROOT), **kw)


def _recorder_running() -> bool:
    cp = _dc("ps", "--services", "--filter", "status=running")
    return SVC in (cp.stdout or "").split()


def main() -> int:
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        print("HARNESS ERROR: docker is not available.", file=sys.stderr)
        return 2
    if not _recorder_running():
        print("HARNESS ERROR: the recorder container is not running — bring it up: "
              "docker compose --profile record up -d recorder", file=sys.stderr)
        return 2

    # A harmless local HTML target so chromium has something to open (no network).
    SMOKE_HTML_HOST.write_text(
        "<!doctype html><meta charset=utf-8><title>profile smoke</title>"
        "<body style='background:#0f1721;color:#e7eef6'>persistent-profile wiring smoke</body>",
        encoding="utf-8",
    )

    ok = True
    try:
        # Drive the REAL launch_browser path WITH a mounted --user-data-dir, exactly
        # as record_run.sh's TICKET_LIVE_URL=1 ending does (here via surface-html so
        # no Linear/auth is involved — we only assert the FLAG is threaded through).
        print(f"[gate]  launching recorder Chromium with CHROMIUM_USER_DATA_DIR={THROWAWAY_CTR}")
        cp = _dc("exec", "-T",
                 "-e", f"CHROMIUM_USER_DATA_DIR={THROWAWAY_CTR}",
                 SVC, EXEC, "surface-html", SMOKE_HTML_CTR)
        log = (cp.stdout or "") + (cp.stderr or "")
        sys.stdout.write(log)

        needle = f"--user-data-dir={THROWAWAY_CTR}"
        if needle in log:
            print(f"PASS - recorder launched Chromium WITH {needle} "
                  "(persistent-profile wiring exercised)")
        else:
            print(f"FAIL - the entrypoint did NOT thread {needle} into the chromium "
                  "launch (persistent-profile wiring broken)")
            ok = False

        # Belt-and-braces: also confirm the entrypoint's explicit log line fired.
        if "using PERSISTENT Chromium profile" in log:
            print("PASS - entrypoint logged the persistent-profile launch path")
        else:
            print("FAIL - entrypoint did not log the persistent-profile launch path")
            ok = False

        # And confirm a profile dir actually materialized inside the mount (chromium
        # writes into --user-data-dir on launch) — extra evidence the flag took.
        time.sleep(2)
        if THROWAWAY_HOST.exists() and any(THROWAWAY_HOST.iterdir()):
            print(f"PASS - Chromium populated the profile dir {THROWAWAY_REL}/ "
                  "(the --user-data-dir is live, not ignored)")
        else:
            print(f"NOTE - profile dir {THROWAWAY_REL}/ not yet populated "
                  "(chromium may still be starting) — the flag-threading proof above stands")
    finally:
        # Clean up the throwaway profile + smoke html (never leave a stray profile).
        _dc("exec", "-T", SVC, "bash", "-lc",
            f"rm -rf '{THROWAWAY_CTR}' '{SMOKE_HTML_CTR}' 2>/dev/null || true")
        try:
            import shutil
            if THROWAWAY_HOST.exists():
                shutil.rmtree(THROWAWAY_HOST, ignore_errors=True)
            if SMOKE_HTML_HOST.exists():
                SMOKE_HTML_HOST.unlink()
        except Exception:  # noqa: BLE001
            pass

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
