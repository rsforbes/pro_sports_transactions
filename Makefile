# Makefile for Pro Sports Transactions
# This file provides convenient shortcuts for common development tasks
# and ensures consistent quality checks across all contributors

# .PHONY declares these targets don't create files with these names
# This prevents conflicts if files named 'test' or 'clean' exist
.PHONY: format lint test coverage complexity check clean help

# Default target when running just 'make' - shows available commands
# Uses awk to parse targets and their descriptions from ## comments
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Black is our formatter - enforces consistent code style across the project
# Running this before linting prevents style-related lint errors
format:  ## Format code with black
	poetry run black .

# Linting catches potential bugs and enforces code quality standards
# We run both pylint (comprehensive) and flake8 (fast) for maximum coverage
# max-complexity=10 enforces our complexity limit defined in .flake8
lint:  ## Run linting checks (pylint and flake8)
	poetry run pylint src/pro_sports_transactions
	poetry run flake8 --max-complexity=10 .

# Basic test run - fast feedback during development
test:  ## Run tests
	poetry run pytest

# Coverage ensures our tests actually exercise the code
# fail-under=80 enforces our minimum 80% coverage requirement
# term-missing shows which lines aren't covered
coverage:  ## Run tests with coverage report
	poetry run pytest --cov --cov-report=term-missing --cov-fail-under=80

# HTML reports are useful for exploring coverage gaps in detail
# Opens in browser for interactive navigation of uncovered code
coverage-html:  ## Generate HTML coverage report
	poetry run pytest --cov --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Radon provides complexity metrics beyond basic McCabe scores
# -a shows average complexity, -nc excludes low complexity functions
complexity:  ## Check code complexity
	poetry run radon cc src -a -nc
	poetry run radon mi src

# Detailed analysis for refactoring decisions
# Shows all metrics to identify problem areas
complexity-detailed:  ## Detailed complexity analysis
	@echo "=== Cyclomatic Complexity ==="
	poetry run radon cc src -s
	@echo "\n=== Maintainability Index ==="
	poetry run radon mi src -s
	@echo "\n=== Raw Metrics ==="
	poetry run radon raw src -s
	@echo "\n=== Halstead Metrics ==="
	poetry run radon hal src

# Standard quality gate - what every commit must pass
# Runs in order: format, lint, test with coverage
# && ensures we stop on first failure for faster feedback
check:  ## Run all quality checks (format, lint, test, coverage)
	poetry run black . && \
	poetry run pylint src/pro_sports_transactions && \
	poetry run flake8 --max-complexity=10 . && \
	poetry run pytest --cov --cov-report=term-missing --cov-fail-under=80

# Extended checks including complexity for major changes
# -nc shows only complex functions, -nd shows no details (just summary)
check-strict:  ## Run all checks including complexity analysis
	poetry run black . && \
	poetry run pylint src/pro_sports_transactions && \
	poetry run flake8 --max-complexity=10 . && \
	poetry run pytest --cov --cov-report=term-missing --cov-fail-under=80 && \
	poetry run radon cc src -nc -nd

# Basic dependency installation for users
install:  ## Install dependencies
	poetry install

# Development installation includes testing and linting tools
install-dev:  ## Install with dev dependencies
	poetry install --with dev

# Removes all generated files and caches for a clean slate
# Useful when debugging strange issues or before releases
clean:  ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf dist/ build/ *.egg-info htmlcov/ .coverage coverage.xml .pytest_cache/

# Convenience alias - makes intent clear when preparing commits
pre-commit: check  ## Alias for check (use before committing)