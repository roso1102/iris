# IRIS — Terraform variables (Phase 0.0).

variable "project_id" {
  description = "GCP project ID for this environment."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid GCP project ID."
  }
}

variable "region" {
  description = "Primary GCP region for Cloud Run, functions, and data stores."
  type        = string
  default     = "asia-south1"
}

variable "owner" {
  description = "Label value for resource ownership (team/email)."
  type        = string
  default     = "iris-team"
}

variable "raw_bucket_name" {
  description = "Globally unique bucket name for raw documents."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$", var.raw_bucket_name))
    error_message = "raw_bucket_name must be a valid globally unique GCS bucket name."
  }
}

variable "alert_email" {
  description = "Email address for infrastructure alerts."
  type        = string

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be a valid email address."
  }
}

variable "enable_firestore_rules" {
  description = "Release Firestore rules only after Firebase has been initialized for the project."
  type        = bool
  default     = false
}
