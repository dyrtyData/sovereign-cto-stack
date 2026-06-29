#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 dyrtyData
# Part of sovereign-cto-stack — licensed under the GNU AGPL v3.0; see LICENSE.

#
# convert_corpus.sh — build the CTO knowledge corpus (Phase 2).
#
# Converts the textbook source folders to Markdown into corpus/ (gitignored —
# copyrighted content stays local; this script IS tracked). Two engines:
#
#   *.pdf   -> docling (Apple MPS acceleration, ~0.2-0.3s/page) via the
#              embedded Python below (mirrors the docling-pdf skill batch template).
#   *.epub  -> pandoc (docling has no EPUB support; research §15).
#
# Dedupe rule: prefer the PDF when both a PDF and an EPUB of the same title
# exist (design Q5). EPUB-only titles still convert.
#
# Idempotent / resumable: a source is skipped if its corpus/<slug>.md already
# exists and is non-empty. The docling pass over many large PDFs is long-running
# (expected) — re-running picks up where it left off.
#
# Usage:
#   bash scripts/convert_corpus.sh                 # all source folders
#   CORPUS_SRC_ROOT=/some/dir bash scripts/convert_corpus.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${CORPUS_OUT_DIR:-$REPO_ROOT/corpus}"
SRC_ROOT="${CORPUS_SRC_ROOT:-$HOME/Downloads/UTM-shared}"
SRC_DIRS=("Growth" "System Design" "Org Design")

mkdir -p "$OUT_DIR"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "convert_corpus: pandoc not found (needed for EPUB). Install: brew install pandoc" >&2
  exit 1
fi

# slugify: lower-case, keep the leading title token before the first separator
# punctuation, collapse to [a-z0-9-]. Used so a PDF and its EPUB twin map to the
# SAME corpus slug -> the PDF (converted first) wins, the EPUB is skipped.
slugify() {
  # $1 = source basename WITHOUT extension
  local name="$1"
  # take everything up to the first '_' / ':' / '{' / '[' / '(' / '-' run that
  # typically begins the metadata tail; keep it simple and stable.
  name="${name%%_*}"
  name="${name%%\{*}"
  name="${name%%\[*}"
  name="${name%%(*}"
  printf '%s' "$name" \
    | tr '[:upper:]' '[:lower:]' \
    | tr -cs 'a-z0-9' '-' \
    | sed -E 's/^-+//; s/-+$//'
}

target_md() { printf '%s/%s.md' "$OUT_DIR" "$(slugify "$1")"; }

nonempty_md() { [ -f "$1" ] && [ -s "$1" ]; }

converted=0
skipped=0
pdf_failed=0   # a PDF that docling couldn't do (may be covered by its EPUB twin)
failed=0       # a source title with NO usable .md at all (hard failure)

# --- PDF pass first (so PDF wins the dedupe over a same-title EPUB) ---
echo "=== PDF pass (docling, MPS) ==="
PDFS=()
for d in "${SRC_DIRS[@]}"; do
  src="$SRC_ROOT/$d"
  [ -d "$src" ] || { echo "  (skip missing dir: $src)"; continue; }
  while IFS= read -r -d '' f; do PDFS+=("$f"); done \
    < <(find "$src" -maxdepth 1 -type f -iname '*.pdf' -print0)
done

# Build a newline-delimited list of PDF paths whose .md is missing, for the
# docling Python batch (it reuses one DocumentConverter for speed).
PDF_TODO=()
for f in "${PDFS[@]:-}"; do
  [ -n "$f" ] || continue
  base="$(basename "$f")"; stem="${base%.*}"
  md="$(target_md "$stem")"
  if nonempty_md "$md"; then
    echo "  skip (exists): $base -> $(basename "$md")"
    skipped=$((skipped + 1))
  else
    PDF_TODO+=("$f|$md")
  fi
done

# Embedded single-file docling worker. Run ONE PDF per `uv run` subprocess so a
# docling crash/OOM on a large PDF (observed on big multi-agent textbooks) only
# costs that one book — the batch continues and stays resumable. argv: src dst.
DOCLING_WORKER="$(mktemp -t docling_one.XXXXXX.py)"
trap 'rm -f "$DOCLING_WORKER"' EXIT
cat > "$DOCLING_WORKER" <<'PY'
import sys, time
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice,
)
from docling.datamodel.base_models import InputFormat

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
accel = AcceleratorOptions(num_threads=8, device=AcceleratorDevice.MPS)
opts = PdfPipelineOptions()
opts.accelerator_options = accel
# OCR off: these are digital (born-text) textbooks, so OCR adds nothing and the
# RapidOCR engine bundled with docling 2.68 fails to initialize on this host
# ("Unsupported configuration: torch.PP-OCRv6.det.small"). Text + table extraction
# is all we need; this is also much faster.
opts.do_ocr = False
opts.do_table_structure = True
conv = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
)
t0 = time.time()
doc = conv.convert(str(src))
md = doc.document.export_to_markdown()
if not md.strip():
    raise RuntimeError("docling produced empty markdown")
