terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Partial backend configuration: pass the state bucket at init time so the
  # repo stays project-agnostic. deploy-terraform.sh does this automatically:
  #   terraform init -backend-config="bucket=${PROJECT_ID}-terraform-state"
  backend "gcs" {
    prefix = "terraform/state"
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}

locals {
  image_repo = "${var.region}-docker.pkg.dev/${var.project_id}/fraud-forge-images"

  # Sensitive values delivered to Cloud Run either via Secret Manager
  # (use_secret_manager = true, recommended) or plain env vars (free tier).
  backend_secrets = {
    OPENROUTER_API_KEY    = var.openrouter_key
    HUGGINGFACE_API_TOKEN = var.huggingface_token
    PINECONE_API_KEY      = var.pinecone_api_key
  }

  # Non-sensitive configuration, always plain env vars.
  backend_plain_env = {
    PINECONE_INDEX_NAME = var.pinecone_index_name
    PINECONE_HOST       = var.pinecone_host
    ALLOWED_ORIGINS     = var.allowed_origins
    FRAUDFORGE_API_KEY  = var.fraudforge_api_key
    GCP_PROJECT_ID      = var.project_id
  }
}

# ==================== BACKEND ====================
resource "google_cloud_run_service" "backend" {
  name     = "fraud-forge-backend"
  location = var.region

  metadata {
    annotations = {
      "run.googleapis.com/ingress" = "all"
    }
  }

  template {
    spec {
      service_account_name = google_service_account.fraudforge_backend.email

      containers {
        image = "${local.image_repo}/fraud-forge-backend:latest"

        ports {
          name           = "http1"
          container_port = 8080
        }

        dynamic "env" {
          for_each = local.backend_plain_env
          content {
            name  = env.key
            value = env.value
          }
        }

        # Secrets as plain env vars (only when Secret Manager is disabled)
        dynamic "env" {
          for_each = var.use_secret_manager ? {} : local.backend_secrets
          content {
            name  = env.key
            value = env.value
          }
        }

        # Secrets referenced from Secret Manager (recommended)
        dynamic "env" {
          for_each = var.use_secret_manager ? local.backend_secrets : {}
          content {
            name = env.key
            value_from {
              secret_key_ref {
                name = google_secret_manager_secret.app[env.key].secret_id
                key  = "latest"
              }
            }
          }
        }

        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }

      timeout_seconds       = 300
      container_concurrency = 80
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  depends_on = [
    google_service_account.fraudforge_backend
  ]
}

# ==================== FRONTEND WITH SECURITY CONTROLS ====================
resource "google_cloud_run_service" "frontend" {
  name     = "fraud-forge-frontend"
  location = var.region

  metadata {
    annotations = {
      "run.googleapis.com/ingress" = "all"
    }
  }

  template {
    spec {
      # Use dedicated service account with minimal permissions
      service_account_name = google_service_account.frontend.email

      containers {
        image = "${local.image_repo}/fraud-forge-frontend:latest"

        ports {
          name           = "http1"
          container_port = 3000
        }

        env {
          name  = "NEXT_PUBLIC_API_URL"
          value = google_cloud_run_service.backend.status[0].url
        }

        env {
          name  = "NODE_ENV"
          value = "production"
        }

        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }

      timeout_seconds       = 300
      container_concurrency = 80
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  depends_on = [google_cloud_run_service.backend]
}

# Create dedicated service account for frontend
resource "google_service_account" "frontend" {
  project      = var.project_id
  account_id   = "fraudforge-frontend"
  display_name = "FraudForge AI Frontend Service Account"
  description  = "Minimal permissions service account for frontend"
}

# Grant only necessary permissions
resource "google_project_iam_member" "frontend_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.frontend.email}"
}

resource "google_project_iam_member" "frontend_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.frontend.email}"
}

# ==================== PUBLIC ACCESS ====================
# Gated by enable_public_access. Set to false to remove unauthenticated
# access (then front the services with IAP or call with an identity token).
resource "google_cloud_run_service_iam_member" "backend_public" {
  count    = var.enable_public_access ? 1 : 0
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "frontend_public" {
  count    = var.enable_public_access ? 1 : 0
  service  = google_cloud_run_service.frontend.name
  location = google_cloud_run_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ==================== OUTPUTS ====================
output "backend_url" {
  value = google_cloud_run_service.backend.status[0].url
}

output "frontend_url" {
  value = google_cloud_run_service.frontend.status[0].url
}
