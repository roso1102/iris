# IRIS — Ingestion Worker image (Cloud Run).
FROM python:3.12-slim

WORKDIR /app

COPY services/ingestion-worker/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ingestion-worker/ ./services/ingestion-worker/
COPY services/common/ ./services/common/

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["python", "services/ingestion-worker/app.py"]
