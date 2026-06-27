#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = [
#   "fastmcp>=3,<4",
#   "lancedb>=0.13",
#   "sentence-transformers>=3,<6",
#   "pyarrow>=15",
# ]
# ///
"""CTO knowledge RAG brain — local Vector MCP sidecar (Phase 2).

Indexes the converted textbook corpus (Markdown in /corpus, gitignored) and
serves a single MCP tool, `query_cto_knowledge`, over HTTP at /mcp. The agent
(Hermes) is instructed to consult it before every CTO function and cite the
grounding text(s) it returns (design Q5; hermes/AGENTS.md standing rule #1).

Design choices (mirror scripts/mem0_roundtrip.py for consistency, zero external keys):
- Embeddings: local sentence-transformers all-MiniLM-L6-v2 (384 dims) — no API key.
- Vector store: LanceDB (file-based, embedded) at $RAG_DB_DIR (default ./.lancedb,
  or /data in the container). Self-contained; no second DB service to run.
- Chunking: heading-aware, then fixed-size with overlap, so each chunk carries a
  stable `source_file` citation back to the corpus Markdown it came from.

Run locally:
    uv run rag/server.py --ingest      # build/refresh the index from CORPUS_DIR
    uv run rag/server.py               # serve MCP + HTTP on :8080

Run in docker: see rag/Dockerfile + the `rag-sidecar` compose service.

HTTP surface (for curl-based validation + health checks):
    GET  /health                 -> {"status": "...", "chunks": N, "sources": M}
    POST /ingest                 -> (re)build the index from CORPUS_DIR
    POST /search  {"query": "...", "k": 5}
                                 -> ranked chunks, each with source_file citation
MCP surface:
    POST /mcp  (Streamable HTTP)  tool: query_cto_knowledge(query, k=5)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

# --- configuration (env-overridable, sane container + local defaults) ---
CORPUS_DIR = Path(os.environ.get("CORPUS_DIR", "/corpus"))
if not CORPUS_DIR.exists():
    # local default: repo-root/corpus relative to this file (rag/ -> ..)
    _local = Path(__file__).resolve().parent.parent / "corpus"
    if _local.exists():
        CORPUS_DIR = _local

DB_DIR = Path(os.environ.get("RAG_DB_DIR", "/data"))
if not DB_DIR.parent.exists() and str(DB_DIR) == "/data":
    DB_DIR = Path(__file__).resolve().parent / ".lancedb"

TABLE_NAME = os.environ.get("RAG_TABLE", "cto_knowledge")
EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_DIMS = 384  # all-MiniLM-L6-v2
HOST = os.environ.get("RAG_HOST", "0.0.0.0")
PORT = int(os.environ.get("RAG_PORT", "8080"))
MCP_PATH = os.environ.get("RAG_MCP_PATH", "/mcp")

CHUNK_CHARS = int(os.environ.get("RAG_CHUNK_CHARS", "1200"))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "150"))
DEFAULT_K = int(os.environ.get("RAG_DEFAULT_K", "5"))


# --- embeddings (lazy: model load is slow; only once) ---
@lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    model = _embedder()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vecs]


# --- chunking: heading-aware split, then fixed-size windows with overlap ---
@dataclass
class Chunk:
    text: str
    source_file: str
    heading: str
    chunk_index: int


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _split_by_heading(md: str) -> list[tuple[str, str]]:
    """Return [(heading, body)] segments. Heading is the most recent ## seen."""
    segments: list[tuple[str, list[str]]] = []
    current_heading = ""
    buf: list[str] = []
    for line in md.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            if buf:
                segments.append((current_heading, buf))
                buf = []
            current_heading = m.group(2).strip()
        else:
            buf.append(line)
    if buf:
        segments.append((current_heading, buf))
    return [(h, "\n".join(b)) for h, b in segments]


