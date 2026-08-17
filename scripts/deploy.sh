#!/usr/bin/env bash
# IRIS — Phase 0.0 deploy script.
# Builds + deploys the hello-world services and the billing kill switch,
# then wires the Eventarc triggers (ingestion topic -> ingestion-worker,
# billing-alerts topic -> kill-switch function).

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${2:-asia-south1}"
REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/iris"

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
  --cpu=2 --memory=8Gi --max-instances=10 --min-instances=1 --concurrency=1 \
  --timeout=900 \
  --service-account="ingestion-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --vpc-connector=iris-connector --vpc-egress=private-ranges-only \
  --set-env-vars="MODEL_BACKEND=vertex,GCP_PROJECT=${PROJECT_ID},EMBEDDING_MODEL=text-embedding-004,SYNTHESIS_MODEL=gemini-2.5-flash,LITE_MODEL=gemini-2.5-flash-lite,VERTEX_VISION_LOCATION=us-central1,QDRANT_URL=http://10.0.0.5:6333,RETRIEVAL_COLLECTION=iris_chunks_v2"

gcloud run deploy retrieval-api \
  --image="${REPO}/retrieval-api:latest" \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --no-allow-unauthenticated --ingress=all \
  --cpu=2 --memory=2Gi --max-instances=10 --min-instances=0 \
  --service-account="retrieval-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --vpc-connector=iris-connector --vpc-egress=private-ranges-only \
  --set-env-vars="MODEL_BACKEND=vertex,GCP_PROJECT=${PROJECT_ID},EMBEDDING_MODEL=text-embedding-004,SYNTHESIS_MODEL=gemini-2.5-flash,LITE_MODEL=gemini-2.5-flash-lite,RETRIEVAL_COLLECTION=iris_chunks_v2,QDRANT_URL=http://10.0.0.5:6333"

echo "==> Granting Cloud Run IAM (kill-switch run.admin, trigger run.invoker)"
gcloud run services add-iam-policy-binding ingestion-worker \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --member="serviceAccount:billing-kill-switch-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin" 2>/dev/null || true
gcloud run services add-iam-policy-binding ingestion-worker \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --member="serviceAccount:ingest-trigger-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" 2>/dev/null || true

echo "==> Deploying billing kill-switch function"
gcloud functions deploy billing-kill-switch \
  --gen2 --runtime=python312 --region="${REGION}" --project="${PROJECT_ID}" \
  --trigger-topic=billing-alerts \
  --source=services/billing-kill-switch \
  --entry-point=kill_switch \
  --service-account="billing-kill-switch-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars="GCP_PROJECT=${PROJECT_ID},TARGET_SUBSCRIPTION=iris-ingestion-sub,MONTHLY_CAP=500"

echo "==> Wiring Eventarc trigger: ingestion topic -> ingestion-worker"
gcloud eventarc triggers create iris-ingest \
  --location="${REGION}" --project="${PROJECT_ID}" \
  --event-filters type=google.cloud.pubsub.topic.v1.messagePublished \
  --event-filters topic=iris-ingestion \
  --destination-run-service=ingestion-worker \
  --destination-run-region="${REGION}" \
  --service-account="ingest-trigger-sa@${PROJECT_ID}.iam.gserviceaccount.com" 2>/dev/null || true

echo "==> Done. Phase 0.0 deploy complete."
echo "    Test 0-A: gcloud pubsub topics publish billing-alerts \\"
echo "      --message='{\"costAmount\":16,\"budgetAmount\":15,\"currencyCode\":\"USD\"}'"
echo "    Then: gcloud run services describe ingestion-worker --region=${REGION} | grep maxInstanceCount"
