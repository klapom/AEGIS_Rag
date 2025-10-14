.PHONY: help install dev test lint format type-check security clean docker-up docker-down docker-logs

help:  ## Show this help message
	@echo "AEGIS RAG - Development Commands"
	@echo "================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Installation & Setup
# ============================================================================

install:  ## Install dependencies
	pip install --upgrade pip
	pip install poetry
	poetry install

dev:  ## Install with development dependencies
	poetry install --with dev
	poetry run pre-commit install

ollama-setup:  ## Pull required Ollama models
	ollama pull llama3.2:3b
	ollama pull llama3.2:8b
	ollama pull nomic-embed-text
	ollama pull mistral:7b

# ============================================================================
# Development
# ============================================================================

run:  ## Run API server in development mode
	poetry run uvicorn src.api.main:app --reload --port 8000

run-prod:  ## Run API server in production mode
	poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

shell:  ## Start IPython shell
	poetry run ipython

# ============================================================================
# Testing
# ============================================================================

test:  ## Run all tests
	poetry run pytest

test-unit:  ## Run unit tests only
	poetry run pytest tests/unit/ -v

test-integration:  ## Run integration tests only
	poetry run pytest tests/integration/ -v

test-e2e:  ## Run end-to-end tests only
	poetry run pytest tests/e2e/ -v

test-cov:  ## Run tests with coverage report
	poetry run pytest --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report: htmlcov/index.html"

test-watch:  ## Run tests in watch mode
	poetry run ptw -- -v

# ============================================================================
# Code Quality
# ============================================================================

lint:  ## Run linter (Ruff)
	poetry run ruff check src/ tests/

lint-fix:  ## Run linter with auto-fix
	poetry run ruff check src/ tests/ --fix

format:  ## Format code (Black + Ruff)
	poetry run black src/ tests/
	poetry run ruff format src/ tests/

type-check:  ## Run type checker (MyPy)
	poetry run mypy src/ --config-file=pyproject.toml

security:  ## Run security scanners (Bandit + Safety)
	poetry run bandit -r src/ -ll
	poetry run safety check

pre-commit:  ## Run all pre-commit hooks
	poetry run pre-commit run --all-files

quality:  ## Run all quality checks
	$(MAKE) lint
	$(MAKE) format
	$(MAKE) type-check
	$(MAKE) security
	$(MAKE) test

# ============================================================================
# Docker
# ============================================================================

docker-up:  ## Start all Docker services
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	docker compose ps

docker-down:  ## Stop all Docker services
	docker compose down

docker-restart:  ## Restart all Docker services
	docker compose restart

docker-logs:  ## Show Docker logs
	docker compose logs -f

docker-ps:  ## Show Docker service status
	docker compose ps

docker-clean:  ## Remove all Docker containers and volumes
	docker compose down -v
	docker system prune -f

# ============================================================================
# Database Operations
# ============================================================================

db-reset:  ## Reset all databases (WARNING: Deletes all data!)
	docker compose down -v
	docker compose up -d qdrant neo4j redis
	@echo "Databases reset. Waiting for services..."
	@sleep 10

neo4j-console:  ## Open Neo4j browser
	@echo "Opening Neo4j browser at http://localhost:7474"
	@open http://localhost:7474 || xdg-open http://localhost:7474

qdrant-console:  ## Open Qdrant dashboard
	@echo "Opening Qdrant dashboard at http://localhost:6333/dashboard"
	@open http://localhost:6333/dashboard || xdg-open http://localhost:6333/dashboard

redis-cli:  ## Connect to Redis CLI
	docker exec -it aegis-redis redis-cli

# ============================================================================
# Monitoring
# ============================================================================

prometheus:  ## Open Prometheus UI
	@echo "Opening Prometheus at http://localhost:9090"
	@open http://localhost:9090 || xdg-open http://localhost:9090

grafana:  ## Open Grafana UI
	@echo "Opening Grafana at http://localhost:3000"
	@echo "Credentials: admin / aegis-rag-grafana"
	@open http://localhost:3000 || xdg-open http://localhost:3000

metrics:  ## Show API metrics
	@curl -s http://localhost:8000/metrics | head -n 20

health:  ## Check API health
	@curl -s http://localhost:8000/api/v1/health | jq '.'

# ============================================================================
# Documentation
# ============================================================================

docs-serve:  ## Serve documentation locally
	poetry run mkdocs serve

docs-build:  ## Build documentation
	poetry run mkdocs build

docs-deploy:  ## Deploy documentation to GitHub Pages
	poetry run mkdocs gh-deploy

# ============================================================================
# Cleanup
# ============================================================================

clean:  ## Clean temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.log" -delete 2>/dev/null || true
	rm -rf htmlcov/ coverage.xml .coverage
	rm -rf dist/ build/
	@echo "Cleaned temporary files"

clean-all: clean docker-clean  ## Clean everything including Docker

# ============================================================================
# CI/CD Simulation
# ============================================================================

ci: quality test  ## Simulate CI pipeline locally

# ============================================================================
# Default
# ============================================================================

.DEFAULT_GOAL := help
