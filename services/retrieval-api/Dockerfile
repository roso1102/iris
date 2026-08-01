# IRIS — Retrieval API image (Cloud Run).
FROM python:3.12-slim

WORKDIR /app

COPY services/retrieval-api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/retrieval-api/ ./services/retrieval-api/
COPY services/common/ ./services/common/

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["python", "services/retrieval-api/app.py"]
