.PHONY: help install dev test lint format type-check clean build run docker-build docker-up docker-down frontend frontend-dev

UV ?= uv

help:
	@echo "TSP-PTSP Solver - Available commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install dependencies"
	@echo "  make dev           Install with dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run          Run development server (backend)"
	@echo "  make frontend     Run Streamlit frontend"
	@echo "  make frontend-dev Run frontend in dev mode"
	@echo "  make test         Run tests"
	@echo "  make test-cov     Run tests with coverage"
	@echo "  make lint         Run code linting"
	@echo "  make format       Format code with black"
	@echo "  make type-check   Run type checking with mypy"
	@echo ""
	@echo "Quality:"
	@echo "  make quality      Run all quality checks"
	@echo "  make clean        Remove build artifacts and cache"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-up    Start Docker containers (backend + frontend)"
	@echo "  make docker-down  Stop Docker containers"
	@echo "  make docker-logs  View Docker logs"

# Setup
install:
	$(UV) sync

dev:
	$(UV) sync --extra dev

# Development
run:
	$(UV) run python run.py

frontend:
	$(UV) run streamlit run streamlit_app.py

frontend-dev:
	$(UV) run streamlit run streamlit_app.py --logger.level=debug --client.showErrorDetails=true

test: dev
	$(UV) run pytest tests/ -v

test-cov: dev
	$(UV) run pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

lint: dev
	$(UV) run ruff check src/ tests/

format: dev
	$(UV) run black src/ tests/
	$(UV) run isort src/ tests/

type-check: dev
	$(UV) run mypy src/ --strict

quality: lint type-check test

# Cleanup
clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov __pycache__ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Docker
docker-build:
	docker-compose build

docker-up:
	@echo "Starting services..."
	@echo "Backend will be available at: http://localhost:8000"
	@echo "Frontend will be available at: http://localhost:8501"
	docker-compose up

docker-up-d:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-rebuild:
	docker-compose down
	docker build -t tsp-ptsp-solver:latest .
	docker-compose up -d

# Build
build: clean
	$(UV) run python -m build

# Default
.DEFAULT_GOAL := help
