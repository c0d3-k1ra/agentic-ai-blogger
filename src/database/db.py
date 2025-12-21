"""PostgreSQL database connection layer with SQLAlchemy."""

import time
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, exc, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.utils.config import get_settings
from src.utils.logging_config import get_logger

# Global engine and session factory
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class DatabaseError(Exception):
    """Base exception for database errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class DatabaseRetryError(DatabaseError):
    """Exception raised when all retry attempts are exhausted."""
    pass


def _get_logger():
    """Get logger instance lazily to avoid import-time config loading."""
    return get_logger(__name__)


def _is_transient_error(error: Exception) -> bool:
    """
    Check if the error is transient and should be retried.
    
    Args:
        error: The exception to check
        
    Returns:
        True if the error is transient, False otherwise
    """
    # SQLAlchemy operational errors are usually transient
    if isinstance(error, exc.OperationalError):
        return True
    
    # Check error message for common transient issues
    error_str = str(error).lower()
    transient_keywords = [
        "connection refused",
        "connection reset",
        "connection timed out",
        "server closed the connection",
        "could not connect",
        "connection lost",
        "deadlock",
        "lock timeout",
        "connection pool exhausted",
    ]
    
    return any(keyword in error_str for keyword in transient_keywords)


def retry_on_transient_error(max_retries: int | None = None, delay: float | None = None):
    """
    Decorator to retry database operations on transient errors.
    
    Args:
        max_retries: Maximum number of retry attempts (uses config default if None)
        delay: Initial delay between retries in seconds (uses config default if None)
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            settings = get_settings()
            retries = max_retries if max_retries is not None else settings.DB_MAX_RETRIES
            retry_delay = delay if delay is not None else settings.DB_RETRY_DELAY
            
            last_error = None
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    if not _is_transient_error(e):
                        # Not a transient error, don't retry
                        _get_logger().error(f"Non-transient database error: {e}")
                        raise
                    
                    if attempt < retries:
                        # Calculate exponential backoff
                        wait_time = retry_delay * (2 ** attempt)
                        _get_logger().warning(
                            f"Transient database error (attempt {attempt + 1}/{retries + 1}): {e}. "
                            f"Retrying in {wait_time:.2f}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        _get_logger().error(
                            f"All {retries + 1} retry attempts exhausted for database operation"
                        )
            
            # All retries exhausted
            raise DatabaseRetryError(
                f"Failed after {retries + 1} attempts. Last error: {last_error}"
            ) from last_error
        
        return wrapper
    return decorator


def init_db() -> None:
    """
    Initialize database engine and session factory.
    
    Creates the SQLAlchemy engine with connection pooling and
    configures the session factory.
    
    Raises:
        DatabaseConnectionError: If DATABASE_URL is not configured
        DatabaseError: If engine creation fails
    """
    global _engine, _session_factory
    
    settings = get_settings()
    database_url = settings.get_database_url()
    
    if not database_url:
        raise DatabaseConnectionError(
            "DATABASE_URL is not configured. Please set it in environment variables."
        )
    
    try:
        _get_logger().info("Initializing database connection...")
        
        # Create engine with connection pooling
        _engine = create_engine(
            database_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_pre_ping=True,  # Verify connections before using them
            echo=settings.DEBUG,  # Log SQL queries in debug mode
        )
        
        # Create session factory
        _session_factory = sessionmaker(
            bind=_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        
        _get_logger().info("Database initialized successfully")
        
    except Exception as e:
        _get_logger().error(f"Failed to initialize database: {e}")
        raise DatabaseError(f"Database initialization failed: {e}") from e


def get_engine() -> Engine:
    """
    Get the SQLAlchemy engine instance.
    
    Returns:
        The initialized engine
        
    Raises:
        DatabaseError: If engine is not initialized
    """
    if _engine is None:
        raise DatabaseError(
            "Database engine not initialized. Call init_db() first."
        )
    return _engine


@contextmanager
@retry_on_transient_error()
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Automatically handles session lifecycle:
    - Creates session
    - Commits on success
    - Rolls back on error
    - Closes session
    
    Usage:
        with get_session() as session:
            # Use session for database operations
            result = session.execute(...)
    
    Yields:
        Database session
        
    Raises:
        DatabaseError: If session factory is not initialized
        DatabaseRetryError: If all retry attempts fail
    """
    if _session_factory is None:
        raise DatabaseError(
            "Database session factory not initialized. Call init_db() first."
        )
    
    session = _session_factory()
    try:
        yield session
        session.commit()
        _get_logger().debug("Database session committed successfully")
    except Exception as e:
        session.rollback()
        _get_logger().error(f"Database session rolled back due to error: {e}")
        raise
    finally:
        session.close()
        _get_logger().debug("Database session closed")


@retry_on_transient_error()
def health_check() -> bool:
    """
    Check database connectivity.
    
    Performs a simple query to verify the database connection is working.
    
    Returns:
        True if database is accessible, False otherwise
        
    Raises:
        DatabaseError: If engine is not initialized
        DatabaseRetryError: If all retry attempts fail
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            _get_logger().info("Database health check passed")
            return True
    except Exception as e:
        _get_logger().error(f"Database health check failed: {e}")
        raise


def close_db() -> None:
    """
    Close database connections and cleanup resources.
    
    Disposes of the engine and clears global state.
    """
    global _engine, _session_factory
    
    if _engine is not None:
        _get_logger().info("Closing database connections...")
        _engine.dispose()
        _engine = None
        _session_factory = None
        _get_logger().info("Database connections closed")
