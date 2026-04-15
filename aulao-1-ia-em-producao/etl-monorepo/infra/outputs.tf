output "registry_url" {
  description = "Artifact Registry URL"
  value       = local.registry_url
}

output "service_account_email" {
  description = "Service account used by ETL jobs"
  value       = google_service_account.etl_runner.email
}
