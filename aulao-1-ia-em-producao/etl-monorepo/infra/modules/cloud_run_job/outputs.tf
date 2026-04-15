output "job_name" {
  description = "Cloud Run Job name"
  value       = google_cloud_run_v2_job.this.name
}

output "job_id" {
  description = "Cloud Run Job full resource ID"
  value       = google_cloud_run_v2_job.this.id
}
