# IRIS — Terraform variables (Phase 0.0).

variable "project_id" {
  description = "GCP project ID (e.g. naturepivot-rag)."
  type        = string
}

variable "region" {
  description = "Primary GCP region for Cloud Run, functions, and data stores."
  type        = string
  default     = "us-central1"
}

variable "billing_account_id" {
  description = "Numeric GCP billing account ID (from `gcloud billing projects describe`). NOT the dashed display form."
  type        = string
  sensitive   = true
}

variable "enable_billing_budget" {
  description = "Create the billing budget + billing-publisher IAM binding. Requires Billing Account Administrator/Costs Manager on the billing account. Set false until billing access is granted."
  type        = bool
  default     = false
}

variable "budget_amount" {
  description = "Monthly billing budget cap in `budget_currency` units (e.g. 25000 = ₹25,000/mo). The kill switch halts ingestion at/above this."
  type        = number
  default     = 25000
}

variable "budget_currency" {
  description = "Currency code for the billing budget (must match the billing account's currency, e.g. USD or INR)."
  type        = string
  default     = "INR"
}

variable "owner" {
  description = "Label value for resource ownership (team/email)."
  type        = string
  default     = "iris-team"
}
