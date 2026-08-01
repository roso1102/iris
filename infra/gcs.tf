# IRIS — Task 1.1: tenant-prefixed GCS buckets (Phase 0.0 provisions the bucket;
# tenant prefixes + IAM conditions + cascading-delete scaffolding land with
# Phase 1.0 ingestion code).

# Raw PDF storage, tenant-prefixed: gs://iris-raw-pdfs/{tenant_id}/{doc_id}.pdf
resource "google_storage_bucket" "raw_pdfs" {
  name                        = "iris-raw-pdfs"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }

  labels = local.labels
}

# Least-privilege: ingestion worker can write/read objects but never manage
# the bucket itself (no storage.admin). Object-level condition scopes to the
# tenant prefix at Phase 4.0 once tenant IDs exist; for now objectAdmin is
# bucket-scoped so the Phase 1.0 worker can place any tenant's objects.
resource "google_storage_bucket_iam_member" "ingestion_object_admin" {
  bucket = google_storage_bucket.raw_pdfs.name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.ingestion_worker.member
}
