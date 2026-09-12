output "raw_bucket_name" {
  description = "Raw document bucket name."
  value       = google_storage_bucket.raw_pdfs.name
}

output "qdrant_internal_ip" {
  description = "Stable internal IP for the Qdrant VM."
  value       = google_compute_address.qdrant_internal.address
}

output "ingestion_worker_service_account" {
  description = "Ingestion worker runtime service account."
  value       = google_service_account.ingestion_worker.email
}

output "retrieval_api_service_account" {
  description = "Retrieval API runtime service account."
  value       = google_service_account.retrieval_api.email
}
