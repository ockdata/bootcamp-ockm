resource "google_cloud_run_v2_job" "this" {
  name     = var.job_name
  location = var.region
  project  = var.project_id

  template {
    task_count  = 1
    parallelism = 1

    template {
      timeout         = "${var.timeout}s"
      max_retries     = var.max_retries
      service_account = var.service_account_email

      containers {
        image = var.image

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }

        env {
          name  = "GCP_PROJECT"
          value = var.project_id
        }

        env {
          name  = "GCS_BUCKET"
          value = var.gcs_bucket
        }

        env {
          name  = "JOB_NAME"
          value = var.job_name
        }

        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }
}
