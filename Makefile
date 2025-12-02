# FraudForge AI - Makefile for local development

.PHONY: help up down logs restart rebuild clean status test backend-shell frontend-shell

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "FraudForge AI - Local Development Commands"
	@echo "=========================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick start: make up"

up: ## Start all services (builds if needed)
	@./local-dev.sh up

start: up ## Alias for 'up'

down: ## Stop and remove all containers
	@./local-dev.sh down

stop: ## Stop services without removing containers
	@./local-dev.sh stop

logs: ## View logs (follow mode)
	@./local-dev.sh logs

restart: ## Restart all services
	@./local-dev.sh restart

rebuild: ## Rebuild all images from scratch
	@./local-dev.sh rebuild

clean: ## Remove all containers, volumes, and images
	@./local-dev.sh clean

status: ## Show status of all services
	@./local-dev.sh status

test: ## Test service health
	@./local-dev.sh test

backend-shell: ## Open a shell in the backend container
	@./local-dev.sh backend

frontend-shell: ## Open a shell in the frontend container
	@./local-dev.sh frontend

# Development targets
dev-backend: ## Run backend in development mode (outside Docker)
	@echo "🔧 Starting backend in development mode..."
	@cd backend && python -m venv venv && \
		. venv/bin/activate && \
		pip install -r requirements.txt && \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

dev-frontend: ## Run frontend in development mode (outside Docker)
	@echo "⚛️  Starting frontend in development mode..."
	@cd frontend && npm install && npm run dev

install: ## Install all dependencies locally
	@echo "📦 Installing dependencies..."
	@cd backend && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	@cd frontend && npm install
	@echo "✅ Dependencies installed"

# Docker management
docker-prune: ## Clean up unused Docker resources
	@echo "🧹 Cleaning up Docker resources..."
	@docker system prune -f
	@docker volume prune -f
	@echo "✅ Docker cleanup complete"

# Quick test targets
test-backend: ## Quick test of backend API
	@curl -s http://localhost:8080/api/health | jq '.' || echo "❌ Backend not responding"

test-frontend: ## Quick test of frontend
	@curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:3000

test-fraud-detection: ## Test fraud detection endpoint
	@curl -s -X POST http://localhost:8080/api/detect \
		-H "Content-Type: application/json" \
		-d '{"sector":"banking","data":{"amount":15000,"location":"Nigeria","device":"new","time":"03:00 AM","user_age_days":2}}' | jq '.'

# Deployment targets
deploy: ## Deploy to Google Cloud Run
	@./deploy.sh

deploy-diagram: ## Deploy architecture diagram to GitHub Pages
	@echo "📊 Deploying architecture diagram..."
	@git checkout gh-pages || git checkout -b gh-pages
	@cp docs/fraud-diagram.html index.html
	@git add index.html
	@git commit -m "Update architecture diagram"
	@git push origin gh-pages
	@git checkout main
	@echo "✅ Diagram deployed to GitHub Pages"

