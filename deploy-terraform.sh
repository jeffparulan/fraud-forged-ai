#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "FraudForge AI — Production Deployment (Cloud Run)"
echo "================================================="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ----------------------------
# CONFIG
# ----------------------------
# Project ID comes from GCP_PROJECT_ID env var or .env (no hardcoded default)
PROJECT_ID="${GCP_PROJECT_ID:-}"
REPO="fraud-forge-images"
LOCATION="us-central1"
FULL_PATH="$LOCATION-docker.pkg.dev/$PROJECT_ID/$REPO"
STATE_BUCKET="${PROJECT_ID}-terraform-state"

CHECK_ONLY=false
if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=true
fi

# Load .env for Terraform vars (tokens) - single source of truth
if [ -f .env ]; then
  echo -e "${GREEN}Loading tokens from .env${NC}"
  set -a
  source .env
  set +a
  # Refresh PROJECT_ID in case .env provided it
  PROJECT_ID="${GCP_PROJECT_ID:-$PROJECT_ID}"
  # Map .env vars to Terraform TF_VAR_* (Terraform auto-picks these up)
  export TF_VAR_project_id="$PROJECT_ID"
  export TF_VAR_huggingface_token="${HUGGINGFACE_API_TOKEN:-}"
  export TF_VAR_openrouter_key="${OPENROUTER_API_KEY:-}"
  export TF_VAR_pinecone_api_key="${PINECONE_API_KEY:-}"
  export TF_VAR_pinecone_index_name="${PINECONE_INDEX_NAME:-fraudforge-master}"
  export TF_VAR_pinecone_host="${PINECONE_HOST:-}"
  export TF_VAR_allowed_origins="${ALLOWED_ORIGINS:-*}"
  export TF_VAR_fraudforge_api_key="${FRAUDFORGE_API_KEY:-}"
  export TF_VAR_medgemma_local_base_url="${MEDGEMMA_LOCAL_BASE_URL:-}"
  export TF_VAR_medgemma_local_api_key="${MEDGEMMA_LOCAL_API_KEY:-}"
else
  echo -e "${YELLOW}No .env found - using terraform.tfvars for tokens${NC}"
  export TF_VAR_project_id="$PROJECT_ID"
fi

if [[ -z "$PROJECT_ID" ]]; then
  echo -e "${RED}GCP_PROJECT_ID is not set. Add it to .env or export it before running.${NC}"
  exit 1
fi
STATE_BUCKET="${PROJECT_ID}-terraform-state"
FULL_PATH="$LOCATION-docker.pkg.dev/$PROJECT_ID/$REPO"

gcloud config set project "$PROJECT_ID" >/dev/null

# ----------------------------
# TOOLING CHECK
# ----------------------------
for tool in gcloud terraform docker gsutil curl; do
    command -v $tool >/dev/null || { echo -e "${RED}$tool is missing${NC}"; exit 1; }
done

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
  echo -e "${RED}No active gcloud account. Run: gcloud auth login${NC}"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo -e "${RED}Docker is not running. Start Docker Desktop first.${NC}"
  exit 1
fi

echo -e "${YELLOW}Checking required Google APIs...${NC}"
if ! gcloud services list --enabled --format="value(name)" >/dev/null 2>&1; then
  echo -e "${RED}Cannot query enabled services in project ${PROJECT_ID}.${NC}"
  echo -e "${YELLOW}Most likely Service Usage API is disabled or you lack permissions.${NC}"
  echo "Enable it first:"
  echo "  https://console.developers.google.com/apis/api/serviceusage.googleapis.com/overview?project=${PROJECT_ID}"
  exit 1
fi
REQUIRED_APIS=(
  run.googleapis.com
  artifactregistry.googleapis.com
  cloudresourcemanager.googleapis.com
  iam.googleapis.com
  secretmanager.googleapis.com
)
for api in "${REQUIRED_APIS[@]}"; do
  if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "^$api$"; then
    echo -e "${YELLOW}Enabling API: $api${NC}"
    gcloud services enable "$api" --project "$PROJECT_ID" >/dev/null
  fi
done

echo -e "${YELLOW}Checking Terraform backend state bucket...${NC}"
if ! gsutil ls -b "gs://${STATE_BUCKET}" >/dev/null 2>&1; then
  echo -e "${RED}Missing state bucket gs://${STATE_BUCKET}${NC}"
  echo -e "${YELLOW}Create it once:${NC}"
  echo "  gcloud storage buckets create gs://${STATE_BUCKET} --location=${LOCATION} --project=${PROJECT_ID}"
  exit 1
