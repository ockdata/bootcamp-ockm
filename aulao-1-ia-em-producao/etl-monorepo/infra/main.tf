terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Uncomment to use GCS as remote backend
  # backend "gcs" {
  #   bucket = "mestrado-insper-tfstate"
  #   prefix = "etl-monorepo"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
