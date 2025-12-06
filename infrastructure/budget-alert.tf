# ==================== BUDGET ALERT SYSTEM ====================

# Grant permission to delete Cloud Run services
resource "google_project_iam_member" "shutdown_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.budget_shutdown.email}"
}

# Pub/Sub topic for budget alerts
resource "google_pubsub_topic" "budget_alert" {
  project = var.project_id
  name    = "budget-alert-topic"
}

# Budget with $5 threshold
resource "google_billing_budget" "monthly_budget" {
  billing_account = var.billing_account_id
  display_name    = "FraudForge AI Monthly Budget"

  budget_filter {
    projects = ["projects/${data.google_project.project.number}"]
  }

  amount {
    specified_amount {
      units = "5"
    }
  }

  threshold_rules {
    threshold_percent = 0.5  # Alert at 50% ($2.50)
  }

  threshold_rules {
    threshold_percent = 0.9  # Alert at 90% ($4.50)
  }

  threshold_rules {
    threshold_percent = 1.0  # Alert at 100% ($5.00)
    spend_basis = "CURRENT_SPEND"
  }

  all_updates_rule {
    pubsub_topic = google_pubsub_topic.budget_alert.id
  }
}

# Service account for shutdown function
resource "google_service_account" "budget_shutdown" {
  project      = var.project_id
  account_id   = "budget-shutdown-sa"
  display_name = "Budget Shutdown Service Account"
}

# Grant permissions to stop Cloud Run services
resource "google_project_iam_member" "shutdown_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.budget_shutdown.email}"
}

# Cloud Function to handle shutdown
resource "google_cloudfunctions2_function" "budget_shutdown" {
  name     = "budget-shutdown-function"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python311"
    entry_point = "process_budget_alert"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.function_code.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "256M"
    timeout_seconds    = 60
    service_account_email = google_service_account.budget_shutdown.email

    environment_variables = {
      PROJECT_ID = var.project_id
      REGION     = var.region
      BACKEND_SERVICE = "fraud-forge-backend"
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.budget_alert.id
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
  }
}

# Storage bucket for function code
resource "google_storage_bucket" "function_source" {
  project       = var.project_id
  name          = "${var.project_id}-budget-function-source"
  location      = var.region
  force_destroy = true
}

# Upload function code
resource "google_storage_bucket_object" "function_code" {
  name   = "budget-shutdown-${filemd5("${path.module}/budget-shutdown-function.zip")}.zip"
  bucket = google_storage_bucket.function_source.name
  source = "${path.module}/budget-shutdown-function.zip"
}

# Get project data
data "google_project" "project" {
  project_id = var.project_id
}

# Output
output "budget_alert_topic" {
  value = google_pubsub_topic.budget_alert.name
}