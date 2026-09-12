# IRIS — Task 0.4: least-privilege service accounts.
# Replaces the broad iris-backend-sa grants (CONTEXT.md §5) with two narrow SAs.

data "google_project" "current" {
  project_id = var.project_id
}

locals {
  pubsub_service_agent = "service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# --- Ingestion Worker SA: write-only GCS + Pub/Sub subscriber + Vertex AI.
resource "google_service_account" "ingestion_worker" {
  account_id   = "ingestion-worker-sa"
  display_name = "IRIS Ingestion Worker"
  project      = var.project_id
  depends_on   = [google_project_service.api]
}

# Write access is scoped to the raw-PDF bucket only (see gcs.tf for the
# storage.objectAdmin binding with a prefix condition).
resource "google_project_iam_member" "ingestion_vertexai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.ingestion_worker.member
}

# --- Retrieval API SA: read-only Qdrant (network-level, Phase 2.0) + Vertex AI.
resource "google_service_account" "retrieval_api" {
  account_id   = "retrieval-api-sa"
  display_name = "IRIS Retrieval API"
  project      = var.project_id
  depends_on   = [google_project_service.api]
}

resource "google_service_account" "qdrant_vm" {
  account_id   = "qdrant-vm-sa"
  display_name = "IRIS Qdrant VM"
  project      = var.project_id
  depends_on   = [google_project_service.api]
}

resource "google_project_iam_member" "qdrant_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = google_service_account.qdrant_vm.member
}

resource "google_project_iam_member" "qdrant_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = google_service_account.qdrant_vm.member
}

resource "google_project_iam_member" "retrieval_vertexai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.retrieval_api.member
}

resource "google_project_iam_member" "retrieval_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.retrieval_api.member
}

resource "google_project_iam_member" "ingestion_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.ingestion_worker.member
}

# --- Phase 4.0: Firebase JWT verification (retrieval_api + ingestion-worker
# --- verify Firebase ID tokens with firebase-admin via ADC).
# --- Phase 4.0: retrieval_api signs V4 GCS URLs with its own ADC identity.
# --- `roles/iam.serviceAccountTokenCreator` on itself lets it mint the
# --- signing key (serviceAccount.signJwt). storage.objects.get on the raw-PDF
# --- bucket is covered by the existing objectAdmin binding in gcs.tf.
resource "google_service_account_iam_member" "retrieval_api_self_signer" {
  service_account_id = google_service_account.retrieval_api.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.retrieval_api.email}"
}

# --- Billing kill-switch function SA.
resource "google_service_account" "billing_kill_switch" {
  account_id   = "billing-kill-switch-sa"
  display_name = "IRIS Billing Kill Switch"
  project      = var.project_id
  depends_on   = [google_project_service.api]
}

# NOTE: the kill switch needs roles/run.admin on the ingestion-worker Cloud Run
# service. The service is created by scripts/deploy.sh (after images build), so
# this binding is applied there via `gcloud run services add-iam-policy-binding`.

# --- Service account used for authenticated Pub/Sub push delivery.
resource "google_service_account" "ingest_trigger" {
  account_id   = "ingest-trigger-sa"
  display_name = "IRIS Ingestion Pub/Sub Push"
  project      = var.project_id
  depends_on   = [google_project_service.api]
}

# Pub/Sub must be allowed to mint an OIDC token for the push identity.
resource "google_service_account_iam_member" "ingest_trigger_token_creator" {
  service_account_id = google_service_account.ingest_trigger.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${local.pubsub_service_agent}"
}

# Pub/Sub's service agent must publish to the DLQ and acknowledge the source
# subscription when forwarding exhausted messages.
resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.ingestion_dlq.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${local.pubsub_service_agent}"
}

resource "google_pubsub_subscription_iam_member" "dlq_subscriber" {
  project      = var.project_id
  subscription = google_pubsub_subscription.ingestion_sub.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${local.pubsub_service_agent}"
}
