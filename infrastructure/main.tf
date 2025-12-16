terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "gen-lang-client-0691181644-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = "gen-lang-client-0691181644"
  region  = "us-central1"
  billing_project       = var.project_id          
  user_project_override = true
}

# ==================== BACKEND ====================
resource "google_cloud_run_service" "backend" {
  name     = "fraud-forge-backend"
  location = "us-central1"

  metadata {
    annotations = {
      "run.googleapis.com/ingress" = "all"
    }
  }

  template {
    spec {
      service_account_name = google_service_account.fraudforge_backend.email

      containers {
        image = "us-central1-docker.pkg.dev/gen-lang-client-0691181644/fraud-forge-images/fraud-forge-backend:latest"

        ports {
          name           = "http1"
          container_port = 8080
        }

        env {
          name = "OPENROUTER_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.openrouter_key.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "HUGGINGFACE_API_TOKEN"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.huggingface_token.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "PINECONE_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.pinecone_key.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "PINECONE_INDEX_NAME"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.pinecone_index.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name  = "PINECONE_HOST"
          value = "https://fraudforge-master-kgn0lb7.svc.aped-4627-b74a.pinecone.io"
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
    google_secret_manager_secret_iam_member.backend_huggingface,
    google_secret_manager_secret_iam_member.backend_openrouter,
    google_secret_manager_secret_iam_member.backend_pinecone_key,
    google_secret_manager_secret_iam_member.backend_pinecone_index
  ]
}

# ==================== FRONTEND WITH SECURITY CONTROLS ====================
resource "google_cloud_run_service" "frontend" {
  name     = "fraud-forge-frontend"
  location = "us-central1"

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
        image = "us-central1-docker.pkg.dev/gen-lang-client-0691181644/fraud-forge-images/fraud-forge-frontend:latest"
        
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
resource "google_cloud_run_service_iam_member" "backend_public" {
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "frontend_public" {
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