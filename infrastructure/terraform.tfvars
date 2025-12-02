# FraudForge AI - GCP Deployment Configuration
# Project: fraud-forge-ai
# Project ID: gen-lang-client-0691181644
# Project Number: 203639324676

# GCP Project Details
project_id = "your-project-id"
region     = "us-central1" # Free tier eligible region
app_name   = "fraud-forge"

# Public Access (set to true for demo, false for production with IAP)
enable_public_access = true

# Budget Configuration - FREE TIER PROTECTION
# Get your billing account ID: gcloud billing accounts list
billing_account_id = "" # TODO: Add your billing account ID (format: 0XXXXX-XXXXXX-XXXXXX)

# Notification channels for alerts (optional - will create email alerts)
notification_channels = []

# API Configuration
gcp_api_key = "your-api-key"

# Environment Variables for Cloud Run
openrouter_key    = ""
medgemma_url      = "" # TODO: Add your Google Colab MedGemma URL

# Pinecone Configuration
pinecone_api_key    = ""
pinecone_index_name = "your-index-name"
pinecone_host       = "https://your-index-host"

# GitHub (optional - for CI/CD)
github_owner = ""
github_repo  = ""

