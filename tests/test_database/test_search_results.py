"""Tests for SearchResult database persistence."""

import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from src.database.db import close_db, get_session, init_db, insert_search_results
from src.database.models import Base, SearchResult
from src.utils.config import reset_settings

# Mark all tests in this file as integration tests requiring PostgreSQL
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require PostgreSQL - set RUN_INTEGRATION_TESTS=1",
)


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables before each test."""
    os.environ["APP_NAME"] = "test-app"
    os.environ["ENVIRONMENT"] = "development"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/testdb"
    os.environ["DB_MAX_RETRIES"] = "3"
    os.environ["DB_RETRY_DELAY"] = "0.1"

    # Reset settings and database state before each test
    reset_settings()
    close_db()

    yield

    # Cleanup after test
    close_db()
    reset_settings()


@pytest.fixture(scope="function")
def db_session():
    """Provide a clean database session for each test."""
    # Initialize database
    init_db()

    # Create tables
    from src.database.db import get_engine

    engine = get_engine()
    Base.metadata.create_all(engine)

    # Yield session context manager
    yield get_session

    # Cleanup: drop all tables
    Base.metadata.drop_all(engine)


def test_insert_valid_search_results(db_session):
    """Test inserting valid normalized search results."""
    results = [
        {
            "title": "AI Trends 2024",
            "summary": "Analysis of AI trends",
            "url": "https://example.com/ai-trends",
            "source": "tavily",
            "published_at": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            "raw": {"original": "data", "score": 95},
        },
        {
            "title": "Machine Learning News",
            "summary": "Latest ML developments",
            "url": "https://example.com/ml-news",
            "source": "hackernews",
            "published_at": None,
            "raw": {"id": 12345, "points": 100},
        },
    ]

    with db_session() as session:
        count = insert_search_results(session, results)

    assert count == 2

    # Verify results persisted
    with db_session() as session:
        saved_results = session.execute(select(SearchResult)).scalars().all()
        assert len(saved_results) == 2

        # Check first result
        result1 = next(r for r in saved_results if r.source == "tavily")
        assert result1.title == "AI Trends 2024"
        assert result1.summary == "Analysis of AI trends"
        assert result1.url == "https://example.com/ai-trends"
        assert result1.published_at == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        assert result1.raw == {"original": "data", "score": 95}
        assert result1.created_at is not None

        # Check second result
        result2 = next(r for r in saved_results if r.source == "hackernews")
        assert result2.title == "Machine Learning News"
        assert result2.published_at is None
        assert result2.raw == {"id": 12345, "points": 100}


def test_insert_duplicate_search_results_ignored(db_session):
    """Test that duplicate (source, url) entries are ignored."""
    original = {
        "title": "Original Title",
        "summary": "Original summary",
        "url": "https://example.com/article",
        "source": "arxiv",
        "published_at": None,
        "raw": {"version": 1},
    }

    duplicate = {
        "title": "Updated Title",  # Different title
        "summary": "Updated summary",  # Different summary
        "url": "https://example.com/article",  # Same URL
        "source": "arxiv",  # Same source
        "published_at": datetime(2024, 1, 20, tzinfo=timezone.utc),
        "raw": {"version": 2},
    }

    # Insert original
    with db_session() as session:
        count1 = insert_search_results(session, [original])

    assert count1 == 1

    # Try to insert duplicate
    with db_session() as session:
        count2 = insert_search_results(session, [duplicate])

    assert count2 == 0  # Duplicate ignored

    # Verify only original persisted
    with db_session() as session:
        saved_results = session.execute(select(SearchResult)).scalars().all()
        assert len(saved_results) == 1
        assert saved_results[0].title == "Original Title"  # Original data preserved
        assert saved_results[0].raw == {"version": 1}


def test_insert_batch_with_mixed_valid_and_duplicate(db_session):
    """Test batch insert with mix of new and duplicate results."""
    # Insert initial results
    initial = [
        {
            "title": "Result 1",
            "summary": "Summary 1",
            "url": "https://example.com/1",
            "source": "tavily",
            "published_at": None,
            "raw": {},
        },
        {
            "title": "Result 2",
            "summary": "Summary 2",
            "url": "https://example.com/2",
            "source": "tavily",
            "published_at": None,
            "raw": {},
        },
    ]

    with db_session() as session:
        count1 = insert_search_results(session, initial)

    assert count1 == 2

    # Batch with 1 new, 1 duplicate, 1 new
    batch = [
        {
            "title": "Result 1",  # Duplicate
            "summary": "Summary 1",
            "url": "https://example.com/1",
            "source": "tavily",
            "published_at": None,
            "raw": {},
        },
        {
            "title": "Result 3",  # New
            "summary": "Summary 3",
            "url": "https://example.com/3",
            "source": "tavily",
            "published_at": None,
            "raw": {},
        },
        {
            "title": "Result 4",  # New
            "summary": "Summary 4",
            "url": "https://example.com/4",
            "source": "tavily",
            "published_at": None,
            "raw": {},
        },
    ]

    with db_session() as session:
        count2 = insert_search_results(session, batch)

    assert count2 == 2  # Only 2 new inserted

    # Verify total
    with db_session() as session:
        total = session.execute(select(SearchResult)).scalars().all()
        assert len(total) == 4


def test_insert_raw_payload_stored_exactly(db_session):
    """Test that raw JSONB payload is stored exactly as provided."""
    complex_raw = {
        "nested": {"data": {"deeply": {"nested": True}}},
        "list": [1, 2, 3, "four"],
        "unicode": "Hello 世界 🌍",
        "special_chars": "quotes\"and'apostrophes",
        "numbers": {"int": 42, "float": 3.14, "negative": -100},
        "boolean": True,
        "null_value": None,
    }

    result = {
        "title": "Test",
        "summary": "Test",
        "url": "https://example.com/test",
        "source": "test",
        "published_at": None,
        "raw": complex_raw,
    }

    with db_session() as session:
        count = insert_search_results(session, [result])

    assert count == 1

    # Verify raw payload preserved exactly
    with db_session() as session:
        saved = session.execute(select(SearchResult)).scalar_one()
        assert saved.raw == complex_raw
        assert saved.raw["nested"]["data"]["deeply"]["nested"] is True
        assert saved.raw["unicode"] == "Hello 世界 🌍"
        assert saved.raw["null_value"] is None


def test_insert_published_at_none_handled(db_session):
    """Test that published_at correctly handles None values."""
    results = [
        {
            "title": "With Date",
            "summary": "Has date",
            "url": "https://example.com/1",
            "source": "test",
            "published_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "raw": {},
        },
        {
            "title": "Without Date",
            "summary": "No date",
            "url": "https://example.com/2",
            "source": "test",
            "published_at": None,
            "raw": {},
        },
    ]

    with db_session() as session:
        count = insert_search_results(session, results)

    assert count == 2

    with db_session() as session:
        saved = session.execute(select(SearchResult)).scalars().all()
        with_date = next(r for r in saved if r.url.endswith("/1"))
        without_date = next(r for r in saved if r.url.endswith("/2"))

        assert with_date.published_at == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert without_date.published_at is None


def test_insert_missing_required_field_raises_error(db_session):
    """Test that missing required fields raise ValueError."""
    # Missing title
    result_missing_title = {
        "summary": "Summary",
        "url": "https://example.com",
        "source": "test",
        "raw": {},
    }

    with db_session() as session:
        with pytest.raises(ValueError, match="Missing required field"):
            insert_search_results(session, [result_missing_title])

    # Missing url
    result_missing_url = {
        "title": "Title",
        "summary": "Summary",
        "source": "test",
        "raw": {},
    }

    with db_session() as session:
        with pytest.raises(ValueError, match="Missing required field"):
            insert_search_results(session, [result_missing_url])

    # Missing raw
    result_missing_raw = {
        "title": "Title",
        "summary": "Summary",
        "url": "https://example.com",
        "source": "test",
    }

    with db_session() as session:
        with pytest.raises(ValueError, match="Missing required field"):
            insert_search_results(session, [result_missing_raw])


def test_insert_invalid_input_type_raises_error(db_session):
    """Test that non-list input raises ValueError."""
    with db_session() as session:
        with pytest.raises(ValueError, match="must be a list"):
            insert_search_results(session, "not a list")

    with db_session() as session:
        with pytest.raises(ValueError, match="must be a list"):
            insert_search_results(session, {"dict": "not list"})


def test_insert_empty_list_returns_zero(db_session):
    """Test that empty list returns count of 0."""
    with db_session() as session:
        count = insert_search_results(session, [])

    assert count == 0


def test_insert_different_sources_same_url_allowed(db_session):
    """Test that same URL from different sources is allowed."""
    results = [
        {
            "title": "Article from Tavily",
            "summary": "Summary",
            "url": "https://example.com/article",
            "source": "tavily",
            "published_at": None,
            "raw": {},
        },
        {
            "title": "Article from HN",
            "summary": "Summary",
            "url": "https://example.com/article",  # Same URL
            "source": "hackernews",  # Different source
            "published_at": None,
            "raw": {},
        },
    ]

    with db_session() as session:
        count = insert_search_results(session, results)

    assert count == 2  # Both should be inserted

    with db_session() as session:
        saved = session.execute(select(SearchResult)).scalars().all()
        assert len(saved) == 2
        sources = {r.source for r in saved}
        assert sources == {"tavily", "hackernews"}


def test_no_session_leak_on_error(db_session):
    """Test that sessions don't leak when errors occur."""
    invalid_results = [
        {
            "title": "Missing url field",
            "summary": "Summary",
            "source": "test",
            "raw": {},
        }
    ]

    # This should raise an error
    with pytest.raises(ValueError):
        with db_session() as session:
            insert_search_results(session, invalid_results)

    # Session should be properly closed, so we can create a new one
    with db_session() as session:
        # This should work without issues
        count = session.execute(select(SearchResult)).scalars().all()
        assert len(count) == 0


