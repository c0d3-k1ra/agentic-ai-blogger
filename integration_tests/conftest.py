"""Shared fixtures for integration tests."""

import os

import pytest

from src.database.db import close_db, get_engine, init_db
from src.utils.config import reset_settings


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


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables before each test."""
    # Reset settings and database state before each test
    reset_settings()
    close_db()

    yield

    # Cleanup after test
    close_db()
    reset_settings()


@pytest.fixture(scope="session", autouse=True)
def clean_database_before_tests():
    """Clean database once before all tests start."""
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    init_db()
    SessionLocal = sessionmaker(bind=get_engine())
    session = SessionLocal()

    try:
        # Clean any leftover data from previous test runs
        session.execute(text("TRUNCATE topics, articles, search_results RESTART IDENTITY CASCADE"))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
        close_db()

    yield


@pytest.fixture(scope="function")
def db_session():
    """Provide a clean database session for each test.

    This fixture assumes the schema already exists (created by run_integration_tests.sh
    or CI pipeline via 'alembic upgrade head'). After each test, all tables are
    truncated to ensure a clean state for the next test.

    Benefits:
    - Fast: TRUNCATE is much faster than DELETE
    - Clean: Each test starts with empty tables
    - Isolated: Tests don't affect each other
    - Realistic: Tests can use commit() like production code
    """
    # Initialize database connection
    init_db()

    # Create session
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=get_engine())
    session = SessionLocal()

    yield session

    # Clean up: truncate all tables to remove test data
    # CASCADE handles foreign key constraints
    # RESTART IDENTITY resets sequences
    try:
        session.execute(text("TRUNCATE topics, articles, search_results RESTART IDENTITY CASCADE"))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
