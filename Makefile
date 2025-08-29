# Learning Objectives Generation - Development Makefile
# Comprehensive development workflow commands

.PHONY: help setup install dev test lint clean build deploy

# Default target
help: ## Show this help message
	@echo "Learning Objectives Generation - Development Commands"
	@echo "=================================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Setup and Installation
setup:
	@echo "Setting up LOs Generation Pipeline..."
	python scripts/setup.py

install:
	@echo "Installing dependencies..."
	poetry install

# Development
start:
	@echo "Starting development environment..."
	python scripts/dev.py start

stop:
	@echo "Stopping all services..."
	python scripts/dev.py stop
	docker-compose stop

restart: stop start

# Database
db-init:
	@echo "Initializing database..."
	poetry run alembic upgrade head

db-migrate:
	@echo "Running database migrations..."
	poetry run alembic upgrade head

db-reset:
	@echo "WARNING: This will destroy all data!"
	@read -p "Are you sure? (y/N) " confirm && [ "$$confirm" = "y" ]
	docker-compose stop postgres
	docker-compose rm -f postgres
	docker volume rm los_generation_postgres_data
	docker-compose up -d postgres
	sleep 5
	$(MAKE) db-migrate

# Quality Assurance
test:
	@echo "Running tests..."
	poetry run pytest -v

test-cov:
	@echo "Running tests with coverage..."
	poetry run pytest -v --cov=src --cov-report=html --cov-report=term-missing

lint:
	@echo "Running code linting..."
	poetry run flake8 src tests
	poetry run mypy src

format:
	@echo "Formatting code..."
	poetry run black src tests scripts
	poetry run isort src tests scripts

# Docker
build:
	@echo "Building Docker images..."
	docker-compose build

up:
	@echo "Starting Docker services..."
	docker-compose up -d

down:
	@echo "Stopping Docker services..."
	docker-compose down

logs:
	@echo "Viewing Docker logs..."
	docker-compose logs -f

# Utilities
clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

deps:
	@echo "Dependency tree:"
	poetry show --tree

# Production
deploy-prod:
	@echo "Deploying to production..."
	docker-compose -f docker-compose.prod.yml up -d

# Ollama models
models-pull:
	@echo "Pulling Ollama models..."
	ollama pull bge-m3:latest
	ollama pull qwen/qwen3-embedding-8b
	ollama pull qwen/qwen3-reranker-8b
	ollama pull bge-reranker-v2-m3:latest

# Development helpers
shell:
	@echo "Starting Python shell..."
	poetry run python

notebook:
	@echo "Starting Jupyter notebook..."
	poetry run jupyter lab

# API testing
api-test:
	@echo "Testing API health..."
	curl -f http://localhost:8000/api/v1/health | jq

api-docs:
	@echo "Opening API documentation..."
	open http://localhost:8000/docs

# Monitoring
monitor:
	@echo "Opening monitoring dashboards..."
	open http://localhost:3000  # Grafana
	open http://localhost:9090  # Prometheus

# Backup
backup-db:
	@echo "Backing up database..."
	docker-compose exec postgres pg_dump -U los_user los_generation > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Security
security-scan:
	@echo "Running security scan..."
	poetry run safety check
	poetry run bandit -r src/

# Pre-commit hooks
pre-commit-install:
	@echo "Installing pre-commit hooks..."
	poetry run pre-commit install

pre-commit-run:
	@echo "Running pre-commit hooks..."
	poetry run pre-commit run --all-files