#!/bin/bash

# FraudForge AI - Local Development Runner
# Runs the app locally using Docker Compose

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         FraudForge AI - Local Development Setup                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found."
    
    if [ -f .env.example ]; then
        echo "📋 Copying .env.example to .env..."
        cp .env.example .env
        echo "✅ Created .env file from template"
        echo ""
        echo "⚠️  IMPORTANT: Please edit .env and add your API keys:"
        echo "   • HUGGINGFACE_API_TOKEN (required)"
        echo "   • PINECONE_API_KEY (required)"
        echo "   • PINECONE_HOST (required)"
        echo "   • OPENROUTER_API_KEY (optional, but recommended)"
        echo ""
        read -p "Press Enter after you've updated .env with your keys, or Ctrl+C to cancel..."
    else
        echo "❌ .env.example not found. Cannot create .env file."
        echo "   Please create .env manually with required environment variables."
        exit 1
    fi
fi

# Validate required environment variables
echo "🔍 Validating environment variables..."

# Function to get env var from .env file (handles comments and quotes)
get_env_var() {
    local var_name=$1
    grep "^${var_name}=" .env 2>/dev/null | head -1 | cut -d '=' -f2- | sed 's/^["'\'']//; s/["'\'']$//' | xargs
}

HUGGINGFACE_TOKEN=$(get_env_var "HUGGINGFACE_API_TOKEN")
PINECONE_KEY=$(get_env_var "PINECONE_API_KEY")
PINECONE_HOST_VAL=$(get_env_var "PINECONE_HOST")

MISSING_VARS=()

if [ -z "$HUGGINGFACE_TOKEN" ] || [[ "$HUGGINGFACE_TOKEN" == *"xxxxxxxx"* ]] || [ "$HUGGINGFACE_TOKEN" = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" ]; then
    MISSING_VARS+=("HUGGINGFACE_API_TOKEN")
fi

if [ -z "$PINECONE_KEY" ] || [[ "$PINECONE_KEY" == *"xxxx"* ]] || [ "$PINECONE_KEY" = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" ]; then
    MISSING_VARS+=("PINECONE_API_KEY")
fi

if [ -z "$PINECONE_HOST_VAL" ] || [[ "$PINECONE_HOST_VAL" == *"xxxxxx"* ]] || [ "$PINECONE_HOST_VAL" = "https://fraudforge-master-xxxxxx.svc.xxxx-xxxx-xxxx.pinecone.io" ]; then
    MISSING_VARS+=("PINECONE_HOST")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Missing or placeholder values found in .env:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   • $var"
    done
    echo ""
    echo "Please update .env with your actual API keys before continuing."
    echo "See .env.example for the required format."
    exit 1
fi

echo "✅ Required environment variables are set"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✅ Docker is running"

# Detect docker-compose command (newer Docker uses "docker compose" without hyphen)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose not found. Please install Docker Compose."
    exit 1
fi

echo "✅ Using: $DOCKER_COMPOSE"
echo ""

# Stop any existing containers
echo "🧹 Cleaning up existing containers..."
$DOCKER_COMPOSE down 2>/dev/null || true

# Build and start services
echo ""
echo "🚀 Building and starting services..."
echo "   This may take a few minutes on first run..."
echo "   Platform: Using native architecture (ARM64/AMD64 auto-detected)"
echo ""

$DOCKER_COMPOSE up --build -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check backend health
echo "🔍 Checking backend health..."
BACKEND_READY=false
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy"
        BACKEND_READY=true
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start after 60 seconds"
        echo "   Check logs with: $DOCKER_COMPOSE logs backend"
        echo "   Or view all logs: $DOCKER_COMPOSE logs"
    else
        echo "   Waiting for backend... ($i/30)"
        sleep 2
    fi
done

# Check frontend
echo "🔍 Checking frontend..."
FRONTEND_READY=false
for i in {1..20}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Frontend is ready"
        FRONTEND_READY=true
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ Frontend failed to start after 40 seconds"
        echo "   Check logs with: $DOCKER_COMPOSE logs frontend"
        echo "   Or view all logs: $DOCKER_COMPOSE logs"
    else
        echo "   Waiting for frontend... ($i/20)"
        sleep 2
    fi
done

# Final status check
if [ "$BACKEND_READY" = false ] || [ "$FRONTEND_READY" = false ]; then
    echo ""
    echo "⚠️  Some services failed to start. Check the logs above for details."
    echo "   You can still try accessing:"
    echo "   • Frontend: http://localhost:3000"
    echo "   • Backend: http://localhost:8000"
    echo ""
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ APP IS RUNNING!                            ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔌 Backend API: http://localhost:8000"
echo ""
echo "📊 Useful commands:"
echo "   • View logs: $DOCKER_COMPOSE logs -f"
echo "   • Stop app: $DOCKER_COMPOSE down"
echo "   • Restart: $DOCKER_COMPOSE restart"
echo ""
echo "🎉 Happy coding!"


