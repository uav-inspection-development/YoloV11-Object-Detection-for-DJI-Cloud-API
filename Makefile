.PHONY: help install install-dev lint type-check test format security check check-all clean

help:
	@echo "Available commands:"
	@echo "  install      Install production dependencies"
	@echo "  install-dev  Install development dependencies"
	@echo "  lint         Run flake8 linting"
	@echo "  type-check   Run mypy type checking"
	@echo "  test         Run pytest tests"
	@echo "  format       Format code with black and isort"
	@echo "  security     Run security checks (bandit + safety)"
	@echo "  check        Run all checks (lint + type-check + test)"
	@echo "  check-all    Run all checks including security"
	@echo "  clean        Clean up cache files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

lint:
	flake8 src

type-check:
	mypy src

test:
	pytest tests/ --cov=src --cov-report=term-missing

format:
	black src tests
	isort src tests

security:
	bandit -r src
	safety check

check: lint type-check test
	@echo "All checks passed!"

check-all: lint type-check test security
	@echo "All checks including security passed!"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.pyd" -delete
	find . -name ".coverage" -delete
	find . -name "*.cover" -delete
