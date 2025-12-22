# Integration Tests

This directory contains integration tests that require external services like PostgreSQL.

## Structure

```
integration_tests/
├── README.md                    # This file
├── conftest.py                  # Shared fixtures and setup
└── test_database/
    ├── __init__.py
    └── test_search_results.py  # PostgreSQL integration tests
```

## Running Integration Tests

### Using the Script (Recommended)

The easiest way to run integration tests locally:

```bash
./scripts/run_integration_tests.sh
```

This script will:
1. Start PostgreSQL in a Docker container if not already running
2. Wait for PostgreSQL to be ready
3. Run all integration tests
4. Report the results

You can pass pytest arguments to the script:

```bash
# Run with verbose output
./scripts/run_integration_tests.sh -v

# Run specific test
./scripts/run_integration_tests.sh -k test_insert_valid

# Stop on first failure
./scripts/run_integration_tests.sh --maxfail=1
```

### Using Make

```bash
# Run integration tests
make test-integration

# Run all tests (unit + integration)
make test-all

# Clean up test database
make clean-db
```

### Manual Setup

If you prefer to manage PostgreSQL yourself:

```bash
# 1. Start PostgreSQL
docker run -d \
  --name postgres-test \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  postgres:17

# 2. Run tests
poetry run pytest integration_tests/ -v

# 3. Stop PostgreSQL (when done)
docker stop postgres-test
docker rm postgres-test
```

## Prerequisites

- Docker (for PostgreSQL container)
- Poetry (for Python dependencies)

## CI/CD

Integration tests run automatically in GitHub Actions with a PostgreSQL service container. See `.github/workflows/ci.yml` for details.

## Adding New Integration Tests

1. Create test file in appropriate subdirectory under `integration_tests/`
2. Import required fixtures from `conftest.py`
3. Write tests that interact with real services (PostgreSQL, etc.)
4. Tests will automatically run in CI

Example:

```python
def test_my_integration(db_session):
    """Test something that needs real PostgreSQL."""
    # Test implementation
    pass
```

## vs Unit Tests

**Unit Tests** (`tests/`):
- Fast, no external dependencies
- Use mocks and in-memory databases
- Run by default with `pytest` or `make test`
- Run on every commit in CI

**Integration Tests** (`integration_tests/`):
- Require real services (PostgreSQL, etc.)
- Test actual integrations
- Run explicitly with `make test-integration`
- Run in separate CI job with service containers
