# Development task automation for strands-base-agent

# Default recipe to show available commands
default:
    @just --list

# Install dependencies using uv
install:
    uv sync

# Run all tests including integration tests
test:
    uv run pytest

# Run only integration tests (skip unit tests; no coverage gate)
test-integration:
    uv run pytest tests/integration/ --no-cov

# Run only unit tests (skip integration tests)
test-unit:
    uv run pytest tests/unit/

# Run code linting with ruff
lint:
    uv run ruff check
    uv run bandit -c pyproject.toml -r strands_base_agent -t B602,B603,B605,B607

# Auto-fix linting issues with ruff
lint-fix:
    uv run ruff check --fix

# Run code formatting check with ruff
format:
    uv run ruff format --check

# Format code with ruff
format-fix:
    uv run ruff format

# Run pyright type checking
type-check:
    uv run basedpyright

# Advisory dead-code scan with vulture. Not part of `check`/`ci` — expect
# false positives from DI container, FastAPI decorators, and Pydantic models.
dead-code:
    uv run vulture

# Add a package to the project
add-package package:
    uv add "{{package}}"

# Add a development package to the project
add-dev-package package:
    uv add --dev "{{package}}"

# Run all quality checks
check: lint format type-check test

# Run CI quality checks
ci: lint format type-check test

# Run the application demo
demo prompt="Tell me about Python programming":
    uv run python -m strands_base_agent "{{prompt}}"

# Run the agent
run:
    uv run python -m strands_base_agent.server

# Clean build artifacts and tooling caches
clean:
    rm -rf build/
    rm -rf dist/
    rm -rf htmlcov/
    rm -rf *.egg-info/
    rm -rf .pytest_cache/
    rm -rf .ruff_cache/
    rm -f .coverage
    find . -type d -name __pycache__ -prune -exec rm -r {} +
    find . -type f -name "*.pyc" -delete

# Setup development environment
setup: install
    uv tool install pre-commit --with pre-commit-uv
    uv run pre-commit install
