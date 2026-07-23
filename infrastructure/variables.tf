variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "fraud-forge"
}

variable "enable_public_access" {
  description = "Enable public access (unauthenticated). Set to false to require IAP."
  type        = bool
  default     = true
}

variable "github_owner" {
  description = "GitHub repository owner"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = ""
}

variable "billing_account_id" {
  description = "GCP Billing Account ID for budget alerts"
  type        = string
  default     = ""
}

variable "notification_channels" {
  description = "List of notification channel IDs for alerts"
  type        = list(string)
  default     = []
}

variable "gcp_api_key" {
  description = "Google Cloud API Key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "huggingface_token" {
  description = "Hugging Face API Token"
  type        = string
  sensitive   = true
}

variable "openrouter_key" {
  description = "OpenRouter API Key"
  type        = string
  sensitive   = true
}

variable "medgemma_url" {
  description = "MedGemma Colab URL (legacy unused)"
  type        = string
  default     = ""
}

variable "medgemma_local_base_url" {
  description = "Local MedGemma base URL (ngrok). Empty disables Stage 1 local path."
  type        = string
  default     = ""
  sensitive   = true
}

variable "medgemma_local_api_key" {
  description = "API key for local MedGemma /v1/audit-claim (X-API-Key)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "pinecone_api_key" {
  description = "Pinecone API Key"
  type        = string
  sensitive   = true
}

variable "pinecone_index_name" {
  description = "Pinecone Index Name"
  type        = string
  default     = "fraudforge-master"
}

variable "pinecone_host" {
  description = "Pinecone Host URL"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment (dev/staging/prod)"
  type        = string
  default     = "prod"
}

variable "use_secret_manager" {
  description = "Store API keys in GCP Secret Manager (recommended). Set false for zero-cost plain env vars."
  type        = bool
  default     = true
}

variable "allowed_origins" {
  description = "Comma-separated list of origins allowed by backend CORS (e.g. the frontend Cloud Run URL)"
  type        = string
  default     = "*"
}

variable "fraudforge_api_key" {
  description = "Optional API key required (X-API-Key header) on /api/detect. Empty = auth disabled (demo mode)."
  type        = string
  default     = ""
  sensitive   = true
}
