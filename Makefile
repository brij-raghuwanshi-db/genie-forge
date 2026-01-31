.PHONY: help install dev lint fmt test test-integration coverage type-check build clean all

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package in editable mode
	pip install -e .

dev:  ## Install package with dev dependencies
	pip install -e ".[dev]"

lint:  ## Run linting checks (ruff)
	ruff check src tests
	ruff format --check src tests

fmt:  ## Format code with ruff
	ruff format src tests
	ruff check --fix src tests

type-check:  ## Run type checking (mypy)
	mypy src/genie_forge

test:  ## Run unit tests
	pytest tests/unit -v

test-integration:  ## Run integration tests (requires GENIE_PROFILE)
	@if [ -z "$$GENIE_PROFILE" ]; then \
		echo "Error: GENIE_PROFILE environment variable not set"; \
		echo "Usage: GENIE_PROFILE=your-profile make test-integration"; \
		exit 1; \
	fi
	pytest tests/integration -v -m integration

coverage:  ## Run tests with coverage report
	pytest tests/unit --cov=src/genie_forge --cov-report=html --cov-report=term-missing -v
	@echo "Coverage report: htmlcov/index.html"

build:  ## Build distribution packages
	pip install build
	python -m build

clean:  ## Clean build artifacts
	rm -rf build dist *.egg-info src/*.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

all: lint type-check test  ## Run all checks (lint, type-check, test)