dst.write_text(md, encoding="utf-8")
pages = len(doc.document.pages) if hasattr(doc.document, "pages") else 0
dt = time.time() - t0
rate = f"{dt/pages:.2f}s/pg" if pages else f"{dt:.1f}s"
print(f"    OK {pages} pages in {dt:.1f}s ({rate}) -> {dst.name}", flush=True)
PY

n_pdf="${#PDF_TODO[@]}"
i=0
for pair in "${PDF_TODO[@]:-}"; do
  [ -n "$pair" ] || continue
  i=$((i + 1))
  src="${pair%%|*}"; md="${pair#*|}"
  echo "[$i/$n_pdf] docling: $(basename "$src")"
  drc=0
  uv run --quiet --with docling python3 "$DOCLING_WORKER" "$src" "$md" || drc=$?
  if [ "$drc" -eq 0 ] && nonempty_md "$md"; then
    converted=$((converted + 1))
  else
    echo "    FAIL docling (rc=$drc): $(basename "$src") — will try EPUB twin if present" >&2
    # leave no partial/empty .md so the EPUB pass can fill in and re-runs resume
    [ -f "$md" ] && [ ! -s "$md" ] && rm -f "$md"
    pdf_failed=1
  fi
done

# --- EPUB pass (pandoc) — only for titles with no PDF-derived .md yet ---
echo "=== EPUB pass (pandoc) ==="
for d in "${SRC_DIRS[@]}"; do
  src="$SRC_ROOT/$d"
  [ -d "$src" ] || continue
  while IFS= read -r -d '' f; do
    base="$(basename "$f")"; stem="${base%.*}"
    md="$(target_md "$stem")"
    if nonempty_md "$md"; then
      echo "  skip (PDF twin or already converted): $base -> $(basename "$md")"
      skipped=$((skipped + 1))
      continue
    fi
    echo "  pandoc: $base -> $(basename "$md")"
    if pandoc "$f" -f epub -t gfm -o "$md" 2>/dev/null && nonempty_md "$md"; then
      converted=$((converted + 1))
    else
      echo "    FAIL pandoc: $base" >&2
      [ -f "$md" ] && [ ! -s "$md" ] && rm -f "$md"
      failed=1
    fi
  done < <(find "$src" -maxdepth 1 -type f -iname '*.epub' -print0)
done

# --- completeness check: every unique source title (by slug) must have a .md ---
# A PDF that docling failed is only a HARD failure if no EPUB twin produced the
# same-slug .md. Build the set of expected slugs from all sources, then verify.
echo "=== completeness check ==="
declare -A EXPECTED=()
for d in "${SRC_DIRS[@]}"; do
  src="$SRC_ROOT/$d"
  [ -d "$src" ] || continue
  while IFS= read -r -d '' f; do
    base="$(basename "$f")"; stem="${base%.*}"
    EXPECTED["$(slugify "$stem")"]=1
  done < <(find "$src" -maxdepth 1 -type f \( -iname '*.pdf' -o -iname '*.epub' \) -print0)
done

missing_titles=0
for slug in "${!EXPECTED[@]}"; do
  md="$OUT_DIR/$slug.md"
  if ! nonempty_md "$md"; then
    echo "  MISSING : $slug.md (no PDF or EPUB produced a usable file)" >&2
    missing_titles=$((missing_titles + 1))
    failed=1
  fi
done
expected_count="${#EXPECTED[@]}"

echo "=== corpus conversion summary ==="
echo "  converted this run : $converted"
echo "  skipped (existing/twin) : $skipped"
echo "  PDFs docling could not do (EPUB-covered or missing) : $pdf_failed"
total_md="$(find "$OUT_DIR" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
echo "  unique source titles expected : $expected_count"
echo "  total .md in corpus/ : $total_md"

if [ "$failed" -ne 0 ]; then
  echo "convert_corpus: INCOMPLETE — $missing_titles title(s) have no usable .md (see above)." >&2
  exit 1
fi
echo "convert_corpus: OK — every source title has a non-empty corpus/*.md."
