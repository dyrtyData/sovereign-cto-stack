#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

#
# preflight.sh — the programmatic form of the Manual Prerequisites gate.
#
# Verifies that the required keys exist in .env and are non-empty (not still the
# .env.example placeholder). Exits non-zero with a clear message if any are missing,
# so later phases halt until the prerequisites are satisfied.
#
# Usage: bash scripts/preflight.sh [path-to-env]   (defaults to ./.env)

set -euo pipefail

ENV_FILE="${1:-.env}"

# Required keys (must be present and non-empty). MEM0_API_KEY / TELEGRAM_HOME_CHANNEL
# are optional and intentionally not listed here.
REQUIRED_KEYS=(
  NOUS_PORTAL_API_KEY
  TELEGRAM_BOT_TOKEN
  TELEGRAM_ALLOWED_USERS
)

# Placeholder values from .env.example that must be replaced with real ones.
PLACEHOLDERS=(
  "sk-nous-xxxxxxxxxxxxxxxxxxxxxxxx"
  "123456789:ABCdef-GhiJklmnoPQRstuvwxyz"
  "123456789"
)

fail() {
  echo "PREFLIGHT FAILED: $1" >&2
  exit 1
}

if [ ! -f "$ENV_FILE" ]; then
  fail "env file '$ENV_FILE' not found. Copy .env.example to .env and fill in real values."
fi

is_placeholder() {
  local value="$1"
  local p
  for p in "${PLACEHOLDERS[@]}"; do
    if [ "$value" = "$p" ]; then
      return 0
    fi
  done
  return 1
}

missing=0
for key in "${REQUIRED_KEYS[@]}"; do
  # Grab the last assignment of the key; strip surrounding quotes and CRs.
  line="$(grep -E "^[[:space:]]*${key}=" "$ENV_FILE" | tail -n 1 || true)"
  value="${line#*=}"
  value="${value%$'\r'}"
  value="${value#\"}"; value="${value%\"}"
  value="${value#\'}"; value="${value%\'}"

  if [ -z "$line" ]; then
    echo "  missing : $key (not set in $ENV_FILE)" >&2
    missing=1
  elif [ -z "$value" ]; then
    echo "  empty   : $key (set but empty in $ENV_FILE)" >&2
    missing=1
  elif is_placeholder "$value"; then
    echo "  default : $key (still the .env.example placeholder)" >&2
    missing=1
  else
    echo "  ok      : $key"
  fi
done

if [ "$missing" -ne 0 ]; then
  fail "one or more required keys are missing/empty/placeholder. See README 'Manual Prerequisites'."
fi

echo "PREFLIGHT OK: all required keys present in $ENV_FILE."
