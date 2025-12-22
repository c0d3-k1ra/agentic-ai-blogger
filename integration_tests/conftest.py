"""Shared fixtures for integration tests."""

import os

import pytest

from src.database.db import close_db, get_engine, init_db
from src.database.models import Base
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


@pytest.fixture(scope="function")
def db_session():
    """Provide a clean database session for each test.

    This fixture:
    - Initializes the database connection
    - Creates all tables
    - Provides a session for the test
    - Cleans up by dropping tables after the test
    """
    # Initialize database
    init_db()

    # Create tables
    engine = get_engine()
    Base.metadata.create_all(engine)

    # Create session using sessionmaker
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(engine)
