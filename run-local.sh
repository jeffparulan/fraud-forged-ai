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
    echo "⚠️  .env file not found. Creating from template..."
    cat > .env << EOF
HUGGINGFACE_API_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MEDGEMMA_COLAB_URL=
EOF
    echo "✅ Created .env file"
fi

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
echo ""

# Stop any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down 2>/dev/null || true

# Build and start services
echo ""
echo "🚀 Building and starting services..."
echo "   This may take a few minutes on first run..."
echo ""

docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check backend health
echo "🔍 Checking backend health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  Backend is taking longer than expected. Check logs with: docker-compose logs backend"
    else
        sleep 2
    fi
done

# Check frontend
echo "🔍 Checking frontend..."
for i in {1..20}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Frontend is ready"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "⚠️  Frontend is taking longer than expected. Check logs with: docker-compose logs frontend"
    else
        sleep 2
    fi
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ APP IS RUNNING!                            ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔌 Backend API: http://localhost:8000"
echo ""
echo "📊 Useful commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop app: docker-compose down"
echo "   • Restart: docker-compose restart"
echo ""
echo "🎉 Happy coding!"

