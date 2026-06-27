# CTO knowledge RAG sidecar (Phase 2).
# Local Vector MCP: MiniLM embeddings + embedded LanceDB + FastMCP HTTP.
# Serves query_cto_knowledge at http://0.0.0.0:8080/mcp.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models \
    CORPUS_DIR=/corpus \
    RAG_DB_DIR=/data \
    RAG_HOST=0.0.0.0 \
    RAG_PORT=8080

WORKDIR /app

# Install CPU-only torch FIRST from PyTorch's CPU index so sentence-transformers
# does NOT pull the multi-GB CUDA wheels (cuBLAS/cuDNN/etc.) — this sidecar only
# does CPU inference of a tiny embedding model. Keeps the image small and the
# build fast on Apple Silicon (CUDA wheels are useless here anyway).
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model into the image so first request is fast and
# the container needs no network at runtime (key-free, offline-capable).
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY server.py .

# corpus/ is mounted read-only; /data (LanceDB) is the writable index volume.
VOLUME ["/data"]
EXPOSE 8080

# Build the index from the mounted corpus on boot, then serve. `|| true` lets
# the server start even if the corpus mount is empty (health reports no-index).
CMD ["sh", "-c", "python server.py --ingest || true; python server.py"]
