resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.api]
}

# Session history is read newest-first by the transaction-assigned turn and
# message position.  Keep this index in Terraform so a fresh project does not
# fail follow-up queries with Firestore's "query requires an index" response.
resource "google_firestore_index" "session_messages_order" {
  project    = var.project_id
  database   = "(default)"
  collection = "messages"

  fields {
    field_path = "turn_seq"
    order      = "DESCENDING"
  }

  fields {
    field_path = "message_index"
    order      = "DESCENDING"
  }

  depends_on = [google_firestore_database.default]
}
