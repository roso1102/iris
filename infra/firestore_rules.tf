# IRIS — Phase 4.0: Firestore Security Rules (deployed via Terraform).

# Ruleset source is the repo-root firestore.rules file — single source of truth.
resource "google_firebaserules_ruleset" "iris" {
  count   = var.enable_firestore_rules ? 1 : 0
  project = var.project_id

  source {
    files {
      name    = "firestore.rules"
      content = file("${path.module}/../firestore.rules")
    }
  }

  depends_on = [google_firestore_database.default]
}

# Release the ruleset as the live rules for the default Firestore database.
# The `release` name convention is "cloud.firestore" + database path.
resource "google_firebaserules_release" "iris" {
  count        = var.enable_firestore_rules ? 1 : 0
  name         = "cloud.firestore"
  ruleset_name = google_firebaserules_ruleset.iris[0].name
  project      = var.project_id

  depends_on = [google_firestore_database.default]
}
