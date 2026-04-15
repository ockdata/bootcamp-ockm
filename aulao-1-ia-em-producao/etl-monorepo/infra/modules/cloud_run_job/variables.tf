variable "job_name" {
  description = "Cloud Run Job name (use hyphens, e.g. ingest-sales)"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "image" {
  description = "Full Docker image URL"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for the job"
  type        = string
}

variable "gcs_bucket" {
  description = "GCS bucket name for raw layer"
  type        = string
}

variable "cpu" {
  description = "CPU allocation (e.g. '1')"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory allocation (e.g. '512Mi')"
  type        = string
  default     = "512Mi"
}

variable "timeout" {
  description = "Job timeout in seconds"
  type        = number
  default     = 3600
}

variable "max_retries" {
  description = "Maximum number of retries on failure"
  type        = number
  default     = 1
}

variable "env_vars" {
  description = "Additional environment variables"
  type        = map(string)
  default     = {}
}
