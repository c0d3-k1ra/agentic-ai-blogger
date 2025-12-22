"""Integration tests for CRUD operations with PostgreSQL.

These tests verify CRUD operations work correctly with a real PostgreSQL database,
without the SQLite workarounds needed in unit tests.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from src.database.db import (
    create_article,
    create_topic,
    get_article_by_id,
    get_topic_by_id,
    get_topic_by_name,
    update_article,
    update_topic,
)

# ============================================================================
# Topic CRUD Tests
# ============================================================================


def test_create_topic_with_all_fields(db_session):
    """Test creating a topic with all fields in PostgreSQL."""
    topic = create_topic(
        db_session,
        name="Python Integration",
        description="Python programming language",
        keywords=["python", "programming", "coding"],
        metadata={"difficulty": "beginner", "category": "programming"},
    )

    db_session.commit()

    assert topic.id is not None
    assert isinstance(topic.id, uuid.UUID)
    assert topic.name == "Python Integration"
    assert topic.description == "Python programming language"
    assert topic.keywords == ["python", "programming", "coding"]
    assert topic.meta_data == {"difficulty": "beginner", "category": "programming"}
    assert topic.created_at is not None
    assert topic.updated_at is not None


def test_topic_jsonb_query_support(db_session):
    """Test PostgreSQL JSONB query capabilities."""
    # Create topics with different metadata
    create_topic(
        db_session,
        name="Beginner Topic",
        metadata={"difficulty": "beginner", "tags": ["tutorial", "basics"]},
    )
    create_topic(
        db_session,
        name="Advanced Topic",
        metadata={"difficulty": "advanced", "tags": ["expert", "deep-dive"]},
    )
    db_session.commit()

    # Query using JSONB operator (column name is 'metadata' not 'meta_data')
    from sqlalchemy import text

    result = db_session.execute(
        text("SELECT name FROM topics WHERE metadata->>'difficulty' = :difficulty"),
        {"difficulty": "beginner"},
    ).fetchall()

    assert len(result) == 1
    assert result[0][0] == "Beginner Topic"


def test_topic_uuid_generation(db_session):
    """Test that PostgreSQL generates valid UUIDs for topics."""
    topic1 = create_topic(db_session, name="Topic 1")
    topic2 = create_topic(db_session, name="Topic 2")
    db_session.commit()

    # Both should have different valid UUIDs
    assert isinstance(topic1.id, uuid.UUID)
    assert isinstance(topic2.id, uuid.UUID)
    assert topic1.id != topic2.id


def test_get_topic_by_name_case_sensitive(db_session):
    """Test that topic name lookup is case-sensitive."""
    create_topic(db_session, name="Python")
    db_session.commit()

    # Exact match should work
    result = get_topic_by_name(db_session, "Python")
    assert result is not None

    # Different case should not match
    result = get_topic_by_name(db_session, "python")
    assert result is None


def test_update_topic_jsonb_metadata(db_session):
    """Test updating JSONB metadata in PostgreSQL."""
    topic = create_topic(db_session, name="Topic", metadata={"version": "1.0"})
    db_session.commit()

    # Update with new metadata
    updated = update_topic(
        db_session,
        topic.id,
        metadata={"version": "2.0", "updated": True, "features": ["a", "b"]},
    )
    db_session.commit()

    # Verify JSONB was completely replaced
    assert updated.meta_data == {"version": "2.0", "updated": True, "features": ["a", "b"]}


def test_create_topic_duplicate_name_fails(db_session):
    """Test that duplicate topic names violate unique constraint."""
    create_topic(db_session, name="Duplicate")
    db_session.commit()

    with pytest.raises(IntegrityError):
        create_topic(db_session, name="Duplicate")
        db_session.commit()


def test_topic_keywords_array_support(db_session):
    """Test PostgreSQL array type for keywords."""
    topic = create_topic(db_session, name="Arrays", keywords=["python", "postgresql", "arrays"])
    db_session.commit()

    # Verify array was stored correctly
    retrieved = get_topic_by_id(db_session, topic.id)
    assert isinstance(retrieved.keywords, list)
    assert len(retrieved.keywords) == 3
    assert "python" in retrieved.keywords


def test_topic_timestamps_auto_generated(db_session):
    """Test that created_at and updated_at are auto-generated."""
    topic = create_topic(db_session, name="Timestamps")
    db_session.commit()

    assert topic.created_at is not None
    assert topic.updated_at is not None
    assert topic.created_at == topic.updated_at


# ============================================================================
# Article CRUD Tests
# ============================================================================


def test_create_article_with_all_fields(db_session):
    """Test creating an article with all fields in PostgreSQL."""
    topic = create_topic(db_session, name="Django Integration")
    db_session.commit()

    article = create_article(
        db_session,
        topic_id=topic.id,
        title="Django REST Framework",
        content="Complete guide to DRF...",
        metadata={"author": "John Doe", "read_time": 10},
    )
    db_session.commit()

    assert article.id is not None
    assert isinstance(article.id, uuid.UUID)
    assert article.topic_id == topic.id
    assert article.title == "Django REST Framework"
    assert article.content == "Complete guide to DRF..."
    assert article.meta_data == {"author": "John Doe", "read_time": 10}
    assert article.status == "draft"
    assert article.published_at is None


def test_article_foreign_key_constraint(db_session):
    """Test that article creation fails with invalid topic_id."""
    invalid_topic_id = uuid.uuid4()

    with pytest.raises(IntegrityError):
        create_article(db_session, topic_id=invalid_topic_id, title="Invalid Article")
        db_session.commit()


def test_article_uuid_generation(db_session):
    """Test that PostgreSQL generates valid UUIDs for articles."""
    topic = create_topic(db_session, name="Topic")
    db_session.commit()

    article1 = create_article(db_session, topic_id=topic.id, title="Article 1")
    article2 = create_article(db_session, topic_id=topic.id, title="Article 2")
    db_session.commit()

    # Both should have valid UUIDs
    assert isinstance(article1.id, uuid.UUID)
    assert isinstance(article2.id, uuid.UUID)
    # UUIDs should be different
    assert article1.id != article2.id


def test_update_article_status(db_session):
    """Test updating article status through workflow."""
    topic = create_topic(db_session, name="Topic")
    article = create_article(db_session, topic_id=topic.id, title="Draft Article")
    db_session.commit()

    # Draft -> In Review
    updated = update_article(db_session, article.id, status="in_review")
    db_session.commit()
    assert updated.status == "in_review"

    # In Review -> Published
    updated = update_article(db_session, article.id, status="published")
    db_session.commit()
    assert updated.status == "published"


def test_article_jsonb_metadata(db_session):
    """Test article JSONB metadata storage and retrieval."""
    topic = create_topic(db_session, name="Topic")
    article = create_article(
        db_session,
        topic_id=topic.id,
        title="Article",
        metadata={
            "tags": ["python", "web"],
            "views": 100,
            "rating": 4.5,
            "featured": True,
        },
    )
    db_session.commit()

    retrieved = get_article_by_id(db_session, article.id)
    assert retrieved.meta_data["tags"] == ["python", "web"]
    assert retrieved.meta_data["views"] == 100
    assert retrieved.meta_data["rating"] == 4.5
    assert retrieved.meta_data["featured"] is True


def test_article_timestamps_auto_generated(db_session):
    """Test that article timestamps are auto-generated."""
    topic = create_topic(db_session, name="Topic")
    article = create_article(db_session, topic_id=topic.id, title="Article")
    db_session.commit()

    assert article.created_at is not None
    assert article.updated_at is not None


# ============================================================================
# Transaction Tests
# ============================================================================


def test_transaction_rollback_on_error(db_session):
    """Test that transaction rolls back on error."""
    # Create a topic
    create_topic(db_session, name="Rollback Test")
    db_session.commit()

    # Start a transaction that will fail
    try:
        create_topic(db_session, name="Topic 1")
        create_topic(db_session, name="Rollback Test")  # Duplicate - will fail
        db_session.commit()
    except IntegrityError:
        db_session.rollback()

    # Topic 1 should not exist (transaction rolled back)
    result = get_topic_by_name(db_session, "Topic 1")
    assert result is None

    # Original topic should still exist
    result = get_topic_by_name(db_session, "Rollback Test")
    assert result is not None


def test_multiple_operations_single_transaction(db_session):
    """Test multiple CRUD operations in a single transaction."""
    # Create topic
    topic = create_topic(db_session, name="Multi-Op")

    # Create article (without commit)
    article = create_article(db_session, topic_id=topic.id, title="Article")

    # Update topic (without commit)
    update_topic(db_session, topic.id, description="Updated")

    # Commit all at once
    db_session.commit()

    # Verify all changes persisted
    retrieved_topic = get_topic_by_id(db_session, topic.id)
    retrieved_article = get_article_by_id(db_session, article.id)

    assert retrieved_topic.description == "Updated"
    assert retrieved_article.title == "Article"


def test_session_isolation(db_session):
    """Test that uncommitted changes are isolated."""
    # Create but don't commit
    create_topic(db_session, name="Uncommitted")

    # Topic visible in same session
    result = get_topic_by_name(db_session, "Uncommitted")
    assert result is not None

    # Rollback
    db_session.rollback()

    # Topic should no longer exist
    result = get_topic_by_name(db_session, "Uncommitted")
    assert result is None


# ============================================================================
# Cascade Behavior Tests
# ============================================================================


def test_topic_deletion_with_articles_fails(db_session):
    """Test that deleting a topic with articles fails (RESTRICT behavior)."""
    # Create topic and articles
    topic = create_topic(db_session, name="To Delete")
    _article1 = create_article(db_session, topic_id=topic.id, title="Article 1")
    _article2 = create_article(db_session, topic_id=topic.id, title="Article 2")
    db_session.commit()

    # Attempting to delete topic should fail due to RESTRICT constraint
    with pytest.raises(IntegrityError):
        db_session.delete(topic)
        db_session.commit()

    # Rollback the failed transaction
    db_session.rollback()

    # Verify topic still exists (articles implicitly exist since delete failed)
    assert get_topic_by_id(db_session, topic.id) is not None


# ============================================================================
# Large Data Tests
# ============================================================================


def test_large_jsonb_storage(db_session):
    """Test storing large JSONB objects."""
    large_metadata = {
        "sections": [{"title": f"Section {i}", "content": f"Content {i}" * 100} for i in range(50)],
        "tags": [f"tag_{i}" for i in range(100)],
        "stats": {f"metric_{i}": i * 100 for i in range(50)},
    }

    topic = create_topic(db_session, name="Large Data", metadata=large_metadata)
    db_session.commit()

    retrieved = get_topic_by_id(db_session, topic.id)
    assert len(retrieved.meta_data["sections"]) == 50
    assert len(retrieved.meta_data["tags"]) == 100


def test_large_text_content(db_session):
    """Test storing large text content in articles."""
    topic = create_topic(db_session, name="Topic")
    large_content = "Lorem ipsum " * 10000  # ~110KB of text
    article = create_article(db_session, topic_id=topic.id, title="Large", content=large_content)
    db_session.commit()

    retrieved = get_article_by_id(db_session, article.id)
    assert len(retrieved.content) == len(large_content)
    assert retrieved.content == large_content
