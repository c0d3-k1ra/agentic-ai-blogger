"""Tests for CRUD helper functions."""

import uuid

import pytest
from sqlalchemy import String, TypeDecorator, create_engine, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.database.db import (
    create_article,
    create_topic,
    get_article_by_id,
    get_topic_by_id,
    get_topic_by_name,
    update_article,
    update_topic,
)
from src.database.models import Base


class GUID(TypeDecorator):  # pylint: disable=abstract-method,too-many-ancestors
    """Platform-independent GUID type that uses PostgreSQL's UUID or String(36) for SQLite."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session with UUID and JSONB support for SQLite."""
    from sqlalchemy import (
        JSON,  # pylint: disable=import-outside-toplevel
        ColumnDefault,  # pylint: disable=import-outside-toplevel
    )
    from sqlalchemy.dialects.postgresql import JSONB  # pylint: disable=import-outside-toplevel

    # Replace UUID and JSONB types for SQLite compatibility
    @event.listens_for(Base.metadata, "before_create")
    def replace_types_for_sqlite(target, connection, **kw):  # pylint: disable=unused-argument
        for table in target.tables.values():
            for column in table.columns:
                if isinstance(column.type, UUID):
                    column.type = GUID()
                    # Remove PostgreSQL-specific server default and add client-side default
                    column.server_default = None
                    column.default = ColumnDefault(uuid.uuid4)
                elif isinstance(column.type, JSONB):
                    column.type = JSON()
                    # Remove PostgreSQL-specific server default
                    column.server_default = None

    engine = create_engine("sqlite:///:memory:")

    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def enable_sqlite_fks(dbapi_conn, connection_record):  # pylint: disable=unused-argument
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create tables (event listener will modify types)
    Base.metadata.create_all(engine)

    session_local = sessionmaker(bind=engine)
    session = session_local()

    yield session

    session.close()

    # Clean up: restore original types for next test
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, GUID):
                from sqlalchemy.dialects.postgresql import (
                    UUID as PG_UUID,  # pylint: disable=import-outside-toplevel,reimported
                )
                column.type = PG_UUID(as_uuid=True)
                column.default = None
            elif isinstance(column.type, JSON):
                column.type = JSONB()

    # Remove event listener
    event.remove(Base.metadata, "before_create", replace_types_for_sqlite)

    engine.dispose()


# ============================================================================
# Topic CRUD Tests
# ============================================================================


def test_create_topic_with_all_fields(db_session: Session):
    """Test creating a topic with all fields."""
    topic = create_topic(
        db_session,
        name="Python",
        description="Python programming language",
        keywords=["python", "programming", "coding"],
        metadata={"difficulty": "beginner"}
    )

    db_session.commit()

    assert topic.id is not None
    assert topic.name == "Python"
    assert topic.description == "Python programming language"
    assert topic.keywords == ["python", "programming", "coding"]
    assert topic.meta_data == {"difficulty": "beginner"}
    assert topic.created_at is not None
    assert topic.updated_at is not None


def test_create_topic_with_minimal_fields(db_session: Session):
    """Test creating a topic with only required field."""
    topic = create_topic(db_session, name="JavaScript")

    db_session.commit()

    assert topic.id is not None
    assert topic.name == "JavaScript"
    assert topic.description is None
    assert topic.keywords == []
    assert topic.meta_data == {}


def test_get_topic_by_id(db_session: Session):
    """Test retrieving topic by ID."""
    topic = create_topic(db_session, name="TypeScript")
    db_session.commit()

    retrieved = get_topic_by_id(db_session, topic.id)

    assert retrieved is not None
    assert retrieved.id == topic.id
    assert retrieved.name == "TypeScript"


def test_get_topic_by_id_not_found(db_session: Session):
    """Test retrieving non-existent topic returns None."""
    from uuid import uuid4  # pylint: disable=import-outside-toplevel

    result = get_topic_by_id(db_session, uuid4())

    assert result is None


def test_get_topic_by_name(db_session: Session):
    """Test retrieving topic by name."""
    topic = create_topic(db_session, name="Rust")
    db_session.commit()

    retrieved = get_topic_by_name(db_session, "Rust")

    assert retrieved is not None
    assert retrieved.id == topic.id
    assert retrieved.name == "Rust"


