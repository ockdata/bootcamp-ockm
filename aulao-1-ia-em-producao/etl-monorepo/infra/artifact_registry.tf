resource "google_artifact_registry_repository" "etl_repo" {
  repository_id = var.repo_name
  location      = var.region
  format        = "DOCKER"
  description   = "Docker images for ETL jobs"
}
