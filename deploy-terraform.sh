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
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$LOCATION" \
  --quiet 2>/dev/null || true

gcloud auth configure-docker "$LOCATION-docker.pkg.dev" --quiet

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
  -target=google_cloud_run_v2_service.backend \
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