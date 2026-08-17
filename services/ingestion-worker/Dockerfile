# IRIS — Ingestion Worker image (Cloud Run).
FROM python:3.12-slim

WORKDIR /app

# System deps for OpenCV (Docling table structure model pulls in cv2),
# and g++ for PyTorch inductor CPU codegen.
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY services/ingestion-worker/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Bake the FastEmbed Qdrant/bm25 model into a dedicated, app-owned directory.
# fastembed 0.8.0 resolves via huggingface_hub's cache layout
# (models--<org>--<model>/{refs, snapshots/<hash>}) under cache_dir. We download
# into that exact layout so runtime loads are purely local (local_files_only).
ENV FASTEMBED_CACHE_PATH=/app/models
RUN mkdir -p /app/models && \
    python -c "from fastembed.sparse.bm25 import Bm25; Bm25(model_name='Qdrant/bm25', cache_dir='/app/models', language='english')"

COPY services/ingestion-worker/ ./services/ingestion-worker/
COPY services/common/ ./services/common/

# Warm Docling layout model weights at build time (~700 MB).
# Without this, every Cloud Run cold start re-downloads them (60s+ delay).
RUN python -c "from docling.document_converter import DocumentConverter; DocumentConverter()"

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["python", "services/ingestion-worker/app.py"]
