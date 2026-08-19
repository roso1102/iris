# IRIS — Phase 4.0: Firestore Security Rules (deployed via Terraform).

# Ruleset source is the repo-root firestore.rules file — single source of truth.
resource "google_firebaserules_ruleset" "iris" {
  project = var.project_id

  source {
    files {
      name    = "firestore.rules"
      content = file("${path.module}/../firestore.rules")
    }
  }
}

# Release the ruleset as the live rules for the default Firestore database.
# The `release` name convention is "cloud.firestore" + database path.
resource "google_firebaserules_release" "iris" {
  name         = "cloud.firestore"
  ruleset_name = google_firebaserules_ruleset.iris.name
  project      = var.project_id
}