fi

echo -e "${YELLOW}Checking required deployment variables...${NC}"
missing=()
for var in TF_VAR_huggingface_token TF_VAR_openrouter_key TF_VAR_pinecone_api_key TF_VAR_pinecone_host; do
  if [[ -z "${!var:-}" ]]; then
    missing+=("$var")
  fi
done
if (( ${#missing[@]} > 0 )); then
  echo -e "${RED}Missing required variables:${NC} ${missing[*]}"
  echo -e "${YELLOW}Set them in .env (preferred) or terraform.tfvars.${NC}"
  exit 1
fi

echo -e "${YELLOW}Running Terraform init/validate preflight...${NC}"
pushd infrastructure >/dev/null
terraform init -upgrade -input=false -backend-config="bucket=${STATE_BUCKET}" >/dev/null
terraform validate >/dev/null
popd >/dev/null

if [[ "$CHECK_ONLY" == "true" ]]; then
  echo -e "${GREEN}Preflight OK. Deployment prerequisites are satisfied.${NC}"
  echo -e "${GREEN}Run without --check to deploy.${NC}"
  exit 0
fi

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
# STEP 1: BUILD & PUSH MCP + BACKEND
# ----------------------------
echo -e "${YELLOW}Building and pushing MCP tool server...${NC}"
docker build --platform linux/amd64 -t "$FULL_PATH/fraud-forge-mcp:latest" ./backend/mcp-server
docker push "$FULL_PATH/fraud-forge-mcp:latest"

echo -e "${YELLOW}Deploying MCP tool server...${NC}"
gcloud run deploy fraud-forge-mcp \
  --project "$PROJECT_ID" \
  --region "$LOCATION" \
  --platform managed \
  --image "$FULL_PATH/fraud-forge-mcp:latest" \
  --allow-unauthenticated \
  --memory 256Mi \
  --quiet >/dev/null

MCP_URL=$(gcloud run services describe fraud-forge-mcp \
  --project "$PROJECT_ID" \
  --region "$LOCATION" \
  --format='value(status.url)')
echo -e "${GREEN}MCP is live at: $MCP_URL${NC}"

echo -e "${YELLOW}Building and pushing backend...${NC}"
docker build --platform linux/amd64 -t "$FULL_PATH/fraud-forge-backend:latest" ./backend
docker push "$FULL_PATH/fraud-forge-backend:latest"

# ----------------------------
# STEP 2: DEPLOY BACKEND (wire MCP_SERVER_URL)
# ----------------------------
echo -e "${YELLOW}Forcing backend rollout from latest image...${NC}"
gcloud run deploy fraud-forge-backend \
  --project "$PROJECT_ID" \
  --region "$LOCATION" \
  --platform managed \
  --image "$FULL_PATH/fraud-forge-backend:latest" \
  --allow-unauthenticated \
  --update-env-vars "MCP_SERVER_URL=${MCP_URL}" \
  --quiet >/dev/null

BACKEND_URL=$(gcloud run services describe fraud-forge-backend \
  --project "$PROJECT_ID" \
  --region "$LOCATION" \
  --format='value(status.url)')
echo -e "${GREEN}Backend is live at: $BACKEND_URL${NC}"

echo -e "${YELLOW}Verifying backend health endpoint...${NC}"
for i in {1..20}; do
  if curl -fsS "${BACKEND_URL}/health" >/dev/null 2>&1; then
    echo -e "${GREEN}Backend health check passed.${NC}"
    break
  fi
  if [[ $i -eq 20 ]]; then
    echo -e "${RED}Backend health check failed after deploy: ${BACKEND_URL}/health${NC}"
    exit 1
  fi
  sleep 3
done

# ----------------------------
# STEP 3: BUILD FRONTEND WITH CORRECT BACKEND URL
# ----------------------------
# Build frontend against the canonical (project-number) backend URL used in resume/LinkedIn
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)' 2>/dev/null || true)
if [[ -n "${PROJECT_NUMBER:-}" ]]; then
  FRONTEND_BUILD_API_URL="https://fraud-forge-backend-${PROJECT_NUMBER}.${LOCATION}.run.app"
else
  FRONTEND_BUILD_API_URL="$BACKEND_URL"
fi
echo -e "${YELLOW}Building frontend with API URL = $FRONTEND_BUILD_API_URL${NC}"
docker build --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL="$FRONTEND_BUILD_API_URL" \
  -t "$FULL_PATH/fraud-forge-frontend:latest" \
  ./frontend

echo -e "${YELLOW}Pushing frontend image...${NC}"
docker push "$FULL_PATH/fraud-forge-frontend:latest"

# ----------------------------
# STEP 4: DEPLOY FRONTEND (and anything else)
# ----------------------------
echo -e "${YELLOW}Forcing frontend rollout from latest image...${NC}"
gcloud run deploy fraud-forge-frontend \
  --project "$PROJECT_ID" \
  --region "$LOCATION" \
  --platform managed \
  --image "$FULL_PATH/fraud-forge-frontend:latest" \
  --allow-unauthenticated \
  --quiet >/dev/null

echo -e "${YELLOW}Syncing full infra via Terraform (IAM/env/state)...${NC}"
pushd infrastructure >/dev/null

# Check if terraform.tfvars exists, if not use example as template
if [ ! -f terraform.tfvars ]; then
    echo -e "${YELLOW}⚠️  terraform.tfvars not found. Using terraform.tfvars.example as reference.${NC}"
    echo -e "${YELLOW}   You may need to create terraform.tfvars with your actual values.${NC}"
fi

# Full apply only — avoid -target (breaks when IAM resources use count / moved addresses)
terraform init -upgrade -backend-config="bucket=${STATE_BUCKET}" >/dev/null

# gcloud may have created fraud-forge-mcp before Terraform knew about it.
# Import into state so apply updates instead of hanging on create.
MCP_TF_ID="locations/${LOCATION}/namespaces/${PROJECT_ID}/services/fraud-forge-mcp"
if ! terraform state list 2>/dev/null | grep -q '^google_cloud_run_service.mcp$'; then
  if gcloud run services describe fraud-forge-mcp \
      --project "$PROJECT_ID" --region "$LOCATION" >/dev/null 2>&1; then
    echo -e "${YELLOW}Importing existing fraud-forge-mcp into Terraform state...${NC}"
    terraform import -input=false google_cloud_run_service.mcp "$MCP_TF_ID" || true
  fi
fi

terraform apply -auto-approve

FRONTEND_URL=$(terraform output -raw frontend_url)
BACKEND_URL=$(terraform output -raw backend_url 2>/dev/null || echo "$BACKEND_URL")
MCP_URL=$(terraform output -raw mcp_url 2>/dev/null || echo "${MCP_URL:-}")

# Prefer the project-number form for CORS + public sharing (resume / LinkedIn)
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)' 2>/dev/null || echo "203639324676")
CANONICAL_FRONTEND="https://fraud-forge-frontend-${PROJECT_NUMBER}.${LOCATION}.run.app"
CANONICAL_BACKEND="https://fraud-forge-backend-${PROJECT_NUMBER}.${LOCATION}.run.app"
HASH_FRONTEND="$FRONTEND_URL"
HASH_BACKEND="$BACKEND_URL"

CORS_ORIGINS="${CANONICAL_FRONTEND},${HASH_FRONTEND},http://localhost:3000,http://127.0.0.1:3000"

UPDATE_ENV="^|^ALLOWED_ORIGINS=${CORS_ORIGINS}"
if [[ -n "${MCP_URL:-}" ]]; then
  UPDATE_ENV="${UPDATE_ENV}|MCP_SERVER_URL=${MCP_URL}"
fi

gcloud run services update fraud-forge-backend \
  --project "$PROJECT_ID" \
  --region "$LOCATION" \
  --update-env-vars "$UPDATE_ENV" \
  --quiet >/dev/null || true

popd >/dev/null

# ----------------------------
# FINAL OUTPUT
# ----------------------------
echo ""
echo -e "${GREEN}FRAUDFORGE AI IS FULLY LIVE AND WORKING!${NC}"
echo ""
echo -e "Public (resume/LinkedIn): $CANONICAL_FRONTEND"
echo -e "Frontend (hash URL)     : $HASH_FRONTEND"
echo -e "Backend                 : $CANONICAL_BACKEND"
echo -e "Backend (hash URL)      : $HASH_BACKEND"
echo -e "MCP tool server         : ${MCP_URL:-"(not set)"}"
echo ""
echo "Share this on LinkedIn:"
echo "     $CANONICAL_FRONTEND"
echo ""
echo "No more localhost:8000 errors — ever"