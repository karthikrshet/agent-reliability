# Agent Reliability Lab — Developer Makefile
# Requires: uv, docker, docker compose, pnpm

.PHONY: help dev dev-down install lint format typecheck test test-unit \
        test-integration test-e2e test-security migrate migrate-down \
        migrate-create build clean doctor

COMPOSE = docker compose -f deployment/docker-compose/docker-compose.yml
UV      = uv
PNPM    = pnpm

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─────────────────────────────────────────────
# Development stack
# ─────────────────────────────────────────────
dev: ## Start the full development stack
	$(COMPOSE) up --build -d
	@echo ""
	@echo "✓ Services starting..."
	@echo "  API:       http://localhost:8000"
	@echo "  Dashboard: http://localhost:3000"
	@echo "  Docs:      http://localhost:8000/docs"
	@echo ""
	@echo "  ⚠ WARNING: Dev mode. Services bound to loopback. Not for production."

dev-logs: ## Stream logs from all services
	$(COMPOSE) logs -f

dev-down: ## Stop the development stack
	$(COMPOSE) down

dev-reset: ## Stop stack and delete all volumes (DESTROYS DATA)
	$(COMPOSE) down -v --remove-orphans

# ─────────────────────────────────────────────
# Installation
# ─────────────────────────────────────────────
install: ## Install all Python and Node dependencies
	$(UV) sync --all-packages
	$(PNPM) install

# ─────────────────────────────────────────────
# Linting and formatting
# ─────────────────────────────────────────────
lint: ## Run all linters
	$(UV) run ruff check .
	$(PNPM) --filter @arl/dashboard lint

lint-fix: ## Auto-fix linting issues
	$(UV) run ruff check . --fix
	$(PNPM) --filter @arl/dashboard lint --fix

format: ## Format all code
	$(UV) run ruff format .
	$(PNPM) --filter @arl/dashboard format

format-check: ## Check formatting without modifying
	$(UV) run ruff format --check .
	$(PNPM) --filter @arl/dashboard format:check

typecheck: ## Run strict type checks
	$(UV) run mypy packages/ apps/ adapters/ environments/
	$(PNPM) --filter @arl/dashboard typecheck

# ─────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────
test: ## Run unit tests (no external dependencies)
	$(UV) run pytest -m "unit" -v

test-unit: ## Run unit tests only
	$(UV) run pytest -m "unit" -v --tb=short

test-integration: ## Run integration tests (requires Docker)
	$(UV) run pytest -m "integration" -v --tb=short

test-contract: ## Run contract tests
	$(UV) run pytest -m "contract" -v --tb=short

test-e2e: ## Run end-to-end tests (requires full stack)
	$(UV) run pytest -m "e2e" -v --tb=short

test-security: ## Run security tests
	$(UV) run pytest -m "security" -v --tb=short

test-recovery: ## Run worker recovery tests
	$(UV) run pytest -m "recovery" -v --tb=short

test-all: ## Run complete test suite
	$(UV) run pytest -v

test-ci: ## Run test suite for CI (with coverage)
	$(UV) run pytest --cov=packages --cov=apps --cov=adapters \
		--cov=environments --cov-report=xml --cov-report=term-missing \
		--cov-fail-under=85 -v

# ─────────────────────────────────────────────
# Database migrations
# ─────────────────────────────────────────────
migrate: ## Apply all pending migrations
	$(UV) run --package arl-api alembic -c apps/api/alembic.ini upgrade head

migrate-down: ## Rollback all migrations
	$(UV) run --package arl-api alembic -c apps/api/alembic.ini downgrade base

migrate-create: ## Create a new migration (MSG= required)
	@test -n "$(MSG)" || (echo "ERROR: MSG= required. Example: make migrate-create MSG='add indexes'"; exit 1)
	$(UV) run --package arl-api alembic -c apps/api/alembic.ini revision \
		--autogenerate -m "$(MSG)"

migrate-history: ## Show migration history
	$(UV) run --package arl-api alembic -c apps/api/alembic.ini history

migrate-current: ## Show current migration revision
	$(UV) run --package arl-api alembic -c apps/api/alembic.ini current

# ─────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────
build: ## Build all packages
	$(UV) build --all-packages
	$(PNPM) --filter @arl/dashboard build

build-containers: ## Build Docker images
	$(COMPOSE) build

# ─────────────────────────────────────────────
# Security scanning
# ─────────────────────────────────────────────
scan-secrets: ## Scan for committed secrets
	@command -v gitleaks >/dev/null 2>&1 || (echo "Install gitleaks: https://github.com/gitleaks/gitleaks"; exit 1)
	gitleaks detect --source . -v

scan-deps: ## Audit Python dependencies for vulnerabilities
	$(UV) run pip-audit

scan-containers: ## Scan container images with Trivy
	@command -v trivy >/dev/null 2>&1 || (echo "Install Trivy: https://trivy.dev"; exit 1)
	trivy image arl-api:latest
	trivy image arl-worker:latest

sbom: ## Generate SBOM
	$(UV) run cyclonedx-py environment -o sbom.json

# ─────────────────────────────────────────────
# Scenario validation
# ─────────────────────────────────────────────
validate-scenarios: ## Validate all scenario YAML files
	$(UV) run python -m arl.scenario_engine.cli validate scenarios/

# ─────────────────────────────────────────────
# Doctor
# ─────────────────────────────────────────────
doctor: ## Check development environment health
	@echo "Checking development environment..."
	@command -v uv >/dev/null 2>&1 && echo "✓ uv found" || echo "✗ uv missing"
	@command -v docker >/dev/null 2>&1 && echo "✓ docker found" || echo "✗ docker missing"
	@command -v docker compose >/dev/null 2>&1 && echo "✓ docker compose found" || echo "✗ docker compose missing"
	@command -v pnpm >/dev/null 2>&1 && echo "✓ pnpm found" || echo "✗ pnpm missing"
	@command -v git >/dev/null 2>&1 && echo "✓ git found" || echo "✗ git missing"
	@echo ""
	@echo "Run 'make install' to install dependencies."
	@echo "Run 'make dev' to start the development stack."

# ─────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────
clean: ## Remove build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "coverage.xml" -delete 2>/dev/null || true
	@echo "✓ Cleaned build artifacts"
