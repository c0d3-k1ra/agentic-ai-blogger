"""PostgreSQL database connection layer with SQLAlchemy."""

import time
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, exc, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Article, SearchResult, Topic
from src.utils.config import get_settings
from src.utils.logging_config import get_logger

# Global engine and session factory
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class DatabaseError(Exception):
    """Base exception for database errors."""


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""


class DatabaseRetryError(DatabaseError):
    """Exception raised when all retry attempts are exhausted."""


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
                        _get_logger().error("Non-transient database error: %s", e)
                        raise

                    if attempt < retries:
                        # Calculate exponential backoff
                        wait_time = retry_delay * (2**attempt)
                        _get_logger().warning(
                            "Transient database error (attempt %d/%d): %s. Retrying in %.2fs...",
                            attempt + 1,
                            retries + 1,
                            e,
                            wait_time,
                        )
                        time.sleep(wait_time)
                    else:
                        _get_logger().error(
                            "All %d retry attempts exhausted for database operation", retries + 1
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
        _get_logger().error("Failed to initialize database: %s", e)
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
        raise DatabaseError("Database engine not initialized. Call init_db() first.")
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
        raise DatabaseError("Database session factory not initialized. Call init_db() first.")

    session = _session_factory()
    try:
        yield session
        session.commit()
        _get_logger().debug("Database session committed successfully")
    except Exception as e:
        session.rollback()
        _get_logger().error("Database session rolled back due to error: %s", e)
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
        _get_logger().error("Database health check failed: %s", e)
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


# ============================================================================
# CRUD Helpers
# ============================================================================


def create_topic(
    session: Session,
    *,
    name: str,
    description: str | None = None,
    keywords: list | None = None,
    metadata: dict | None = None,
) -> Topic:
    """
    Create a new topic.

    Args:
        session: SQLAlchemy session (caller must commit)
        name: Unique topic name
        description: Optional description
        keywords: Optional list (DB default: [])
        metadata: Optional dict (DB default: {})

    Returns:
        Created Topic instance

    Raises:
        IntegrityError: If name already exists
    """
    topic = Topic(
        name=name,
        description=description,
        keywords=keywords if keywords is not None else [],
        meta_data=metadata if metadata is not None else {},
    )
    session.add(topic)
    session.flush()
    session.refresh(topic)
    return topic


def get_topic_by_id(session: Session, topic_id) -> Topic | None:
    """
    Get topic by ID.

    Args:
        session: SQLAlchemy session
        topic_id: Topic ID (UUID)

    Returns:
        Topic instance or None if not found
    """
    return session.get(Topic, topic_id)


def get_topic_by_name(session: Session, name: str) -> Topic | None:
    """
    Get topic by name.

    Args:
        session: SQLAlchemy session
        name: Topic name

    Returns:
        Topic instance or None if not found
    """
    return session.query(Topic).filter(Topic.name == name).first()


def update_topic(session: Session, topic_id, **fields) -> Topic:
    """
    Update topic fields.

    Args:
        session: SQLAlchemy session (caller must commit)
        topic_id: Topic ID (UUID)
        **fields: Fields to update (name, description, keywords, metadata)

    Returns:
        Updated Topic instance

    Raises:
        ValueError: If topic not found or unknown field provided
    """
    topic = session.get(Topic, topic_id)
    if not topic:
        raise ValueError(f"Topic with id {topic_id} not found")

    allowed_fields = {"name", "description", "keywords", "metadata"}
    unknown = set(fields.keys()) - allowed_fields
    if unknown:
        raise ValueError(f"Unknown fields: {unknown}")

    for key, value in fields.items():
        if key == "metadata":
            topic.meta_data = value
        else:
            setattr(topic, key, value)

    session.flush()
    session.refresh(topic)
    return topic


def create_article(
    session: Session,
    *,
    topic_id,
    title: str,
    content: str | None = None,
    metadata: dict | None = None,
) -> Article:
    """
    Create a new article.

    Args:
        session: SQLAlchemy session (caller must commit)
        topic_id: Valid topic ID (FK enforced)
        title: Article title
        content: Optional content (can be None)
        metadata: Optional dict (DB default: {})

    Returns:
        Created Article instance

    Raises:
        IntegrityError: If topic_id doesn't exist
    """
    article = Article(
        topic_id=topic_id,
        title=title,
        content=content if content is not None else "",
        meta_data=metadata if metadata is not None else {},
    )
    session.add(article)
    session.flush()
    session.refresh(article)
    return article


def insert_search_results(session: Session, results: list[dict]) -> int:
    """
    Insert normalized search results using bulk insert.
    Duplicates (based on source, url) are automatically ignored via ON CONFLICT.

    Args:
        session: SQLAlchemy session (caller must commit)
        results: List of normalized result dicts with keys:
                 title, summary, url, source, published_at, raw

    Returns:
        Number of rows successfully inserted

    Raises:
        ValueError: If results is not a list or contains invalid data
    """
    if not isinstance(results, list):
        raise ValueError("results must be a list")

    if not results:
        return 0

    # Validate required fields before attempting insert
    required_fields = {"title", "summary", "url", "source", "raw"}
    for result in results:
        missing = required_fields - set(result.keys())
        if missing:
            raise ValueError(f"Missing required field: {missing.pop()}")

    # Bulk insert with ON CONFLICT DO NOTHING
    # This leverages the unique constraint (source, url) at the database level
    stmt = insert(SearchResult).values(results)
    stmt = stmt.on_conflict_do_nothing(index_elements=["source", "url"])

    result = session.execute(stmt)
    inserted_count = result.rowcount

    _get_logger().debug("Inserted %d search results (duplicates ignored)", inserted_count)

    return inserted_count


def get_article_by_id(session: Session, article_id) -> Article | None:
    """
    Get article by ID.

    Args:
        session: SQLAlchemy session
        article_id: Article ID (UUID)

    Returns:
        Article instance or None if not found
    """
    return session.get(Article, article_id)


def update_article(session: Session, article_id, **fields) -> Article:
    """
    Update article fields.

    Args:
        session: SQLAlchemy session (caller must commit)
        article_id: Article ID (UUID)
        **fields: Fields to update (title, content, metadata, status, published_at)

    Returns:
        Updated Article instance

    Raises:
        ValueError: If article not found or unknown field provided
    """
    article = session.get(Article, article_id)
    if not article:
        raise ValueError(f"Article with id {article_id} not found")

    allowed_fields = {"title", "content", "metadata", "status", "published_at"}
    unknown = set(fields.keys()) - allowed_fields
    if unknown:
        raise ValueError(f"Unknown fields: {unknown}")

    for key, value in fields.items():
        if key == "metadata":
            article.meta_data = value
        else:
            setattr(article, key, value)

    session.flush()
    session.refresh(article)
    return article
