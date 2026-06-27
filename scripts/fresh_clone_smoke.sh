#!/usr/bin/env bash
#
# fresh_clone_smoke.sh — prove the public-clone path works (Phase 5).
#
# Simulates what a stranger does after `git clone`: copy .env.example to .env and run
# the preflight gate. Asserts the two halves of the gate:
#
#   (a) with the .env.example PLACEHOLDERS in place, preflight HALTS (non-zero) — the
#       prerequisites gate refuses to proceed without real keys;
#   (b) with TEST STUB values substituted for the required keys, preflight PASSES (0)
#       — a correctly-filled .env unblocks the build.
#
# It does NOT touch the repo's real .env. It works in a throwaway temp dir that mirrors
# a fresh clone (git archive of HEAD by default; or a real `git clone` of the repo with
# CLONE=1). No secrets are used — only obvious non-secret stub strings.
#
# Usage:
#   bash scripts/fresh_clone_smoke.sh          # archive HEAD into a temp dir (fast)
#   CLONE=1 bash scripts/fresh_clone_smoke.sh  # full `git clone file://<repo>` of HEAD
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/scs-smoke.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

log() { echo "=== fresh_clone_smoke: $* ==="; }

# --- materialize a "fresh clone" (tracked files only — never the real .env) ---
if [ "${CLONE:-0}" = "1" ]; then
  log "git clone (HEAD) -> $TMP/repo"
  git clone -q "file://$REPO_ROOT" "$TMP/repo"
  CLONE_DIR="$TMP/repo"
else
  log "git archive HEAD -> $TMP/repo (tracked files only)"
  mkdir -p "$TMP/repo"
  git -C "$REPO_ROOT" archive HEAD | tar -x -C "$TMP/repo"
  CLONE_DIR="$TMP/repo"
fi

cd "$CLONE_DIR"

[ -f .env.example ] || { echo "smoke: .env.example missing from clone" >&2; exit 1; }
[ -f scripts/preflight.sh ] || { echo "smoke: scripts/preflight.sh missing from clone" >&2; exit 1; }
# the real .env must NOT be present in a clean clone (it is gitignored)
if [ -f .env ]; then echo "smoke: a clone unexpectedly contains .env (should be gitignored)" >&2; exit 1; fi

# --- (a) placeholders in place -> preflight HALTS -----------------------------
log "(a) cp .env.example .env (placeholders) -> preflight must HALT"
cp .env.example .env
if bash scripts/preflight.sh >/dev/null 2>&1; then
  echo "smoke: FAIL — preflight passed with placeholder .env (should have halted)" >&2
  exit 1
fi
log "(a) OK — preflight correctly halted on placeholder keys"

# --- (b) test stubs for required keys -> preflight PASSES ---------------------
log "(b) substitute non-secret test stubs for required keys -> preflight must PASS"
cat > .env <<'STUB'
# Non-secret test stubs (fresh_clone_smoke.sh) — NOT real credentials.
NOUS_PORTAL_API_KEY=sk-nous-SMOKE-TEST-STUB-not-a-real-key
TELEGRAM_BOT_TOKEN=999999999:SMOKE-TEST-STUB-not-a-real-token
TELEGRAM_ALLOWED_USERS=999999999
STUB
if ! bash scripts/preflight.sh >/dev/null 2>&1; then
  echo "smoke: FAIL — preflight halted even with all required keys present" >&2
  bash scripts/preflight.sh || true
  exit 1
fi
log "(b) OK — preflight passed with a correctly-filled .env"

echo "RESULT: PASS — fresh-clone path works (gate halts on placeholders, passes when filled)"
