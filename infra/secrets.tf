# IRIS — Task 0.6: Secret Manager secrets.

locals {
  secrets = {
    "MODEL_BACKEND"    = "vertex"
    "GCP_PROJECT"      = var.project_id
    "EMBEDDING_MODEL"  = "text-embedding-004"
    "SYNTHESIS_MODEL"  = "gemini-flash"
    "LITE_MODEL"       = "gemini-flash-lite"
  }
}

resource "google_secret_manager_secret" "iris" {
  for_each = local.secrets

  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  labels = local.labels
}

resource "google_secret_manager_secret_version" "iris" {
  for_each = local.secrets

  secret      = google_secret_manager_secret.iris[each.key].id
  secret_data = each.value
}

# FIREBASE_CONFIG is created by scripts/setup_firebase.sh after Firebase init
# (Task 0.7) because the apiKey/authDomain are generated, not static.
