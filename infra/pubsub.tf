# IRIS — Tasks 1.3 + 1.8: ingestion Pub/Sub topic, DLQ, and subscription with
# max 3 delivery attempts (Phase 1.0). The topic/subscription are provisioned
# in Phase 0.0 so the plumbing exists before the worker code lands.

# --- Ingestion topic: new upload events.
resource "google_pubsub_topic" "ingestion" {
  name    = "iris-ingestion"
  project = var.project_id
  labels  = local.labels
}

# --- Dead-letter topic: exhausted retries land here (pull-only, drained manually).
resource "google_pubsub_topic" "ingestion_dlq" {
  name    = "iris-ingestion-dlq"
  project = var.project_id
  labels  = local.labels
}

# --- Main subscription (push, Eventarc-driven; see iam.tf for the trigger SA).
resource "google_pubsub_subscription" "ingestion_sub" {
  name    = "iris-ingestion-sub"
  project = var.project_id
  topic   = google_pubsub_topic.ingestion.id

  ack_deadline_seconds = 600

  # Task 1.8: max delivery attempts, then DLQ. Pub/Sub minimum is 5 (as of 2026).
  retry_policy {
    minimum_backoff = "30s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.ingestion_dlq.id
    max_delivery_attempts = 5
  }
}

# --- Billing topic subscription for the kill-switch function (Eventarc-managed).
# Created here so iam.tf can bind the trigger SA's subscriber role; the actual
# push wiring is created by `gcloud eventarc triggers create` in deploy.sh.
resource "google_pubsub_subscription" "billing_trigger" {
  name    = "billing-alerts-sub"
  project = var.project_id
  topic   = google_pubsub_topic.billing_alerts.id
}
