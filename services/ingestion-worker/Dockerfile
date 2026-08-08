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

COPY services/ingestion-worker/ ./services/ingestion-worker/
COPY services/common/ ./services/common/

# Warm Docling layout model weights at build time (~700 MB).
# Without this, every Cloud Run cold start re-downloads them (60s+ delay).
RUN python -c "from docling.document_converter import DocumentConverter; DocumentConverter()"

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["python", "services/ingestion-worker/app.py"]
