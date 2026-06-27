# CTO knowledge RAG sidecar (`query_cto_knowledge`)

The textbook-grounded **CTO RAG brain** (Phase 2). A local Vector MCP sidecar that indexes the
converted corpus (`../corpus/*.md`, gitignored) and serves a single MCP tool,
`query_cto_knowledge`, which Hermes consults before every CTO function and cites (design Q5).

## Stack (fully local, zero external keys)

- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (384 dims) — same model as the mem0
  round-trip, baked into the Docker image so the container needs no network at runtime.
- **Vector store:** LanceDB (file-based, embedded) — no second DB service.
- **Server:** FastMCP over Streamable HTTP at `/mcp`, plus plain HTTP helpers for health/curl.
- **Chunking:** heading-aware split, then fixed-size windows with overlap; every chunk keeps a
  `source_file` citation back to the corpus Markdown.

## Build the corpus first

`query_cto_knowledge` is only as good as the corpus. Convert the textbooks (idempotent,
resumable; output is gitignored):

```bash
bash ../scripts/convert_corpus.sh        # docling (PDF) + pandoc (EPUB) -> ../corpus/*.md
```

## Run via docker compose (the supported path)

```bash
# build the index from the mounted corpus on boot, then serve on :8080
docker compose --profile rag up -d --build rag-sidecar
curl -s localhost:8080/health           # {"status":"ready","chunks":N,"sources":M}
```

Bind it to Hermes (already recorded in `../hermes/config.yaml`):

```bash
hermes mcp add cto_knowledge --url http://localhost:8080/mcp
hermes mcp configure cto_knowledge       # include: query_cto_knowledge
hermes mcp list                          # confirm cto_knowledge is bound
```

The tool appears to the agent as `mcp_cto_knowledge_query_cto_knowledge`.

## Run locally without docker (dev)

```bash
uv run server.py --ingest                # build the LanceDB index from ../corpus
uv run server.py                         # serve MCP + HTTP on :8080
# one-shot query without the server:
uv run server.py --search "microservices coupling" --k 5
```

## HTTP surface (for curl / health checks)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/health` | — | `{status, chunks, sources}` |
| POST | `/ingest` | — | rebuilds the index from `CORPUS_DIR` |
| POST | `/search` | `{"query": "...", "k": 5}` | ranked chunks, each with `source_file` + `score` |
| POST | `/mcp` | (Streamable HTTP) | MCP tool `query_cto_knowledge(query, k=5)` |

## Configuration (env)

| Var | Default | Meaning |
|---|---|---|
| `CORPUS_DIR` | `/corpus` (container) / `../corpus` (local) | source Markdown |
| `RAG_DB_DIR` | `/data` (container) / `./.lancedb` (local) | LanceDB index |
| `RAG_PORT` | `8080` | server port |
| `RAG_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | embedding model |
| `RAG_CHUNK_CHARS` / `RAG_CHUNK_OVERLAP` | `1200` / `150` | chunk window |

## Smoke test

```bash
uv run ../scripts/rag_smoke.py           # asserts ranked, cited chunks + grounding integrity
```
