# Service Account for Backend Cloud Run
resource "google_service_account" "fraudforge_backend" {
  project      = var.project_id
  account_id   = "fraudforge-backend"
  display_name = "FraudForge AI Backend Service Account"
  description  = "Service account for FraudForge AI backend to access secrets and GCP services"
}

# Grant Cloud Run service account necessary roles
resource "google_project_iam_member" "backend_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.fraudforge_backend.email}"
}

resource "google_project_iam_member" "backend_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.fraudforge_backend.email}"
}

resource "google_project_iam_member" "backend_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.fraudforge_backend.email}"
}

# ==================== SECRET MANAGER ====================
#
# Enabled by default (use_secret_manager = true). Costs ~$0.06/secret/month;
# set use_secret_manager = false in terraform.tfvars to fall back to plain
# Cloud Run env vars for zero-cost demos (keys will be visible in the
# Cloud Run console and Terraform state either way - state is sensitive!).

locals {
  managed_secrets = var.use_secret_manager ? merge(
    {
      OPENROUTER_API_KEY    = var.openrouter_key
      HUGGINGFACE_API_TOKEN = var.huggingface_token
      PINECONE_API_KEY      = var.pinecone_api_key
    },
    var.medgemma_local_base_url != "" ? {
      MEDGEMMA_LOCAL_BASE_URL = var.medgemma_local_base_url
    } : {},
    var.medgemma_local_api_key != "" ? {
      MEDGEMMA_LOCAL_API_KEY = var.medgemma_local_api_key
    } : {},
  ) : {}
}

resource "google_secret_manager_secret" "app" {
  for_each  = local.managed_secrets
  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  labels = {
    app         = "fraudforge-ai"
    environment = var.environment
    managed-by  = "terraform"
  }
}

resource "google_secret_manager_secret_version" "app" {
  for_each    = local.managed_secrets
  secret      = google_secret_manager_secret.app[each.key].id
  secret_data = each.value
}

resource "google_secret_manager_secret_iam_member" "backend_access" {
  for_each  = local.managed_secrets
  project   = var.project_id
  secret_id = google_secret_manager_secret.app[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.fraudforge_backend.email}"
}

# ==================== OUTPUTS ====================

output "backend_service_account_email" {
  value       = google_service_account.fraudforge_backend.email
  description = "Email of the backend service account"
}

output "secret_manager_enabled" {
  value       = var.use_secret_manager
  description = "Whether API keys are stored in Secret Manager (vs plain env vars)"
}
