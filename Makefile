# FraudForge AI - Makefile for local development

.PHONY: help up down logs restart rebuild clean status test deploy

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "FraudForge AI - Local Development Commands"
	@echo "=========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick start: make up"

up: ## Start all services via docker compose
	@./run-local.sh

down: ## Stop and remove compose services
	@docker compose down

logs: ## Tail compose logs
	@docker compose logs -f

restart: ## Restart compose services
	@docker compose restart

rebuild: ## Rebuild and restart compose services
	@docker compose up -d --build

clean: ## Remove compose containers and local images for this project
	@docker compose down --rmi local --volumes --remove-orphans

status: ## Show compose service status
	@docker compose ps

test: ## Run backend unit tests
	@cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/unit/ -q

deploy: ## Deploy to Google Cloud Run via Terraform script
	@./deploy-terraform.sh
