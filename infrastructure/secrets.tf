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

# ==================== SECRETS ====================

# Hugging Face API Token
resource "google_secret_manager_secret" "huggingface_token" {
  project   = var.project_id
  secret_id = "HUGGINGFACE_API_TOKEN"

  replication {
    auto {}
  }

  labels = {
    app         = "fraudforge-ai"
    environment = var.environment
    managed-by  = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "backend_huggingface" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.huggingface_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.fraudforge_backend.email}"
}

# OpenRouter API Key
resource "google_secret_manager_secret" "openrouter_key" {
  project   = var.project_id
  secret_id = "OPENROUTER_API_KEY"

  replication {
    auto {}
  }

  labels = {
    app         = "fraudforge-ai"
    environment = var.environment
    managed-by  = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "backend_openrouter" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.openrouter_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.fraudforge_backend.email}"
}

# Pinecone API Key
resource "google_secret_manager_secret" "pinecone_key" {
  project   = var.project_id
  secret_id = "PINECONE_API_KEY"

  replication {
    auto {}
  }

  labels = {
    app         = "fraudforge-ai"
    environment = var.environment
    managed-by  = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "backend_pinecone_key" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.pinecone_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.fraudforge_backend.email}"
}

# Pinecone Index Name
resource "google_secret_manager_secret" "pinecone_index" {
  project   = var.project_id
  secret_id = "PINECONE_INDEX_NAME"

  replication {
    auto {}
  }

  labels = {
    app         = "fraudforge-ai"
    environment = var.environment
    managed-by  = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "backend_pinecone_index" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.pinecone_index.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.fraudforge_backend.email}"
}

# ==================== OUTPUTS ====================

output "backend_service_account_email" {
  value       = google_service_account.fraudforge_backend.email
  description = "Email of the backend service account"
}

output "huggingface_token_secret_name" {
  value       = google_secret_manager_secret.huggingface_token.secret_id
  description = "Name of the Hugging Face API token secret in Secret Manager"
}

output "openrouter_key_secret_name" {
  value       = google_secret_manager_secret.openrouter_key.secret_id
  description = "Name of the OpenRouter API key secret in Secret Manager"
}

output "pinecone_key_secret_name" {
  value       = google_secret_manager_secret.pinecone_key.secret_id
  description = "Name of the Pinecone API key secret in Secret Manager"
}

output "pinecone_index_secret_name" {
  value       = google_secret_manager_secret.pinecone_index.secret_id
  description = "Name of the Pinecone index name secret in Secret Manager"
}