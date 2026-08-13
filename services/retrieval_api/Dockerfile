# IRIS — Retrieval API image (Cloud Run).
# Phase 2.0: FastAPI + uvicorn.
FROM python:3.12-slim

WORKDIR /app

COPY services/retrieval_api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/retrieval_api/ ./services/retrieval_api/
COPY services/common/ ./services/common/

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "services.retrieval_api.app:app", "--host", "0.0.0.0", "--port", "8080"]
