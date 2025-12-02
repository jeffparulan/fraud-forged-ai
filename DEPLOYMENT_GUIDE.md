# FraudForge AI - Complete Deployment Guide

## 🚀 Quick Start

This guide will help you deploy FraudForge AI to Google Cloud Platform (GCP) using Terraform, staying **100% within the FREE TIER**.

---

## 📋 Prerequisites

### 1. **Required Accounts (All Free)**
- [x] Google Cloud Platform account with billing enabled (free tier: $300 credit + always-free resources)
- [x] Hugging Face account with API token ([Get it here](https://huggingface.co/settings/tokens))
- [x] Pinecone account with free Starter plan ([Sign up here](https://app.pinecone.io/))
- [ ] OpenRouter account (optional, for fallback) ([Get key here](https://openrouter.ai/keys))

### 2. **Local Tools**
```bash
# Install required tools
brew install terraform  # or: https://developer.hashicorp.com/terraform/install
brew install google-cloud-sdk  # or: https://cloud.google.com/sdk/docs/install
```

### 3. **Verify Installations**
```bash
terraform version  # Should be >= 1.0
gcloud version     # Should be latest
docker --version   # Should be >= 20.0
```

---

## 🔧 Step 1: Clone & Setup

### 1.1 Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/fraud-forged-ai.git
cd fraud-forged-ai
```

### 1.2 Setup Environment Variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your favorite editor
```

**Required values in `.env`:**
```bash
HUGGINGFACE_API_TOKEN=hf_your_token_here
PINECONE_API_KEY=your_pinecone_key_here
PINECONE_INDEX_NAME=fraudforge-master
PINECONE_HOST=https://fraudforge-master-xxxxx.svc.xxxx-xxxx-xxxx.pinecone.io
OPENROUTER_API_KEY=sk-or-v1-your_key_here  # Optional
```

---

## ☁️ Step 2: Setup Google Cloud Platform

### 2.1 Create GCP Project
```bash
# Set your project ID (must be globally unique)
export PROJECT_ID="fraudforge-ai-$(date +%s)"

# Create the project
gcloud projects create $PROJECT_ID --name="FraudForge AI"

# Set as default project
gcloud config set project $PROJECT_ID

# Link billing account (required for Cloud Run free tier)
# Get your billing account ID
gcloud billing accounts list

# Link it (replace BILLING_ACCOUNT_ID)
gcloud billing projects link $PROJECT_ID \
  --billing-account=BILLING_ACCOUNT_ID
```

### 2.2 Enable Required APIs
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com
```

### 2.3 Create Artifact Registry Repository
```bash
gcloud artifacts repositories create fraud-forge-images \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker images for FraudForge AI"
```

### 2.4 Configure Docker Authentication
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## 🗄️ Step 3: Setup Pinecone Vector Database

### 3.1 Create Pinecone Index
1. Go to [Pinecone Console](https://app.pinecone.io/)
2. Click "Create Index"
3. **Settings:**
   - Name: `fraudforge-master`
   - Dimensions: `2048`
   - Metric: `cosine`
   - Pod Type: `s1.x1` (Free Starter plan)
4. Copy the **Host URL** (e.g., `https://fraudforge-master-xxxxx.svc.xxxx-xxxx-xxxx.pinecone.io`)

### 3.2 Preload Fraud Patterns
```bash
cd backend

# Install dependencies (if not already done)
pip install -r requirements.txt

# Run preload script
python scripts/preload_pinecone.py
```

**Expected output:**
```
✅ Successfully loaded 193 fraud patterns into Pinecone!
```

---

## 🏗️ Step 4: Terraform Deployment

### 4.1 Configure Terraform Variables
```bash
cd infrastructure

# Copy the example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required values in `terraform.tfvars`:**
```hcl
project_id           = "your-gcp-project-id"
region               = "us-central1"
app_name             = "fraud-forge"
enable_public_access = true

# API Keys (from your .env file)
huggingface_token  = "hf_your_token_here"
openrouter_key     = "sk-or-v1-your_key_here"
pinecone_api_key   = "your_pinecone_key_here"
pinecone_index_name = "fraudforge-master"
pinecone_host      = "https://fraudforge-master-xxxxx.svc.xxxx-xxxx-xxxx.pinecone.io"

# Optional
medgemma_url = ""  # Leave empty unless using Colab
```

### 4.2 Initialize Terraform
```bash
terraform init
```

### 4.3 Review Deployment Plan
```bash
terraform plan
```

**Expected output:**
- ✅ 15-20 resources to be created
- ✅ All free-tier resource limits configured
- ✅ Auto-scaling to zero when idle

### 4.4 Deploy Infrastructure
```bash
terraform apply
```

Type `yes` when prompted. Deployment takes **2-4 minutes**.

---

## 🐳 Step 5: Build & Push Docker Images

### 5.1 Build Backend Image
```bash
cd ../backend

docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/fraud-forge-images/fraud-forge-backend:latest .

docker push us-central1-docker.pkg.dev/$PROJECT_ID/fraud-forge-images/fraud-forge-backend:latest
```

### 5.2 Build Frontend Image
```bash
cd ../frontend

docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/fraud-forge-images/fraud-forge-frontend:latest .

docker push us-central1-docker.pkg.dev/$PROJECT_ID/fraud-forge-images/fraud-forge-frontend:latest
```

---

## 🚢 Step 6: Deploy to Cloud Run

### 6.1 Deploy Backend
```bash
gcloud run deploy fraud-forge-backend \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/fraud-forge-images/fraud-forge-backend:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 300
```

**Wait for deployment to complete (~2-3 minutes).**

### 6.2 Deploy Frontend
```bash
# Get backend URL
BACKEND_URL=$(gcloud run services describe fraud-forge-backend --region us-central1 --format 'value(status.url)')

# Deploy frontend with backend URL
gcloud run deploy fraud-forge-frontend \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/fraud-forge-images/fraud-forge-frontend:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 256Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars NEXT_PUBLIC_API_URL=$BACKEND_URL
```

---

## ✅ Step 7: Verify Deployment

### 7.1 Get Service URLs
```bash
# Get frontend URL
FRONTEND_URL=$(gcloud run services describe fraud-forge-frontend --region us-central1 --format 'value(status.url)')

echo "🎉 FraudForge AI Deployed!"
echo "Frontend: $FRONTEND_URL"
echo "Backend: $BACKEND_URL"
```

### 7.2 Test the Application
```bash
# Test backend health
curl $BACKEND_URL/api/health

# Expected response:
# {"status":"healthy","timestamp":"..."}

# Open frontend in browser
open $FRONTEND_URL  # macOS
# or
xdg-open $FRONTEND_URL  # Linux
```

### 7.3 Test Fraud Detection
1. Navigate to **Detect Fraud** page
2. Select **Banking** form
3. Click **"Suspicious International Wire (High Risk)"**
4. Click **"Analyze Transaction"**
5. Wait 10-30 seconds for AI analysis
6. Review fraud score and explanation

---

## 💰 Cost Optimization (FREE TIER)

### Always-Free Resources (Monthly)
- ✅ **Cloud Run**: 2M requests, 360K GB-seconds
- ✅ **Artifact Registry**: 500 MB storage
- ✅ **Cloud Build**: 120 build-minutes/day
- ✅ **Pinecone**: 100K vectors (Starter plan)
- ✅ **Hugging Face**: ~100-300 requests/hour

### How We Stay Free
1. **Scale to Zero**: Services scale to 0 when idle (no cost!)
2. **Resource Limits**: CPU/memory capped at free tier limits
3. **No CPU Boost**: Disabled for cost savings
4. **CPU Throttling**: CPU only active during requests
5. **Concurrent Limits**: Max 2 instances per service

### Expected Monthly Cost: **$0.00** 🎉

---

## 🔄 Continuous Deployment (Optional)

### GitHub Actions Setup
1. Create `.github/workflows/deploy.yml`
2. Add GCP service account key to GitHub Secrets
3. Push to `main` branch to auto-deploy

See `MANUAL_GCP_DEPLOYMENT.md` for detailed CI/CD setup.

---

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check logs
gcloud run services logs read fraud-forge-backend --region us-central1 --limit 50

# Common issues:
# 1. Missing environment variables → Check terraform.tfvars
# 2. Pinecone not initialized → Run preload script
# 3. Invalid API keys → Verify in .env
```

### Frontend Can't Connect to Backend
```bash
# Verify backend URL is set
gcloud run services describe fraud-forge-frontend --region us-central1 --format 'yaml(spec.template.spec.containers[0].env)'

# Update if needed
gcloud run services update fraud-forge-frontend \
  --region us-central1 \
  --set-env-vars NEXT_PUBLIC_API_URL=$BACKEND_URL
```

### Terraform Errors
```bash
# Clean state and retry
cd infrastructure
rm -rf .terraform/ .terraform.lock.hcl
terraform init
terraform plan
```

### Rate Limit Errors (HF)
- **Cause**: Exceeded HF free tier (~100-300 req/hr)
- **Solution**: Wait 1 hour, or upgrade to HF Pro ($9/mo)
- **Fallback**: OpenRouter will be used automatically

---

## 📊 Monitoring

### View Logs
```bash
# Backend logs
gcloud run services logs read fraud-forge-backend --region us-central1 --tail 100 --follow

# Frontend logs
gcloud run services logs read fraud-forge-frontend --region us-central1 --tail 100 --follow
```

### View Metrics
```bash
# Open Cloud Console Monitoring
echo "https://console.cloud.google.com/run?project=$PROJECT_ID"
```

---

## 🔒 Security Checklist

- [x] Environment variables stored in Secret Manager (Terraform handles this)
- [x] Service accounts with minimal permissions
- [x] HTTPS enforced (Cloud Run default)
- [x] CORS configured properly
- [x] Rate limiting enabled
- [ ] Optional: Enable IAP for authentication
- [ ] Optional: Add Cloud Armor for DDoS protection

---

## 📚 Additional Resources

- [Terraform Docs](https://developer.hashicorp.com/terraform/docs)
- [GCP Cloud Run Docs](https://cloud.google.com/run/docs)
- [Pinecone Docs](https://docs.pinecone.io/)
- [Hugging Face Inference API](https://huggingface.co/docs/api-inference/index)

---

## 🆘 Support

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section above
2. Review logs: `gcloud run services logs read fraud-forge-backend --region us-central1`
3. Open an issue on [GitHub](https://github.com/YOUR_USERNAME/fraud-forged-ai/issues)

---

## 🎉 Success!

Your FraudForge AI application is now live on GCP Cloud Run!

**Next Steps:**
- Test all 4 fraud detection forms (Banking, Medical, E-commerce, Supply Chain)
- Monitor costs in GCP Console (should stay at $0)
- Customize the UI/models for your use case
- Share the URL with your team!

---

**Deployment Time:** 2-4 hours (first time) | 15-30 minutes (subsequent deploys)

**Cost:** $0/month (free tier) | $9-20/month (with HF Pro + moderate traffic)

**Savings vs Traditional BPM:** 95%+ ($2M+ annually)

