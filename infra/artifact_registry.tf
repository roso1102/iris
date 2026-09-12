resource "google_artifact_registry_repository" "iris" {
  project       = var.project_id
  location      = var.region
  repository_id = "iris"
  description   = "IRIS container images"
  format        = "DOCKER"
  mode          = "STANDARD_REPOSITORY"
  labels        = local.labels

  depends_on = [google_project_service.api]
}