def test_get_topic_by_name_not_found(db_session: Session):
    """Test retrieving non-existent topic by name returns None."""
    result = get_topic_by_name(db_session, "NonExistent")

    assert result is None


def test_update_topic_single_field(db_session: Session):
    """Test updating a single topic field."""
    topic = create_topic(db_session, name="Go", description="Old description")
    db_session.commit()

    updated = update_topic(db_session, topic.id, description="New description")
    db_session.commit()

    assert updated.id == topic.id
    assert updated.description == "New description"
    assert updated.name == "Go"  # Unchanged


def test_update_topic_multiple_fields(db_session: Session):
    """Test updating multiple topic fields."""
    topic = create_topic(db_session, name="Swift")
    db_session.commit()

    updated = update_topic(
        db_session,
        topic.id,
        description="iOS development language",
        keywords=["swift", "ios", "apple"],
        metadata={"platform": "iOS"}
    )
    db_session.commit()

    assert updated.description == "iOS development language"
    assert updated.keywords == ["swift", "ios", "apple"]
    assert updated.meta_data == {"platform": "iOS"}


def test_update_topic_not_found(db_session: Session):
    """Test updating non-existent topic raises ValueError."""
    from uuid import uuid4  # pylint: disable=import-outside-toplevel

    with pytest.raises(ValueError, match="Topic with id .* not found"):
        update_topic(db_session, uuid4(), name="NewName")


def test_update_topic_unknown_field(db_session: Session):
    """Test updating unknown field raises ValueError."""
    topic = create_topic(db_session, name="Kotlin")
    db_session.commit()

    with pytest.raises(ValueError, match="Unknown fields"):
        update_topic(db_session, topic.id, unknown_field="value")


def test_create_topic_duplicate_name(db_session: Session):
    """Test creating topic with duplicate name raises IntegrityError."""
    create_topic(db_session, name="Java")
    db_session.commit()

    with pytest.raises(IntegrityError):
        create_topic(db_session, name="Java")
        db_session.commit()


# ============================================================================
# Article CRUD Tests
# ============================================================================


def test_create_article_with_all_fields(db_session: Session):
    """Test creating an article with all fields."""
    topic = create_topic(db_session, name="Django")
    db_session.commit()

    article = create_article(
        db_session,
        topic_id=topic.id,
        title="Introduction to Django",
        content="Django is a web framework...",
        metadata={"author": "John Doe"}
    )
    db_session.commit()

    assert article.id is not None
    assert article.topic_id == topic.id
    assert article.title == "Introduction to Django"
    assert article.content == "Django is a web framework..."
    assert article.meta_data == {"author": "John Doe"}
    assert article.status == "draft"
    assert article.published_at is None
    assert article.created_at is not None


def test_create_article_with_content_none(db_session: Session):
    """Test creating article with content=None."""
    topic = create_topic(db_session, name="Flask")
    db_session.commit()

    article = create_article(
        db_session,
        topic_id=topic.id,
        title="Flask Tutorial",
        content=None
    )
    db_session.commit()

    assert article.content == ""
    assert article.status == "draft"


def test_create_article_minimal_fields(db_session: Session):
    """Test creating article with minimal fields."""
    topic = create_topic(db_session, name="FastAPI")
    db_session.commit()

    article = create_article(
        db_session,
        topic_id=topic.id,
        title="FastAPI Basics"
    )
    db_session.commit()

    assert article.title == "FastAPI Basics"
    assert article.content == ""
    assert article.meta_data == {}


def test_create_article_invalid_topic(db_session: Session):
    """Test creating article with non-existent topic raises IntegrityError."""
    from uuid import uuid4  # pylint: disable=import-outside-toplevel

    with pytest.raises(IntegrityError):
        create_article(
            db_session,
            topic_id=uuid4(),
            title="Invalid Article"
        )
        db_session.commit()


def test_get_article_by_id(db_session: Session):
    """Test retrieving article by ID."""
    topic = create_topic(db_session, name="React")
    article = create_article(db_session, topic_id=topic.id, title="React Hooks")
    db_session.commit()

    retrieved = get_article_by_id(db_session, article.id)

    assert retrieved is not None
    assert retrieved.id == article.id
    assert retrieved.title == "React Hooks"


