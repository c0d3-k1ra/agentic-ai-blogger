.PHONY: test test-unit test-integration test-all clean-db help

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

test: test-unit ## Run unit tests (default)

test-unit: ## Run unit tests only (fast, no PostgreSQL needed)
	@echo "🧪 Running unit tests..."
	poetry run pytest tests/ -v

test-integration: ## Run integration tests (requires Docker for PostgreSQL)
	@echo "🧪 Running integration tests..."
	./scripts/run_integration_tests.sh

test-all: test-unit test-integration ## Run all tests (unit + integration)
	@echo "✅ All tests complete"

test-coverage: ## Run unit tests with coverage report
	@echo "🧪 Running unit tests with coverage..."
	poetry run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

clean-db: ## Clean up test database container
	@echo "🧹 Cleaning up test database container..."
	@docker stop postgres-test 2>/dev/null || true
	@docker rm postgres-test 2>/dev/null || true
	@echo "✅ Cleanup complete"

lint: ## Run ruff linting
	@echo "🔍 Running ruff linting..."
	poetry run ruff check

format: ## Run ruff formatting
	@echo "✨ Formatting code..."
	poetry run ruff format

format-check: ## Check code formatting without making changes
	@echo "🔍 Checking code formatting..."
	poetry run ruff format --check

install: ## Install project dependencies
	@echo "📦 Installing dependencies..."
	poetry install

.DEFAULT_GOAL := help
