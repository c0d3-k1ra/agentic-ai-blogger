"""Shared fixtures for integration tests."""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_integration_env():
    """Ensure required environment variables are set for integration tests."""
    # Set defaults if not already set
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
    os.environ.setdefault("APP_NAME", "test-app")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("DB_MAX_RETRIES", "3")
    os.environ.setdefault("DB_RETRY_DELAY", "0.1")

    yield
