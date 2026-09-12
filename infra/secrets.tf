# IRIS — Task 0.6: Secret Manager secrets.

locals {
  secret_names = toset(["FIREBASE_CONFIG"])
}

resource "google_secret_manager_secret" "iris" {
  for_each = local.secret_names

  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  labels = local.labels

  depends_on = [google_project_service.api]
}

# FIREBASE_CONFIG is created by scripts/setup_firebase.sh after Firebase init
# (Task 0.7) because the apiKey/authDomain are generated, not static.
# Secret values are intentionally not managed by Terraform because secret_data
# would be persisted in Terraform state. Populate versions through a controlled
# release job or Secret Manager after the secret containers exist.
