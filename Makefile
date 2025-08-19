.PHONY: help install install-dev test lint format clean build

help:
	@echo "Available commands:"
	@echo "  make install      Install package in production mode"
	@echo "  make install-dev  Install package in development mode"
	@echo "  make test        Run tests"
	@echo "  make lint        Run linters"
	@echo "  make format      Format code"
	@echo "  make clean       Clean build artifacts"
	@echo "  make build       Build distribution packages"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v --cov=shpi --cov-report=term-missing

lint:
	ruff check shpi tests
	mypy shpi

format:
	black shpi tests
	ruff check --fix shpi tests

clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .coverage .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build