def _window(text: str, size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out: list[str] = []
    start = 0
    step = max(1, size - overlap)
    while start < len(text):
        out.append(text[start : start + size])
        start += step
    return out


def chunk_markdown(md: str, source_file: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for heading, body in _split_by_heading(md):
        for piece in _window(body, CHUNK_CHARS, CHUNK_OVERLAP):
            piece = piece.strip()
            if len(piece) < 40:  # drop trivial fragments
                continue
            chunks.append(
                Chunk(text=piece, source_file=source_file, heading=heading, chunk_index=idx)
            )
            idx += 1
    return chunks


# --- LanceDB store ---
def _connect():
    import lancedb

    DB_DIR.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(DB_DIR))


def ingest() -> dict[str, Any]:
    """(Re)build the index from CORPUS_DIR. Idempotent: drops & rebuilds the table."""
    import pyarrow as pa

    md_files = sorted(CORPUS_DIR.glob("*.md"))
    if not md_files:
        return {"status": "empty", "reason": f"no .md files under {CORPUS_DIR}", "chunks": 0}

    rows: list[dict[str, Any]] = []
    for f in md_files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for ch in chunk_markdown(text, f.name):
            rows.append(
                {
                    "text": ch.text,
                    "source_file": ch.source_file,
                    "heading": ch.heading,
                    "chunk_index": ch.chunk_index,
                }
            )
    if not rows:
        return {"status": "empty", "reason": "files present but produced no chunks", "chunks": 0}

    print(f"[ingest] embedding {len(rows)} chunks from {len(md_files)} files...", flush=True)
    vectors = embed([r["text"] for r in rows])
    for r, v in zip(rows, vectors):
        r["vector"] = v

    schema = pa.schema(
        [
            pa.field("vector", pa.list_(pa.float32(), EMBED_DIMS)),
            pa.field("text", pa.string()),
            pa.field("source_file", pa.string()),
            pa.field("heading", pa.string()),
            pa.field("chunk_index", pa.int64()),
        ]
    )
    db = _connect()
    if TABLE_NAME in db.table_names():
        db.drop_table(TABLE_NAME)
    tbl = db.create_table(TABLE_NAME, data=rows, schema=schema)
    n = tbl.count_rows()
    sources = sorted({r["source_file"] for r in rows})
    print(f"[ingest] done: {n} chunks across {len(sources)} sources.", flush=True)
    return {"status": "ok", "chunks": n, "sources": sources}


def _open_table():
    db = _connect()
    if TABLE_NAME not in db.table_names():
        return None
    return db.open_table(TABLE_NAME)


def search(query: str, k: int = DEFAULT_K) -> list[dict[str, Any]]:
    tbl = _open_table()
    if tbl is None:
        raise RuntimeError(
            "index not built — run ingest first (uv run rag/server.py --ingest "
            "or POST /ingest)"
        )
    qv = embed([query])[0]
    res = tbl.search(qv).metric("cosine").limit(max(1, int(k))).to_list()
    out = []
    for r in res:
        # LanceDB cosine returns `_distance` (0 = identical). score = 1 - distance.
        dist = r.get("_distance")
        score = (1.0 - dist) if dist is not None else None
        out.append(
            {
                "text": r["text"],
                "source_file": r["source_file"],
                "heading": r.get("heading", ""),
                "chunk_index": r.get("chunk_index"),
                "score": score,
            }
        )
    return out


def _stats() -> dict[str, Any]:
    tbl = _open_table()
    if tbl is None:
        return {"status": "no-index", "chunks": 0, "sources": 0}
    n = tbl.count_rows()
    try:
        sources = len({r["source_file"] for r in tbl.to_arrow().to_pylist()})
    except Exception:  # noqa: BLE001
        sources = None
    return {"status": "ready", "chunks": n, "sources": sources}


# --- MCP + HTTP server (FastMCP, Streamable HTTP) ---
def build_app():
    from fastmcp import FastMCP
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    mcp = FastMCP(name="cto_knowledge")

    @mcp.tool
    def query_cto_knowledge(query: str, k: int = DEFAULT_K) -> str:
        """Search the CTO textbook corpus and return ranked, cited passages.

        Consult this BEFORE every CTO function (tech-debt audit, PMF research,
        org/strategy) and cite the returned `source_file`(s) in your output.

        Args:
            query: Natural-language question or topic (e.g. "microservices coupling").
            k: Number of passages to return (default 5).

        Returns:
            JSON string: a list of {source_file, heading, score, text} passages,
            ranked best-first. Each `source_file` is the grounding text to cite.
        """
        hits = search(query, k)
        return json.dumps(
            {
                "query": query,
                "results": [
                    {
                        "source_file": h["source_file"],
                        "heading": h["heading"],
                        "score": h["score"],
                        "text": h["text"],
                    }
                    for h in hits
                ],
            },
            ensure_ascii=False,
        )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_req: Request) -> JSONResponse:  # noqa: ANN001
        return JSONResponse(_stats())

    @mcp.custom_route("/search", methods=["POST"])
    async def http_search(req: Request) -> JSONResponse:  # noqa: ANN001
        body = await req.json()
        query = body.get("query", "")
        k = int(body.get("k", DEFAULT_K))
        if not query:
            return JSONResponse({"error": "missing 'query'"}, status_code=400)
        try:
            hits = search(query, k)
        except RuntimeError as e:
            return JSONResponse({"error": str(e)}, status_code=409)
        return JSONResponse({"query": query, "results": hits})

    @mcp.custom_route("/ingest", methods=["POST"])
    async def http_ingest(_req: Request) -> JSONResponse:  # noqa: ANN001
        return JSONResponse(ingest())

    return mcp


def main() -> int:
    ap = argparse.ArgumentParser(description="CTO knowledge RAG MCP sidecar")
    ap.add_argument("--ingest", action="store_true", help="build the index and exit")
    ap.add_argument("--search", metavar="QUERY", help="run one search and print JSON, then exit")
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    args = ap.parse_args()

    if args.ingest:
        print(json.dumps(ingest(), indent=2))
        return 0
    if args.search:
        print(json.dumps(search(args.search, args.k), indent=2, ensure_ascii=False))
        return 0

    mcp = build_app()
    print(
        f"[serve] cto_knowledge MCP on http://{HOST}:{PORT}{MCP_PATH} "
        f"(corpus={CORPUS_DIR}, db={DB_DIR})",
        flush=True,
    )
    mcp.run(transport="http", host=HOST, port=PORT, path=MCP_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
