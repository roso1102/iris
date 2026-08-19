# IRIS — Task 0.4: least-privilege service accounts.
# Replaces the broad iris-backend-sa grants (CONTEXT.md §5) with two narrow SAs.

# --- Ingestion Worker SA: write-only GCS + Pub/Sub subscriber + Vertex AI.
resource "google_service_account" "ingestion_worker" {
  account_id   = "ingestion-worker-sa"
  display_name = "IRIS Ingestion Worker"
  project      = var.project_id
}

# Write access is scoped to the raw-PDF bucket only (see gcs.tf for the
# storage.objectAdmin binding with a prefix condition).
resource "google_project_iam_member" "ingestion_vertexai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.ingestion_worker.member
}

resource "google_project_iam_member" "ingestion_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = google_service_account.ingestion_worker.member
}

# --- Retrieval API SA: read-only Qdrant (network-level, Phase 2.0) + Vertex AI.
resource "google_service_account" "retrieval_api" {
  account_id   = "retrieval-api-sa"
  display_name = "IRIS Retrieval API"
  project      = var.project_id
}

resource "google_project_iam_member" "retrieval_vertexai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.retrieval_api.member
}

resource "google_project_iam_member" "retrieval_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = google_service_account.retrieval_api.member
}

resource "google_project_iam_member" "retrieval_firestore" {
  project = var.project_id
  role    = "roles/datastore.owner"
  member  = google_service_account.retrieval_api.member
}

resource "google_project_iam_member" "ingestion_firestore" {
  project = var.project_id
  role    = "roles/datastore.owner"
  member  = google_service_account.ingestion_worker.member
}

# --- Phase 4.0: Firebase JWT verification (retrieval_api + ingestion-worker
# --- verify Firebase ID tokens with firebase-admin via ADC).
resource "google_project_iam_member" "retrieval_firebaseauth" {
  project = var.project_id
  role    = "roles/firebaseauth.viewer"
  member  = google_service_account.retrieval_api.member
}

resource "google_project_iam_member" "ingestion_firebaseauth" {
  project = var.project_id
  role    = "roles/firebaseauth.viewer"
  member  = google_service_account.ingestion_worker.member
}

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
}

# NOTE: the kill switch needs roles/run.admin on the ingestion-worker Cloud Run
# service. The service is created by scripts/deploy.sh (after images build), so
# this binding is applied there via `gcloud run services add-iam-policy-binding`.

# Eventarc trigger SA for the billing topic -> function delivery.
resource "google_service_account" "billing_eventarc" {
  account_id   = "billing-eventarc-sa"
  display_name = "IRIS Billing Eventarc"
  project      = var.project_id
}

resource "google_pubsub_subscription_iam_member" "billing_eventarc_sub" {
  project      = var.project_id
  subscription = google_pubsub_subscription.billing_trigger.name
  role         = "roles/pubsub.subscriber"
  member       = google_service_account.billing_eventarc.member
}

# --- Eventarc trigger SA for the ingestion topic -> Cloud Run delivery.
resource "google_service_account" "ingest_trigger" {
  account_id   = "ingest-trigger-sa"
  display_name = "IRIS Ingestion Eventarc"
  project      = var.project_id
}

# NOTE: the trigger SA needs roles/run.invoker on ingestion-worker; applied in
# deploy.sh (same reason as above).

resource "google_pubsub_subscription_iam_member" "ingest_trigger_sub" {
  project      = var.project_id
  subscription = google_pubsub_subscription.ingestion_sub.name
  role         = "roles/pubsub.subscriber"
  member       = google_service_account.ingest_trigger.member
}