def test_session_isolation(db_session):
    """Test that multiple sessions are properly isolated."""
    result = {
        "title": "Test",
        "summary": "Summary",
        "url": "https://example.com/test",
        "source": "test",
        "published_at": None,
        "raw": {},
    }

    # Insert in first session
    with db_session() as session1:
        count = insert_search_results(session1, [result])
        assert count == 1

    # Query in second session
    with db_session() as session2:
        saved = session2.execute(select(SearchResult)).scalars().all()
        assert len(saved) == 1

    # Verify in third session
    with db_session() as session3:
        saved = session3.execute(select(SearchResult)).scalars().all()
        assert len(saved) == 1
        assert saved[0].title == "Test"


def test_created_at_timestamp_auto_generated(db_session):
    """Test that created_at is automatically set."""
    result = {
        "title": "Test",
        "summary": "Summary",
        "url": "https://example.com/test",
        "source": "test",
        "published_at": None,
        "raw": {},
    }

    before_insert = datetime.now(timezone.utc)

    with db_session() as session:
        insert_search_results(session, [result])

    after_insert = datetime.now(timezone.utc)

    with db_session() as session:
        saved = session.execute(select(SearchResult)).scalar_one()
        assert saved.created_at is not None
        assert before_insert <= saved.created_at <= after_insert


def test_uuid_id_auto_generated(db_session):
    """Test that UUID id is automatically generated."""
    result = {
        "title": "Test",
        "summary": "Summary",
        "url": "https://example.com/test",
        "source": "test",
        "published_at": None,
        "raw": {},
    }

    with db_session() as session:
        insert_search_results(session, [result])

    with db_session() as session:
        saved = session.execute(select(SearchResult)).scalar_one()
        assert saved.id is not None
        # Verify it's a valid UUID format
        assert len(str(saved.id)) == 36  # UUID string format
        assert str(saved.id).count("-") == 4  # UUID has 4 hyphens
