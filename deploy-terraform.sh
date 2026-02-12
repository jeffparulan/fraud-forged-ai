#!/bin/bash
set -euo pipefail

echo "FraudForge AI — Production Deployment (Cloud Run)"
echo "================================================="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ----------------------------
# CONFIG
# ----------------------------
PROJECT_ID="gen-lang-client-0691181644"
REPO="fraud-forge-images"
LOCATION="us-central1"
FULL_PATH="$LOCATION-docker.pkg.dev/$PROJECT_ID/$REPO"

# Load .env for Terraform vars (tokens) - single source of truth
if [ -f .env ]; then
  echo -e "${GREEN}Loading tokens from .env${NC}"
  set -a
  source .env
  set +a
  # Map .env vars to Terraform TF_VAR_* (Terraform auto-picks these up)
  export TF_VAR_project_id="${GCP_PROJECT_ID:-$PROJECT_ID}"
  export TF_VAR_huggingface_token="${HUGGINGFACE_API_TOKEN:-}"
  export TF_VAR_openrouter_key="${OPENROUTER_API_KEY:-}"
  export TF_VAR_pinecone_api_key="${PINECONE_API_KEY:-}"
  export TF_VAR_pinecone_index_name="${PINECONE_INDEX_NAME:-fraudforge-master}"
  export TF_VAR_pinecone_host="${PINECONE_HOST:-}"
else
  echo -e "${YELLOW}No .env found - using terraform.tfvars for tokens${NC}"
  export TF_VAR_project_id="$PROJECT_ID"
fi

gcloud config set project "$PROJECT_ID" >/dev/null

# ----------------------------
# TOOLING CHECK
# ----------------------------
for tool in gcloud terraform docker jq; do
    command -v $tool >/dev/null || { echo -e "${RED}$tool is missing${NC}"; exit 1; }
done

# ----------------------------
# ENSURE ARTIFACT REGISTRY REPO
# ----------------------------
echo -e "${YELLOW}Ensuring Artifact Registry repo exists...${NC}"
if ! gcloud artifacts repositories describe "$REPO" --location="$LOCATION" &>/dev/null; then
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$LOCATION" \
    --quiet
else
  echo -e "${GREEN}Repo $REPO already exists${NC}"
fi

# Skip configure-docker if already set up (avoids slow/hanging gcloud call)
REGISTRY="$LOCATION-docker.pkg.dev"
if grep -q "\"$REGISTRY\"" ~/.docker/config.json 2>/dev/null; then
  echo -e "${GREEN}Docker already configured for $REGISTRY${NC}"
else
  echo -e "${YELLOW}Configuring Docker for Artifact Registry...${NC}"
  gcloud auth configure-docker "$REGISTRY" --quiet
fi

# ----------------------------
# STEP 1: BUILD & PUSH BACKEND ONLY
# ----------------------------
echo -e "${YELLOW}Building and pushing backend...${NC}"
docker build --platform linux/amd64 -t "$FULL_PATH/fraud-forge-backend:latest" ./backend
docker push "$FULL_PATH/fraud-forge-backend:latest"

# ----------------------------
# STEP 2: DEPLOY BACKEND ONLY via Terraform (get real URL)
# ----------------------------
echo -e "${YELLOW}Deploying backend via Terraform (this gives us the real URL)...${NC}"
cd infrastructure

terraform init -upgrade >/dev/null

terraform apply \
  -target=google_cloud_run_service.backend \
  -target=google_cloud_run_service_iam_member.backend_public \
  -auto-approve

# Extract the live backend URL
BACKEND_URL=$(terraform output -raw backend_url)
echo -e "${GREEN}Backend is live at: $BACKEND_URL${NC}"

cd ..

# ----------------------------
# STEP 3: BUILD FRONTEND WITH CORRECT BACKEND URL
# ----------------------------
echo -e "${YELLOW}Building frontend with API URL = $BACKEND_URL${NC}"
docker build --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL="$BACKEND_URL" \
  -t "$FULL_PATH/fraud-forge-frontend:latest" \
  ./frontend

echo -e "${YELLOW}Pushing frontend image...${NC}"
docker push "$FULL_PATH/fraud-forge-frontend:latest"

# ----------------------------
# STEP 4: DEPLOY FRONTEND (and anything else)
# ----------------------------
echo -e "${YELLOW}Deploying frontend + full infra...${NC}"
cd infrastructure

# Check if terraform.tfvars exists, if not use example as template
if [ ! -f terraform.tfvars ]; then
    echo -e "${YELLOW}⚠️  terraform.tfvars not found. Using terraform.tfvars.example as reference.${NC}"
    echo -e "${YELLOW}   You may need to create terraform.tfvars with your actual values.${NC}"
fi

# Apply with auto-approve (will prompt for variables if terraform.tfvars doesn't exist)
terraform apply -auto-approve

FRONTEND_URL=$(terraform output -raw frontend_url)

cd ..

# ----------------------------
# FINAL OUTPUT
# ----------------------------
echo ""
echo -e "${GREEN}FRAUDFORGE AI IS FULLY LIVE AND WORKING!${NC}"
echo ""
echo -e "Frontend : $FRONTEND_URL"
echo -e "Backend  : $BACKEND_URL"
echo ""
echo "Share this on LinkedIn (bonus points if you add a custom domain):"
echo "     $FRONTEND_URL"
echo ""
echo "No more localhost:8000 errors — ever"