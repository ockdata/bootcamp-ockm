variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "mestrado-insper"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "repo_name" {
  description = "Artifact Registry repository name"
  type        = string
  default     = "data-etl-repo"
}

variable "image_name" {
  description = "Docker image name"
  type        = string
  default     = "etl-monorepo"
}

variable "gcs_bucket" {
  description = "GCS bucket for raw data layer"
  type        = string
  default     = "mestrado-insper-raw"
}

locals {
  registry_url = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repo_name}"
  image        = "${local.registry_url}/${var.image_name}:latest"
}