def test_get_article_by_id_not_found(db_session: Session):
    """Test retrieving non-existent article returns None."""
    from uuid import uuid4  # pylint: disable=import-outside-toplevel

    result = get_article_by_id(db_session, uuid4())

    assert result is None


def test_update_article_single_field(db_session: Session):
    """Test updating a single article field."""
    topic = create_topic(db_session, name="Vue")
    article = create_article(db_session, topic_id=topic.id, title="Old Title")
    db_session.commit()

    updated = update_article(db_session, article.id, title="New Title")
    db_session.commit()

    assert updated.title == "New Title"
    assert updated.content == ""  # Unchanged


def test_update_article_multiple_fields(db_session: Session):
    """Test updating multiple article fields."""
    topic = create_topic(db_session, name="Angular")
    article = create_article(db_session, topic_id=topic.id, title="Angular Guide")
    db_session.commit()

    updated = update_article(
        db_session,
        article.id,
        content="Full content here",
        metadata={"tags": ["frontend", "spa"]},
        status="in_review"
    )
    db_session.commit()

    assert updated.content == "Full content here"
    assert updated.meta_data == {"tags": ["frontend", "spa"]}
    assert updated.status == "in_review"
    assert updated.title == "Angular Guide"  # Unchanged


def test_update_article_only_specified_fields(db_session: Session):
    """Test that update only changes specified fields."""
    topic = create_topic(db_session, name="Svelte")
    article = create_article(
        db_session,
        topic_id=topic.id,
        title="Original Title",
        content="Original Content",
        metadata={"version": "1.0"}
    )
    db_session.commit()

    original_content = article.content
    original_metadata = article.meta_data

    updated = update_article(db_session, article.id, title="Updated Title")
    db_session.commit()

    assert updated.title == "Updated Title"
    assert updated.content == original_content
    assert updated.meta_data == original_metadata


def test_update_article_not_found(db_session: Session):
    """Test updating non-existent article raises ValueError."""
    from uuid import uuid4  # pylint: disable=import-outside-toplevel

    with pytest.raises(ValueError, match="Article with id .* not found"):
        update_article(db_session, uuid4(), title="NewTitle")


def test_update_article_unknown_field(db_session: Session):
    """Test updating unknown field raises ValueError."""
    topic = create_topic(db_session, name="Ember")
    article = create_article(db_session, topic_id=topic.id, title="Ember App")
    db_session.commit()

    with pytest.raises(ValueError, match="Unknown fields"):
        update_article(db_session, article.id, unknown_field="value")


def test_article_defaults_to_draft(db_session: Session):
    """Test that article status defaults to draft."""
    topic = create_topic(db_session, name="Node.js")
    article = create_article(db_session, topic_id=topic.id, title="Node Basics")
    db_session.commit()

    assert article.status == "draft"
    assert article.published_at is None


# ============================================================================
# Session Safety Tests
# ============================================================================


def test_session_remains_usable_after_crud(db_session: Session):
    """Test that session remains usable after CRUD operations."""
    topic1 = create_topic(db_session, name="Topic1")
    db_session.commit()

    # Session should still be usable
    topic2 = create_topic(db_session, name="Topic2")
    db_session.commit()

    assert get_topic_by_id(db_session, topic1.id) is not None
    assert get_topic_by_id(db_session, topic2.id) is not None


def test_multiple_crud_calls_in_same_session(db_session: Session):
    """Test multiple CRUD operations in the same session."""
    # Create topic
    topic = create_topic(db_session, name="Multi-Op")

    # Create article without committing
    article = create_article(db_session, topic_id=topic.id, title="Article 1")

    # Update topic without committing
    update_topic(db_session, topic.id, description="Updated description")

    # Commit all changes
    db_session.commit()

    # Verify all changes persisted
    retrieved_topic = get_topic_by_id(db_session, topic.id)
    retrieved_article = get_article_by_id(db_session, article.id)

    assert retrieved_topic.description == "Updated description"
    assert retrieved_article.title == "Article 1"


def test_no_implicit_commit(db_session: Session):  # pylint: disable=redefined-outer-name
    """Test that CRUD helpers do not implicitly commit."""
    create_topic(db_session, name="NoCommit")

    # Rollback without explicit commit
    db_session.rollback()

    # Topic should not exist
    result = get_topic_by_name(db_session, "NoCommit")
    assert result is None
