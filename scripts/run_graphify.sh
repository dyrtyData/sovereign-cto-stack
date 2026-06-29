#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

#
# run_graphify.sh — map the tech-debt audit target with graphify (Phase 3, hero).
#
# Clones GoogleCloudPlatform/microservices-demo (Online Boutique) into
# workspaces/ (gitignored — we never deploy it; K8s-only upstream, source-graph
# ONLY) and runs a headless graphify extraction over its src/ tree, producing:
#
#   graphify-out/graph.json       NetworkX export (nodes + edges, source_file refs)
#   graphify-out/GRAPH_REPORT.md  "god nodes" / high-connectivity hubs report
#   graphify-out/graph.html       interactive vis.js visualization
#
# The known topology (research §13): the static call-graph sees the gRPC client
# stubs each service opens. `frontend` opens 7 outbound gRPC connections and
# `checkoutservice` opens 6 — the two high-degree coupling hubs. The auditor
# profile reads this graph, consults query_cto_knowledge, and files a
# [Brownfield] Linear ticket naming the concrete src/<service>/ files.
#
# AST extraction is fully local (tree-sitter, no API key). The semantic LLM
# layer is OPTIONAL and skipped by default here (--no-cluster keeps the run
# deterministic and offline for CI / topology assertions). Set GRAPHIFY_DEEP=1
# to add the semantic/community layer via a configured backend.
#
# Usage:
#   bash scripts/run_graphify.sh                 # clone (if needed) + extract
#   GRAPHIFY_DEEP=1 bash scripts/run_graphify.sh # also run the semantic layer
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACES="${WORKSPACES_DIR:-$REPO_ROOT/workspaces}"
TARGET_DIR="$WORKSPACES/microservices-demo"
TARGET_REPO="${TARGET_REPO:-https://github.com/GoogleCloudPlatform/microservices-demo.git}"
OUT_DIR="$REPO_ROOT/graphify-out"
# Analyze the source tree only (each src/<service>/ is a self-contained dir).
SRC_PATH="$TARGET_DIR/src"

command -v graphify >/dev/null 2>&1 || {
  echo "run_graphify: graphify not found. Install: uv tool install graphifyy" >&2
  exit 1
}
command -v git >/dev/null 2>&1 || { echo "run_graphify: git not found" >&2; exit 1; }

mkdir -p "$WORKSPACES"

# --- 1. Clone the audit target (static analysis only; never deployed) ---
if [ -d "$TARGET_DIR/.git" ]; then
  echo "=== target present: $TARGET_DIR (skipping clone) ==="
else
  echo "=== cloning $TARGET_REPO -> $TARGET_DIR (depth 1, source-graph only) ==="
  git clone --depth 1 "$TARGET_REPO" "$TARGET_DIR"
fi

[ -d "$SRC_PATH" ] || { echo "run_graphify: expected source tree at $SRC_PATH" >&2; exit 1; }

# --- 1b. Prune non-code assets so this is a "code-only corpus" (no LLM key) ---
# graphify demands a semantic-extraction backend (API key) the moment it sees
# docs/images. Online Boutique's src/ ships per-service README.md files and the
# frontend's large static asset tree (images/icons/products) — none of which is
# part of the call-graph topology we audit. Removing them keeps the default run
# fully local/offline and deterministic. (We never deploy this clone, so pruning
# its static assets is harmless; re-clone to restore.) GRAPHIFY_DEEP=1 keeps a
# backend anyway, so the prune is unconditional and only affects irrelevant files.
echo "=== pruning non-code assets from the clone (source-graph only) ==="
find "$SRC_PATH" -type d \( -name static -o -name node_modules \) -prune -exec rm -rf {} + 2>/dev/null || true
find "$SRC_PATH" -type f \
  \( -iname '*.md' -o -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \
     -o -iname '*.gif' -o -iname '*.svg' -o -iname '*.ico' -o -iname '*.webp' \
     -o -iname '*.html' -o -iname '*.txt' \) \
  -delete 2>/dev/null || true

# --- 2. Extract the code graph (AST/tree-sitter; semantic layer optional) ---
echo "=== graphify extract: $SRC_PATH -> $OUT_DIR ==="
EXTRA=()
if [ "${GRAPHIFY_DEEP:-0}" = "1" ]; then
  echo "  (GRAPHIFY_DEEP=1: including semantic + community layer)"
  # A backend (and its API key) is only needed for the semantic/community layer.
  EXTRA+=(--mode deep --backend "${GRAPHIFY_BACKEND:-deepseek}")
else
  # Deterministic, offline, fast: AST call/import graph only — no LLM, no API
  # key. This is all the topology assertion (frontend=7, checkoutservice=6
  # outbound edges) needs.
  EXTRA+=(--no-cluster)
fi

# --out writes <DIR>/graphify-out/ ; point it at the repo root so output lands
# in graphify-out/ exactly as the validation expects.
graphify extract "$SRC_PATH" --out "$REPO_ROOT" "${EXTRA[@]}" || {
  rc=$?
  echo "run_graphify: graphify extract failed (rc=$rc)" >&2
  exit "$rc"
}

[ -f "$OUT_DIR/graph.json" ] || {
  echo "run_graphify: extraction did not produce $OUT_DIR/graph.json" >&2
  exit 1
}

# --- 3. Generate GRAPH_REPORT.md + graph.html ---
# `--no-cluster` writes only graph.json. Re-run clustering (with --no-label so it
# needs no LLM) to also emit the "god nodes" report and the interactive viz the
# outline requires (graphify-out/{GRAPH_REPORT.md, graph.html}). GRAPHIFY_DEEP=1
# already produced all three, so only do this in the default (AST-only) path.
if [ "${GRAPHIFY_DEEP:-0}" != "1" ]; then
  echo "=== cluster-only (no LLM): GRAPH_REPORT.md + graph.html ==="
  graphify cluster-only "$REPO_ROOT" --no-label 2>&1 | tail -5 || {
    echo "run_graphify: cluster-only failed (graph.json still valid)" >&2
  }
fi

# --- 4. Derive the SERVICE-LEVEL coupling topology (deterministic) ---
# The raw graphify graph is file/symbol-level; the audit's headline signal is
# service-to-service coupling — how many distinct gRPC backends each service
# dials. scripts/service_topology.py scans the gRPC client wiring in the cloned
# source and writes graphify-out/service-coupling.json with per-service outbound
# degree (research §13: frontend=7, checkoutservice=6). This is the hard signal
# the auditor and the topology assertion read.
echo "=== deriving service-level coupling (service_topology.py) ==="
python3 "$REPO_ROOT/scripts/service_topology.py" \
  --src "$SRC_PATH" --out "$OUT_DIR/service-coupling.json"

# --- 5. Render a LEGIBLE service-level graph for humans / screen capture ---
# graphify's graph.html is the raw file/symbol graph (hundreds of nodes) — too
# dense to read. render_service_graph.py turns the ~11-node service topology into
# a clean, standalone HTML (directed gRPC edges, frontend/checkout emphasized) that
# opens in any browser and is legible for the Phase-4 recording.
echo "=== rendering legible service graph (render_service_graph.py) ==="
python3 "$REPO_ROOT/scripts/render_service_graph.py" \
  --in "$OUT_DIR/service-coupling.json" --out "$OUT_DIR/service-graph.html"

echo "=== graphify-out artifacts ==="
ls -la "$OUT_DIR" | sed -n '1,20p'
echo "run_graphify: OK — graph at $OUT_DIR/graph.json"
