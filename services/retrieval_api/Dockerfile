# IRIS — Retrieval API image (Cloud Run).
# Phase 2.0: FastAPI + uvicorn.
FROM python:3.12-slim

WORKDIR /app

COPY services/retrieval_api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/retrieval_api/ ./services/retrieval_api/
COPY services/common/ ./services/common/

# Bake the FastEmbed Qdrant/bm25 model into a dedicated, app-owned directory.
# fastembed 0.8.0 resolves via huggingface_hub's cache layout
# (models--<org>--<model>/{refs, snapshots/<hash>}) under cache_dir. We download
# into that exact layout so runtime loads are purely local (local_files_only).
ENV FASTEMBED_CACHE_PATH=/app/models
RUN mkdir -p /app/models && \
    python -c "from fastembed.sparse.bm25 import Bm25; Bm25(model_name='Qdrant/bm25', cache_dir='/app/models', language='english')"

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "services.retrieval_api.app:app", "--host", "0.0.0.0", "--port", "8080"]
