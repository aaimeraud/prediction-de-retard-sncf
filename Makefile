.PHONY: help install dev test test-coverage lint type-check security clean docker docker-run docker-compose-up docker-compose-down

help:
	@echo "SNCF Delay Prediction ML - Development Commands"
	@echo "================================================"
	@echo ""
	@echo "Environment Setup:"
	@echo "  make install          - Install dependencies (pip3)"
	@echo "  make dev              - Install dev dependencies"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             - Run all tests (pytest)"
	@echo "  make test-coverage    - Run tests with coverage report"
	@echo "  make lint             - Run code linting (flake8)"
	@echo "  make type-check       - Run type checking (mypy)"
	@echo "  make security         - Run security checks (bandit)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker           - Build Docker image"
	@echo "  make docker-run       - Run Docker image interactively"
	@echo "  make docker-test      - Run tests in Docker"
	@echo "  make docker-compose-up   - Start services (docker-compose)"
	@echo "  make docker-compose-down - Stop services"
	@echo ""
	@echo "Utilities:"
	@echo "  make format           - Format code (autopep8)"
	@echo "  make clean            - Remove cache and build artifacts"
	@echo "  make docs             - Generate documentation"

install:
	@echo "Installing production dependencies..."
	python3 -m pip install --upgrade pip
	pip3 install -r requirements.txt

dev:
	@echo "Installing development dependencies..."
	pip3 install -r requirements.txt
	pip3 install pytest pytest-cov flake8 mypy autopep8 bandit black

test:
	@echo "Running tests..."
	python3 -m pytest tests/ -v --tb=short

test-coverage:
	@echo "Running tests with coverage..."
	python3 -m pytest tests/ -v --tb=short --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	@echo "Running linting checks..."
	flake8 src/ tests/ --max-line-length=100 --exclude=__pycache__,*.pyc
	@echo "✓ Linting passed"

type-check:
	@echo "Running type checking..."
	mypy src/ --ignore-missing-imports
	@echo "✓ Type checking passed"

security:
	@echo "Running security checks..."
	bandit -r src/ -ll
	safety check
	@echo "✓ Security checks passed"

format:
	@echo "Formatting code..."
	autopep8 --in-place --aggressive --aggressive -r src/ tests/
	black src/ tests/ --line-length=100
	@echo "✓ Formatting complete"

clean:
	@echo "Cleaning cache and build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'htmlcov' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.coverage' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info
	@echo "✓ Cleanup complete"

docker:
	@echo "Building Docker image..."
	docker build -f Dockerfile -t sncf-delay-prediction:latest .
	@echo "✓ Docker image built: sncf-delay-prediction:latest"

docker-run:
	@echo "Running Docker container..."
	docker run -it --rm \
		-p 8888:8888 \
		-p 5000:5000 \
		-p 8501:8501 \
		-v $(PWD):/app \
		sncf-delay-prediction:latest \
		bash

docker-test:
	@echo "Running tests in Docker..."
	docker run --rm \
		-v $(PWD):/app \
		sncf-delay-prediction:latest \
		python3 -m pytest tests/ -v --tb=short

docker-compose-up:
	@echo "Starting services with docker-compose..."
	docker-compose -f compose.yaml up -d
	@echo "✓ Services started"
	@echo "  Jupyter Lab: http://localhost:8888"
	@echo "  FastAPI: http://localhost:5000/docs"
	@echo "  Streamlit: http://localhost:8501"

docker-compose-down:
	@echo "Stopping services..."
	docker-compose -f compose.yaml down
	@echo "✓ Services stopped"

docs:
	@echo "Generating documentation..."
	@echo "Documentation files:"
	@ls -1 docs/*.md | sed 's/^/  /'

.DEFAULT_GOAL := help
