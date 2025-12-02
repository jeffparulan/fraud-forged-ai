# FraudForge AI - Terraform Infrastructure

This directory contains Terraform configuration for deploying FraudForge AI to Google Cloud Platform.

## Architecture

- **Cloud Run Services**: Backend (FastAPI) and Frontend (Next.js)
- **Artifact Registry**: Docker image repository
- **Secret Manager**: Secure API key storage
- **IAM**: Service accounts and permissions
- **Monitoring**: Alerts and dashboards
- **Budget Alerts**: Cost control (optional)

## Files

- `main.tf` - Core infrastructure (Cloud Run, IAM, APIs)
- `secrets.tf` - Secret Manager and service accounts
- `monitoring.tf` - Monitoring, alerts, and cost control
- `variables.tf` - Input variables
- `outputs.tf` - Output values (URLs, service names)
- `terraform.tfvars` - Variable values (sensitive - DO NOT commit!)
- `terraform.tfvars.example` - Example variable file (safe to commit)

## Prerequisites

1. **GCP Project**: Create or use an existing project
2. **Terraform**: Install Terraform >= 1.0
3. **gcloud CLI**: Install and authenticate
4. **Docker**: For building container images

## Setup

1. **Copy example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit `terraform.tfvars`** with your values:
   - `project_id`: Your GCP project ID
   - `huggingface_token`: Your Hugging Face API token
   - `openrouter_key`: Your OpenRouter API key
   - `pinecone_api_key`: Your Pinecone API key
   - `pinecone_host`: Your Pinecone host URL

3. **Initialize Terraform:**
   ```bash
   terraform init
   ```

4. **Review plan:**
   ```bash
   terraform plan
   ```

5. **Apply infrastructure:**
   ```bash
   terraform apply
   ```

## Deployment Workflow

### Option 1: Using deploy-terraform.sh (Recommended)

This script handles the complete deployment workflow:

```bash
./deploy-terraform.sh
```

What it does:
1. Builds Docker images
2. Pushes to Artifact Registry (GCR is disabled)
3. Runs Terraform to deploy infrastructure
4. Outputs service URLs

### Option 2: Manual Deployment

1. **Build and push images:**
   ```bash
   # Set project
   gcloud config set project YOUR_PROJECT_ID
   
   # Authenticate Docker
   gcloud auth configure-docker us-central1-docker.pkg.dev
   
   # Build and push backend
   docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/fraud-forge-images/fraud-forge-backend:latest ./backend
   docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/fraud-forge-images/fraud-forge-backend:latest
   
   # Build and push frontend
   docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/fraud-forge-images/fraud-forge-frontend:latest ./frontend
   docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/fraud-forge-images/fraud-forge-frontend:latest
   ```

2. **Deploy with Terraform:**
   ```bash
   cd infrastructure
   terraform init
   terraform apply
   ```

## Key Features

### Cost Optimization
- **Scale to zero**: Services scale down to $0 when idle
- **Free tier eligible**: Stays within GCP free tier limits
- **CPU throttling**: CPU only during requests
- **Resource limits**: Optimized for cost efficiency

### Security
- **Secret Manager**: API keys stored securely
- **IAM**: Least privilege service accounts
- **Public access**: Can be disabled for IAP (Identity-Aware Proxy)

### Monitoring
- **Budget alerts**: Get notified at 50%, 90%, 100% of budget
- **CPU alerts**: Monitor high CPU usage
- **Request count alerts**: Monitor traffic spikes
- **Dashboard**: Real-time metrics visualization

## Variables

See `variables.tf` for all available variables.

Key variables:
- `project_id`: GCP Project ID (required)
- `region`: GCP Region (default: us-central1)
- `app_name`: Application name (default: fraud-forge)
- `enable_public_access`: Enable public access (default: true)

## Outputs

After deployment, get outputs with:

```bash
terraform output
```

Key outputs:
- `backend_url`: Backend API URL
- `frontend_url`: Frontend application URL
- `backend_service_name`: Backend Cloud Run service name
- `frontend_service_name`: Frontend Cloud Run service name

## Updating Services

After updating code:

1. **Rebuild and push images:**
   ```bash
   ./deploy-terraform.sh
   ```

2. **Terraform will automatically:**
   - Detect new image tags
   - Create new Cloud Run revisions
   - Route traffic to latest revision

## Troubleshooting

### Service won't start
- Check Cloud Run logs: `gcloud run services logs read SERVICE_NAME --region us-central1`
- Verify environment variables are set correctly
- Check IAM permissions for service account

### Image pull errors
- Verify Artifact Registry repository exists
- Check service account has `roles/artifactregistry.reader`
- Ensure image was pushed successfully

### Terraform state issues
- Never manually edit `terraform.tfstate`
- Use `terraform refresh` to sync state with GCP
- Backup state before major changes

## Best Practices

1. **Always use `terraform plan`** before `terraform apply`
2. **Commit `terraform.tfvars.example`**, never commit `terraform.tfvars`
3. **Use separate workspaces** for dev/staging/prod
4. **Review changes** before applying in production
5. **Monitor costs** using budget alerts

## Resources Created

- 2 Cloud Run services (backend, frontend)
- 1 Artifact Registry repository
- 2 Service accounts (backend, cloudbuild)
- 1 Secret Manager secret (Hugging Face token)
- Multiple IAM bindings
- Monitoring alerts and dashboard (optional)
- Budget alert (optional)

## Cost Estimate

**Free Tier Eligible:**
- 180K vCPU-seconds/month
- 360K GiB-seconds/month
- 2 million requests/month
- **Total: $0/month** (within free tier)

**Beyond Free Tier:**
- ~$0.50 per million requests
- ~$0.00002400 per vCPU-second
- ~$0.00000250 per GiB-second
- Scales to $0 when idle

## Support

For issues or questions:
1. Check Cloud Run logs
2. Review Terraform plan output
3. Check GCP Console for resource status

