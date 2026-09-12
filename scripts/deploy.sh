#!/usr/bin/env bash
# IRIS — Phase 0.0 deploy script.
# Builds + deploys the services and billing kill switch. Ingestion uses the
# Terraform-managed Pub/Sub subscription with an authenticated push endpoint;
# the endpoint is attached after Cloud Run returns its URL.

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${2:-asia-south1}"
REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/iris"
# Browser origins allowed to call retrieval-api (comma-separated). Override via env:
#   CORS_ALLOWED_ORIGINS="https://iris.example.com,http://localhost:3000" ./scripts/deploy.sh
CORS_ALLOWED_ORIGINS="${CORS_ALLOWED_ORIGINS:-}"
GCS_RAW_BUCKET="${GCS_RAW_BUCKET:-procambrian-iris-staging-raw}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: could not determine GCP project. Pass it: $0 <project-id> [region]" >&2
  exit 1
fi

echo "==> Ensuring Artifact Registry repo 'iris' exists"
gcloud artifacts repositories create iris --repository-format=docker \
  --location="${REGION}" --project="${PROJECT_ID}" 2>/dev/null || true

echo "==> Building + pushing images"
gcloud builds submit --config=services/ingestion-worker/cloudbuild.yaml \
  --project="${PROJECT_ID}" --region="${REGION}" --substitutions=_REPO="${REPO}" . || {
  echo "ERROR: ingestion-worker build failed" >&2
  exit 1
}

QDRANT_IP="$(gcloud compute instances describe qdrant-1 \
  --zone="${REGION}-b" --project="${PROJECT_ID}" \
  --format='value(networkInterfaces[0].networkIP)')"
if [[ -z "${QDRANT_IP}" ]]; then
  echo "ERROR: qdrant-1 has no internal IP. Apply Terraform networking first." >&2
  exit 1
fi
gcloud builds submit --config=services/retrieval_api/cloudbuild.yaml \
  --project="${PROJECT_ID}" --region="${REGION}" --substitutions=_REPO="${REPO}" . || {
  echo "ERROR: retrieval-api build failed" >&2
  exit 1
}

echo "==> Deploying Cloud Run services"
gcloud run deploy ingestion-worker \
  --image="${REPO}/ingestion-worker:latest" \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --no-allow-unauthenticated --ingress=all \
  --cpu=2 --memory=8Gi --max-instances=3 --min-instances=0 --concurrency=1 \
  --timeout=900 --cpu-boost \
  --service-account="ingestion-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --network=iris-vpc --subnet=iris-subnet --vpc-egress=private-ranges-only \
  --set-env-vars="MODEL_BACKEND=vertex,GCP_PROJECT=${PROJECT_ID},FIREBASE_PROJECT_ID=${PROJECT_ID},GCS_RAW_BUCKET=${GCS_RAW_BUCKET},EMBEDDING_MODEL=text-embedding-004,SYNTHESIS_MODEL=gemini-2.5-flash,LITE_MODEL=gemini-2.5-flash-lite,VERTEX_VISION_LOCATION=us-central1,QDRANT_URL=http://${QDRANT_IP}:6333,RETRIEVAL_COLLECTION=iris_chunks_v2,CHUNK_TARGET_TOKENS=256,BM25_HINDI_ENABLED=1"

INGEST_URL="$(gcloud run services describe ingestion-worker \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --format='value(status.url)')"
if [[ -z "${INGEST_URL}" ]]; then
  echo "ERROR: could not resolve ingestion-worker URL." >&2
  exit 1
fi

echo "==> Attaching authenticated Pub/Sub push endpoint"
# Page events are consumed by POST / (the page handler). /ingest is the
# document-level fan-out and must NOT be the push target, or each page would
# be re-split and republished into an ingestion loop.
gcloud pubsub subscriptions update iris-ingestion-sub \
  --project="${PROJECT_ID}" \
  --push-endpoint="${INGEST_URL}/" \
  --push-auth-service-account="ingest-trigger-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --push-auth-token-audience="${INGEST_URL}"

gcloud run deploy retrieval-api \
  --image="${REPO}/retrieval-api:latest" \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --allow-unauthenticated --ingress=all \
  --cpu=2 --memory=2Gi --max-instances=10 --min-instances=1 --cpu-boost \
  --service-account="retrieval-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --network=iris-vpc --subnet=iris-subnet --vpc-egress=private-ranges-only \
  --set-env-vars="MODEL_BACKEND=vertex,GCP_PROJECT=${PROJECT_ID},FIREBASE_PROJECT_ID=${PROJECT_ID},GCS_RAW_BUCKET=${GCS_RAW_BUCKET},EMBEDDING_MODEL=text-embedding-004,SYNTHESIS_MODEL=gemini-2.5-flash,LITE_MODEL=gemini-2.5-flash-lite,RETRIEVAL_COLLECTION=iris_chunks_v2,QDRANT_URL=http://${QDRANT_IP}:6333,CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS},RERANK_LOCATION=global,BM25_HINDI_ENABLED=1"

echo "==> Granting Cloud Run IAM (kill-switch run.admin, trigger run.invoker)"
gcloud run services add-iam-policy-binding ingestion-worker \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --member="serviceAccount:billing-kill-switch-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"
gcloud run services add-iam-policy-binding ingestion-worker \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --member="serviceAccount:ingest-trigger-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

echo "==> Deploying billing kill-switch function"
gcloud functions deploy billing-kill-switch \
  --gen2 --runtime=python312 --region="${REGION}" --project="${PROJECT_ID}" \
  --trigger-topic=billing-alerts \
  --source=services/billing-kill-switch \
  --entry-point=kill_switch \
  --service-account="billing-kill-switch-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars="GCP_PROJECT=${PROJECT_ID},TARGET_SUBSCRIPTION=iris-ingestion-sub,MONTHLY_CAP=500"

echo "==> Done. Phase 0.0 deploy complete."
echo "    Test 0-A: gcloud pubsub topics publish billing-alerts \\"
echo "      --message='{\"costAmount\":16,\"budgetAmount\":15,\"currencyCode\":\"USD\"}'"
echo "    Then: gcloud run services describe ingestion-worker --region=${REGION} | grep maxInstanceCount"
