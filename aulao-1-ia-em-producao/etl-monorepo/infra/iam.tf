resource "google_service_account" "etl_runner" {
  account_id   = "etl-runner"
  display_name = "ETL Jobs Runner"
  description  = "Service account used by Cloud Run ETL jobs"
}

# Read/write access to GCS
resource "google_project_iam_member" "etl_gcs" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.etl_runner.email}"
}

# BigQuery data editor
resource "google_project_iam_member" "etl_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.etl_runner.email}"
}

# BigQuery job user (run queries)
resource "google_project_iam_member" "etl_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.etl_runner.email}"
}

# Read secrets from Secret Manager
resource "google_project_iam_member" "etl_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.etl_runner.email}"
}
