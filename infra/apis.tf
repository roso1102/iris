# IRIS — Task 0.1: enable required GCP APIs.
# Also enables compute + servicenetworking needed for the VPC/PSC work in 0.5.

locals {
  required_apis = [
    "cloudresourcemanager.googleapis.com",   # IAM / project APIs
    "cloudbilling.googleapis.com",           # billing budgets
    "compute.googleapis.com",                # VPC, subnets, PSC addresses
    "run.googleapis.com",                    # Cloud Run (ingestion-worker, retrieval-api)
    "eventarc.googleapis.com",               # Pub/Sub -> Cloud Run triggers
    "pubsub.googleapis.com",                 # ingestion topic + DLQ + billing alerts
    "firestore.googleapis.com",              # sessions, quotas, kill-switch state
    "storage.googleapis.com",                # GCS buckets
    "artifactregistry.googleapis.com",       # container registry for Cloud Run
    "aiplatform.googleapis.com",     # Vertex AI (Gemini + text-embedding-004) — real service ID
    "secretmanager.googleapis.com",          # secrets (MODEL_BACKEND, API keys)
    "iam.googleapis.com",                    # service accounts, policies
    "iamcredentials.googleapis.com",         # SA token generation
    "cloudfunctions.googleapis.com",         # billing-kill-switch
    "vpcaccess.googleapis.com",              # Cloud Run VPC connector
    "servicenetworking.googleapis.com",      # Firestore VPC peering
    "identitytoolkit.googleapis.com",        # Firebase Authentication / Identity Platform
    "firebase.googleapis.com",               # Firebase project link
    "cloudscheduler.googleapis.com",         # (optional) periodic budget re-check
  ]
}

resource "google_project_service" "api" {
  for_each = toset(local.required_apis)

  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}
