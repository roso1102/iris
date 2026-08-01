# IRIS — Phase 0.0 Terraform root module.
# Reproducible GCP foundation: project services, IAM, VPC/PSC, secrets,
# GCS buckets, Pub/Sub (ingestion + DLQ + billing alerts), billing budget.
# See README.md / ACTIONPLAN.md Phase 0.0.

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # GCS-backed state (SRS NFR-6: infra as code, reproducible environments).
  backend "gcs" {
    # bucket is bootstrapped by scripts/bootstrap_state.sh
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  # ADC already carries quota_project_id=naturepivot-rag; honor it so APIs like
  # billingbudgets (which require a quota project) authenticate correctly.
  user_project_override = true
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  user_project_override = true
}

locals {
  # Shared labels for all resources. GCP label values must be lowercase
  # letters, digits, hyphens, or underscores (no dots — emails are invalid).
  # owner is intentionally a static safe value, not the raw email.
  labels = {
    app     = "iris"
    phase   = "phase-0"
    managed = "terraform"
    owner   = "iris-team"
  }
}
