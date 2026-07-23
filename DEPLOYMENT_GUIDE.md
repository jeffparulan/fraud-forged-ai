# FraudForge AI - Complete Deployment Guide

## ⚠️ Prerequisites & Dependencies

### Required Software & Versions

Before deploying, ensure you have the following installed:

| Tool | Minimum Version | Installation |
|------|----------------|--------------|
| **Docker Desktop** | 4.0+ | [Download](https://www.docker.com/products/docker-desktop) |
| **Terraform** | 1.5.0+ | `brew install terraform` (Mac) or [Download](https://www.terraform.io/downloads) |
| **Google Cloud SDK (gcloud)** | 450.0.0+ | [Install Guide](https://cloud.google.com/sdk/docs/install) |
| **jq** | 1.6+ | `brew install jq` (Mac) or `apt-get install jq` (Linux) |
| **Git** | 2.30+ | Usually pre-installed |

### Required Accounts & Access

1. **Google Cloud Platform Account**
   - Active billing account (required for Cloud Run)
   - Project with billing enabled
   - Owner or Editor role on the project

2. **API Keys & Tokens**
   - **Hugging Face**: [Get token](https://huggingface.co/settings/tokens) (Pro subscription recommended)
   - **Pinecone**: [Get API key](https://app.pinecone.io/) (Free tier available)
   - **OpenRouter**: [Get API key](https://openrouter.ai/keys) (Free tier available)

### System Requirements

- **RAM**: 8GB minimum (16GB recommended for Docker)
- **Disk Space**: 10GB free space
- **Network**: Stable internet connection (for downloading Docker images and deploying)

## 📋 Pre-Deployment Checklist

- [ ] Docker Desktop installed and running
- [ ] Terraform installed (`terraform version`)
- [ ] gcloud CLI installed and authenticated (`gcloud auth login`)
- [ ] GCP project created with billing enabled
- [ ] All API keys obtained (HF, Pinecone, OpenRouter)
- [ ] Git repository cloned locally
- [ ] Terminal access with admin/sudo privileges

## 🚀 Step-by-Step Deployment

### Step 1: Clone and Setup (5-10 minutes)

```bash
# Clone the repository
git clone <your-repo-url>
cd fraud-forged-ai

# Verify Docker is running
docker ps

# Verify Terraform is installed
terraform version

# Verify gcloud is authenticated
gcloud auth list
```

### Step 2: Configure Environment Variables (10-15 minutes)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

**Required variables:**
```bash
HUGGINGFACE_API_TOKEN=hf_xxxxxxxxxxxxx
PINECONE_API_KEY=pcsk_xxxxxxxxxxxxx
PINECONE_HOST=https://xxxxx-xxxxx.svc.environment.pinecone.io
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
```

### Step 3: Configure Terraform (10-15 minutes)

```bash
cd infrastructure

# Copy example Terraform variables
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your GCP project details
nano terraform.tfvars  # or use your preferred editor
```

**Required variables:**
```hcl
project_id = "your-gcp-project-id"
huggingface_token = "hf_xxxxxxxxxxxxx"
openrouter_key = "sk-or-v1-xxxxxxxxxxxxx"
pinecone_api_key = "pcsk_xxxxxxxxxxxxx"
pinecone_index_name = "fraud-patterns"
pinecone_host = "https://xxxxx-xxxxx.svc.environment.pinecone.io"
github_owner = "your-github-username"
github_repo = "fraud-forged-ai"
```

### Step 4: Initialize Terraform (5-10 minutes)

```bash
# Still in infrastructure/ directory
terraform init

# Verify Terraform can connect to GCP
terraform plan
```

**Expected output:** Should show resources to be created (no errors).

### Step 5: Deploy Infrastructure (30-60 minutes)

```bash
# Return to project root
cd ..

# Run deployment script
./deploy-terraform.sh
```

**What happens during deployment:**
1. **Docker Build** (10-15 min): Builds **three** images — `fraud-forge-mcp`, `fraud-forge-backend`, `fraud-forge-frontend`
2. **Image Push** (5-10 min): Pushes images to Google Artifact Registry
3. **MCP + Backend rollouts**: Deploys MCP first, then sets backend `MCP_SERVER_URL` to the MCP URL
4. **Terraform Apply** (15-30 min): Syncs Cloud Run services, IAM, networking for all three services
5. **Service Startup** (5-10 min): Cloud Run services start and become available

**Total time: 30-60 minutes** (first deployment)

### Step 6: Verify Deployment (5 minutes)

```bash
# Get deployment URLs
cd infrastructure
terraform output
# Expect: mcp_url, backend_url, frontend_url

# Test MCP tool server
curl "$(terraform output -raw mcp_url)/health"

# Test backend health
curl "$(terraform output -raw backend_url)/health"

# Test frontend
open "$(terraform output -raw frontend_url)"
```

On a successful detect run, the decision-trace badge should show `mcp: ok` (not `mcp: disabled`) when the payload includes wallets / provider_id / seller_id.

## ⏱️ Realistic Deployment Times

| Scenario | Time Estimate | Notes |
|----------|---------------|-------|
| **First-time deployment** | 1-2 hours | Includes all setup, learning curve, troubleshooting |
| **Subsequent deployments** | 15-30 minutes | Code updates only, infrastructure already exists |
| **Full infrastructure rebuild** | 45-60 minutes | If Terraform state is lost or major changes |

**Factors affecting deployment time:**
- Internet speed (Docker image downloads)
- GCP region latency
- Terraform state initialization (first time)
- Docker build cache (faster on subsequent builds)

## 🔧 Troubleshooting

### Common Issues

#### 1. Docker Build Fails
```bash
# Clear Docker cache
docker system prune -a

# Rebuild images with no cache (MCP, then backend, then frontend)
docker build --no-cache -t fraud-forge-mcp ./backend/mcp-server
docker build --no-cache -t fraud-forge-backend ./backend
docker build --no-cache --build-arg NEXT_PUBLIC_API_URL=https://your-backend.run.app \
  -t fraud-forge-frontend ./frontend
```

#### 2. Terraform Authentication Error
```bash
# Re-authenticate with GCP
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

#### 3. Cloud Run Deployment Fails
```bash
# Check each service
gcloud run services describe fraud-forge-mcp --region=us-central1
gcloud run services describe fraud-forge-backend --region=us-central1
gcloud run services describe fraud-forge-frontend --region=us-central1

# Confirm backend can reach MCP
gcloud run services describe fraud-forge-backend --region=us-central1 \
  --format='yaml(spec.template.spec.containers[0].env)' | grep -A1 MCP_SERVER_URL

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

#### 4. API Key Errors
- Verify keys are correct in `.env` and `terraform.tfvars`
- Check API key permissions (HF token with model access accepted, Pinecone free tier limits, OpenRouter key active)
- Ensure keys don't have extra spaces or quotes

#### 5. CORS Errors
- Verify backend URL is correctly set in frontend build
- Check Cloud Run IAM permissions (public access enabled)

## 📚 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 🆘 Getting Help

If you encounter issues:
1. Check the troubleshooting section above
2. Review Cloud Run logs: `gcloud logging read`
3. Check Terraform state: `terraform show`
4. Verify all prerequisites are met

---

**Note:** This deployment guide assumes basic familiarity with Docker, Terraform, and Google Cloud Platform. For first-time users, allow 2-3 hours for the complete setup process including learning and troubleshooting.

