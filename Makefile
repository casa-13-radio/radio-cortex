.PHONY: help install test lint format clean docker-build docker-up docker-down

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Radio Cortex - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ============================================================================
# DEVELOPMENT
# ============================================================================

install: ## Install dependencies
	pip install -e .[dev]
	pre-commit install

install-prod: ## Install production dependencies only
	pip install -e .

update: ## Update dependencies
	pip install --upgrade pip
	pip install --upgrade -e .[dev]

# ============================================================================
# TESTING
# ============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest tests/unit -v

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest tests/integration -v

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest --cov=. --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report generated at htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode
	pytest-watch

# ============================================================================
# CODE QUALITY
# ============================================================================

lint: ## Run linting checks
	@echo "$(BLUE)Running linters...$(NC)"
	ruff check .
	mypy agents/ api/ models/ services/

format: ## Format code
	@echo "$(BLUE)Formatting code...$(NC)"
	ruff format .
	isort .

format-check: ## Check if code is formatted
	ruff format --check .
	isort --check .

type-check: ## Run type checking
	mypy agents/ api/ models/ services/

# ============================================================================
# DATABASE
# ============================================================================

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	alembic upgrade head

db-rollback: ## Rollback last migration
	@echo "$(RED)Rolling back last migration...$(NC)"
	alembic downgrade -1

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)Resetting database... This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		alembic downgrade base; \
		alembic upgrade head; \
		python scripts/seed_db.py; \
		echo "$(GREEN)Database reset complete$(NC)"; \
	fi

db-seed: ## Seed database with sample data
	@echo "$(BLUE)Seeding database...$(NC)"
	python scripts/seed_db.py

db-backup: ## Backup database
	@echo "$(BLUE)Creating backup...$(NC)"
	./scripts/backup.sh

# ============================================================================
# AGENTS
# ============================================================================

hunter: ## Run Hunter agent (once)
	@echo "$(BLUE)Running Hunter agent...$(NC)"
	python -m agents.hunter --source all

hunter-daemon: ## Run Hunter as daemon
	@echo "$(BLUE)Starting Hunter daemon...$(NC)"
	python -m agents.hunter --daemon

librarian: ## Run Librarian agent
	@echo "$(BLUE)Running Librarian agent...$(NC)"
	python -m agents.librarian

compliance: ## Run Compliance agent
	@echo "$(BLUE)Running Compliance agent...$(NC)"
	python -m agents.compliance

agents-all: ## Run all agents
	@echo "$(BLUE)Starting all agents...$(NC)"
	python orchestrator.py

# ============================================================================
# DOCKER
# ============================================================================

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build

docker-up: ## Start all services
	@echo "$(GREEN)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

docker-up-dev: ## Start services in dev mode (with logs)
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

docker-down: ## Stop all services
	@echo "$(RED)Stopping services...$(NC)"
	docker-compose down

docker-logs: ## Show logs
	docker-compose logs -f

docker-ps: ## Show running containers
	docker-compose ps

docker-shell: ## Open shell in cortex container
	docker-compose exec cortex /bin/bash

docker-clean: ## Remove all containers, volumes, and images
	@echo "$(RED)Cleaning Docker environment...$(NC)"
	docker-compose down -v --rmi all

# ============================================================================
# API
# ============================================================================

api-dev: ## Run API in development mode
	@echo "$(BLUE)Starting API (dev mode)...$(NC)"
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

api-prod: ## Run API in production mode
	@echo "$(BLUE)Starting API (production)...$(NC)"
	gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

api-test: ## Test API with curl
	@echo "$(BLUE)Testing API endpoints...$(NC)"
	curl -X GET http://localhost:8000/health
	curl -X GET http://localhost:8000/api/v1/tracks

# ============================================================================
# DOCUMENTATION
# ============================================================================

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving docs at http://localhost:8001$(NC)"
	mkdocs serve -a localhost:8001

docs-build: ## Build documentation
	mkdocs build

docs-deploy: ## Deploy documentation to GitHub Pages
	mkdocs gh-deploy

# ============================================================================
# CLEANUP
# ============================================================================

clean: ## Clean temporary files
	@echo "$(BLUE)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf htmlcov/ .coverage build/ dist/ *.egg-info

clean-downloads: ## Clean downloaded audio files
	@echo "$(RED)Cleaning downloaded files...$(NC)"
	rm -rf /tmp/hunter_downloads/*

# ============================================================================
# CI/CD
# ============================================================================

ci-test: ## Run CI tests locally
	@echo "$(BLUE)Running CI pipeline locally...$(NC)"
	make lint
	make format-check
	make type-check
	make test-cov

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

# ============================================================================
# DEPLOYMENT
# ============================================================================

deploy-dev: ## Deploy to development environment
	@echo "$(BLUE)Deploying to dev...$(NC)"
	./scripts/deploy.sh dev

deploy-prod: ## Deploy to production environment
	@echo "$(BLUE)Deploying to production...$(NC)"
	./scripts/deploy.sh prod

# ============================================================================
# UTILITIES
# ============================================================================

version: ## Show project version
	@python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"

check-env: ## Check if environment variables are set
	@echo "$(BLUE)Checking environment...$(NC)"
	@python -c "from config.settings import settings; print('✅ All environment variables are set')"

logs-hunter: ## Show Hunter agent logs
	tail -f logs/hunter.log

logs-api: ## Show API logs
	tail -f logs/api.log

# ============================================================================
# FIRST-TIME SETUP
# ============================================================================

setup: ## First-time setup (install deps, setup DB, seed data)
	@echo "$(GREEN)Setting up Radio Cortex for the first time...$(NC)"
	make install
	cp .env.example .env
	@echo "$(BLUE)Please edit .env with your configuration, then run:$(NC)"
	@echo "  make docker-up"
	@echo "  make db-migrate"
	@echo "  make db-seed"