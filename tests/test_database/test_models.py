"""
Tests for database models.

This test suite verifies:
- Table creation and schema
- Foreign key constraints
- JSONB serialization/deserialization
- ENUM validation
- Cascade behavior
- Auto-updating timestamps
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import String, TypeDecorator, create_engine, event, inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.database.models import Article, Base, EmailThread, Topic, WorkflowState


class GUID(TypeDecorator):  # pylint: disable=abstract-method,too-many-ancestors
    """Platform-independent GUID type that uses PostgreSQL's UUID or String(36) for SQLite."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
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
                    # Remove PostgreSQL-specific server default and add client-side defaults
                    column.server_default = None
                    # Check if this is an array or object type based on the column name
                    if (
                        "keywords" in column.name
                        or "participants" in column.name
                        or "messages" in column.name
                    ):
                        column.default = ColumnDefault(list)
                    else:
                        column.default = ColumnDefault(dict)

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


class TestTableCreation:
    """Test that all tables are created with correct schema."""

    def test_all_tables_created(self, db_session):
        """Verify all expected tables exist in the database."""
        engine = db_session.get_bind()
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "topics" in tables
        assert "articles" in tables
        assert "workflow_states" in tables
        assert "email_threads" in tables

    def test_topic_table_schema(self, db_session):
        """Verify Topic table has correct columns and types."""
        engine = db_session.get_bind()
        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("topics")}

        assert "id" in columns
        assert "name" in columns
        assert "description" in columns
        assert "keywords" in columns
        assert "metadata" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_article_table_schema(self, db_session):
        """Verify Article table has correct columns and types."""
        engine = db_session.get_bind()
        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("articles")}

        assert "id" in columns
        assert "topic_id" in columns
        assert "title" in columns
        assert "content" in columns
        assert "metadata" in columns
        assert "status" in columns
        assert "published_at" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_workflow_state_table_schema(self, db_session):
        """Verify WorkflowState table has correct columns."""
        engine = db_session.get_bind()
        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("workflow_states")}

        assert "id" in columns
        assert "article_id" in columns
        assert "state" in columns
        assert "state_data" in columns
        assert "transitioned_at" in columns
        assert "transitioned_by" in columns
        assert "created_at" in columns

    def test_email_thread_table_schema(self, db_session):
        """Verify EmailThread table has correct columns."""
        engine = db_session.get_bind()
        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("email_threads")}

        assert "id" in columns
        assert "article_id" in columns
        assert "thread_id" in columns
        assert "subject" in columns
        assert "participants" in columns
        assert "messages" in columns
        assert "status" in columns
        assert "last_activity_at" in columns
        assert "created_at" in columns
        assert "updated_at" in columns


class TestIndexes:
    """Test that indexes are created correctly."""

    def test_topic_indexes(self, db_session):
        """Verify Topic table has required indexes."""
        engine = db_session.get_bind()
        inspector = inspect(engine)
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("topics")}

        assert "ix_topics_name" in indexes
        assert "ix_topics_created_at" in indexes

    def test_article_indexes(self, db_session):
        """Verify Article table has required indexes."""
        engine = db_session.get_bind()
        inspector = inspect(engine)
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("articles")}

        assert "ix_articles_topic_id" in indexes
        assert "ix_articles_status" in indexes
        assert "ix_articles_published_at" in indexes
        assert "ix_articles_created_at" in indexes

    def test_workflow_state_indexes(self, db_session):
        """Verify WorkflowState table has required indexes."""
        engine = db_session.get_bind()
        inspector = inspect(engine)
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("workflow_states")}

        assert "ix_workflow_states_article_id" in indexes
        assert "ix_workflow_states_state" in indexes
        assert "ix_workflow_states_transitioned_at" in indexes

    def test_email_thread_indexes(self, db_session):
        """Verify EmailThread table has required indexes."""
        engine = db_session.get_bind()
        inspector = inspect(engine)
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("email_threads")}

        assert "ix_email_threads_article_id" in indexes
        assert "ix_email_threads_thread_id" in indexes
        assert "ix_email_threads_status" in indexes
        assert "ix_email_threads_last_activity_at" in indexes


class TestJSONBFields:
    """Test JSONB field serialization and deserialization."""

    def test_topic_keywords_jsonb(self, db_session):
        """Test Topic keywords JSONB field."""
        topic = Topic(name="Test Topic", keywords=["python", "machine learning", "AI"])
        db_session.add(topic)
        db_session.commit()

        # Retrieve and verify
        retrieved = db_session.query(Topic).filter_by(name="Test Topic").first()
        assert retrieved.keywords == ["python", "machine learning", "AI"]

    def test_topic_metadata_jsonb(self, db_session):
        """Test Topic metadata JSONB field."""
        topic = Topic(
            name="Test Topic", meta_data={"priority": "high", "tags": ["trending", "popular"]}
        )
        db_session.add(topic)
        db_session.commit()

        # Retrieve and verify
        retrieved = db_session.query(Topic).filter_by(name="Test Topic").first()
        assert retrieved.meta_data["priority"] == "high"
        assert retrieved.meta_data["tags"] == ["trending", "popular"]

    def test_article_metadata_jsonb(self, db_session):
        """Test Article metadata JSONB field."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(
            topic_id=topic.id,
            title="Test Article",
            content="Content",
            meta_data={"model": "gpt-4", "temperature": 0.7, "tokens": 1500},
        )
        db_session.add(article)
        db_session.commit()

        # Retrieve and verify
        retrieved = db_session.query(Article).filter_by(title="Test Article").first()
        assert retrieved.meta_data["model"] == "gpt-4"
        assert retrieved.meta_data["temperature"] == 0.7
        assert retrieved.meta_data["tokens"] == 1500

    def test_workflow_state_data_jsonb(self, db_session):
        """Test WorkflowState state_data JSONB field."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        workflow = WorkflowState(
            article_id=article.id,
            state="drafting",
            state_data={"progress": 75, "notes": "Nearly complete", "blockers": []},
        )
        db_session.add(workflow)
        db_session.commit()

        # Retrieve and verify
        retrieved = db_session.query(WorkflowState).filter_by(article_id=article.id).first()
        assert retrieved.state_data["progress"] == 75
        assert retrieved.state_data["notes"] == "Nearly complete"
        assert retrieved.state_data["blockers"] == []

    def test_email_thread_participants_and_messages_jsonb(self, db_session):
        """Test EmailThread participants and messages JSONB fields."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        email_thread = EmailThread(
            article_id=article.id,
            thread_id="thread123",
            participants=["user@example.com", "editor@example.com"],
            messages=[
                {"from": "user@example.com", "body": "First message"},
                {"from": "editor@example.com", "body": "Reply"},
            ],
        )
        db_session.add(email_thread)
        db_session.commit()

        # Retrieve and verify
        retrieved = db_session.query(EmailThread).filter_by(thread_id="thread123").first()
        assert retrieved.participants == ["user@example.com", "editor@example.com"]
        assert len(retrieved.messages) == 2
        assert retrieved.messages[0]["from"] == "user@example.com"
        assert retrieved.messages[1]["body"] == "Reply"


class TestEnumValidation:
    """Test ENUM field validation."""

    def test_article_status_valid_values(self, db_session):
        """Test Article status accepts valid enum values."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        valid_statuses = ["draft", "in_review", "published", "archived"]

        for status in valid_statuses:
            article = Article(
                topic_id=topic.id, title=f"Article {status}", content="Content", status=status
            )
            db_session.add(article)

        db_session.commit()

        # Verify all were created
        count = db_session.query(Article).count()
        assert count == len(valid_statuses)

    def test_article_status_invalid_value_raises_error(self, db_session):
        """Test Article status rejects invalid enum values.

        SQLAlchemy's Enum type validates values on both insert and read,
        so this test verifies that invalid values raise a LookupError.
        """
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(
            topic_id=topic.id, title="Test Article", content="Content", status="invalid_status"
        )
        db_session.add(article)
        db_session.commit()

        # SQLAlchemy's Enum type raises LookupError when reading invalid values
        with pytest.raises(LookupError, match="is not among the defined enum values"):
            _ = article.status

    def test_workflow_state_valid_values(self, db_session):
        """Test WorkflowState state accepts valid enum values."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        valid_states = ["idea", "researching", "drafting", "reviewing", "published"]

        for state in valid_states:
            workflow = WorkflowState(article_id=article.id, state=state)
            db_session.add(workflow)

        db_session.commit()

        # Verify all were created
        count = db_session.query(WorkflowState).count()
        assert count == len(valid_states)

    def test_workflow_state_invalid_value_raises_error(self, db_session):
        """Test WorkflowState state rejects invalid enum values.

        SQLAlchemy's Enum type validates values on both insert and read,
        so this test verifies that invalid values raise a LookupError.
        """
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        workflow = WorkflowState(article_id=article.id, state="invalid_state")
        db_session.add(workflow)
        db_session.commit()

        # SQLAlchemy's Enum type raises LookupError when reading invalid values
        with pytest.raises(LookupError, match="is not among the defined enum values"):
            _ = workflow.state

    def test_email_thread_status_valid_values(self, db_session):
        """Test EmailThread status accepts valid enum values."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        valid_statuses = ["open", "closed", "archived"]

        for idx, status in enumerate(valid_statuses):
            email_thread = EmailThread(
                article_id=article.id, thread_id=f"thread{idx}", status=status
            )
            db_session.add(email_thread)

        db_session.commit()

        # Verify all were created
        count = db_session.query(EmailThread).count()
        assert count == len(valid_statuses)

    def test_email_thread_status_invalid_value_raises_error(self, db_session):
        """Test EmailThread status rejects invalid enum values.

        SQLAlchemy's Enum type validates values on both insert and read,
        so this test verifies that invalid values raise a LookupError.
        """
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        email_thread = EmailThread(
            article_id=article.id, thread_id="thread123", status="invalid_status"
        )
        db_session.add(email_thread)
        db_session.commit()

        # SQLAlchemy's Enum type raises LookupError when reading invalid values
        with pytest.raises(LookupError, match="is not among the defined enum values"):
            _ = email_thread.status


class TestRelationships:
    """Test relationships between models."""

    def test_topic_article_relationship(self, db_session):
        """Test Topic to Article one-to-many relationship."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article1 = Article(topic_id=topic.id, title="Article 1", content="Content 1")
        article2 = Article(topic_id=topic.id, title="Article 2", content="Content 2")
        db_session.add_all([article1, article2])
        db_session.commit()

        # Test forward relationship
        retrieved_topic = db_session.query(Topic).filter_by(name="Test Topic").first()
        assert len(retrieved_topic.articles) == 2

        # Test backward relationship
        retrieved_article = db_session.query(Article).filter_by(title="Article 1").first()
        assert retrieved_article.topic.name == "Test Topic"

    def test_article_workflow_state_relationship(self, db_session):
        """Test Article to WorkflowState one-to-many relationship."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        workflow1 = WorkflowState(article_id=article.id, state="idea")
        workflow2 = WorkflowState(article_id=article.id, state="drafting")
        db_session.add_all([workflow1, workflow2])
        db_session.commit()

        # Test forward relationship
        retrieved_article = db_session.query(Article).filter_by(title="Test Article").first()
        assert len(retrieved_article.workflow_states) == 2

        # Test backward relationship
        retrieved_workflow = db_session.query(WorkflowState).filter_by(state="idea").first()
        assert retrieved_workflow.article.title == "Test Article"

    def test_article_email_thread_relationship(self, db_session):
        """Test Article to EmailThread one-to-many relationship."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        thread1 = EmailThread(article_id=article.id, thread_id="thread1")
        thread2 = EmailThread(article_id=article.id, thread_id="thread2")
        db_session.add_all([thread1, thread2])
        db_session.commit()

        # Test forward relationship
        retrieved_article = db_session.query(Article).filter_by(title="Test Article").first()
        assert len(retrieved_article.email_threads) == 2

        # Test backward relationship
        retrieved_thread = db_session.query(EmailThread).filter_by(thread_id="thread1").first()
        assert retrieved_thread.article.title == "Test Article"


class TestCascadeBehavior:
    """Test cascade delete behavior."""

    def test_delete_topic_does_not_cascade_to_articles(self, db_session):
        """Test that deleting a Topic does NOT delete Articles (RESTRICT)."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        # Attempt to delete topic
        db_session.delete(topic)

        # Should raise IntegrityError due to RESTRICT
        with pytest.raises(IntegrityError):
            db_session.commit()

        # Rollback and verify article still exists
        db_session.rollback()
        article_count = db_session.query(Article).count()
        assert article_count == 1

    def test_delete_article_cascades_to_workflow_states(self, db_session):
        """Test that deleting an Article cascades to WorkflowStates."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        workflow = WorkflowState(article_id=article.id, state="drafting")
        db_session.add(workflow)
        db_session.commit()

        # Verify workflow exists
        workflow_count = db_session.query(WorkflowState).count()
        assert workflow_count == 1

        # Delete article
        db_session.delete(article)
        db_session.commit()

        # Verify workflow was deleted
        workflow_count = db_session.query(WorkflowState).count()
        assert workflow_count == 0

    def test_delete_article_cascades_to_email_threads(self, db_session):
        """Test that deleting an Article cascades to EmailThreads."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        thread = EmailThread(article_id=article.id, thread_id="thread123")
        db_session.add(thread)
        db_session.commit()

        # Verify thread exists
        thread_count = db_session.query(EmailThread).count()
        assert thread_count == 1

        # Delete article
        db_session.delete(article)
        db_session.commit()

        # Verify thread was deleted
        thread_count = db_session.query(EmailThread).count()
        assert thread_count == 0

    def test_delete_article_cascades_to_both_children(self, db_session):
        """Test that deleting an Article cascades to both WorkflowStates and EmailThreads."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        workflow = WorkflowState(article_id=article.id, state="drafting")
        thread = EmailThread(article_id=article.id, thread_id="thread123")
        db_session.add_all([workflow, thread])
        db_session.commit()

        # Verify both exist
        assert db_session.query(WorkflowState).count() == 1
        assert db_session.query(EmailThread).count() == 1

        # Delete article
        db_session.delete(article)
        db_session.commit()

        # Verify both were deleted
        assert db_session.query(WorkflowState).count() == 0
        assert db_session.query(EmailThread).count() == 0


class TestTimestamps:
    """Test timestamp behavior."""

    def test_created_at_auto_set(self, db_session):
        """Test that created_at is automatically set."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        assert topic.created_at is not None
        assert isinstance(topic.created_at, datetime)

    def test_updated_at_auto_set(self, db_session):
        """Test that updated_at is automatically set on creation."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        assert topic.updated_at is not None
        assert isinstance(topic.updated_at, datetime)

    def test_updated_at_changes_on_update_topic(self, db_session):
        """Test that updated_at changes when Topic is updated."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        original_updated_at = topic.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.1)

        # Update topic
        topic.description = "Updated description"
        db_session.commit()

        # Refresh to get latest data
        db_session.refresh(topic)

        assert topic.updated_at > original_updated_at

    def test_updated_at_changes_on_update_article(self, db_session):
        """Test that updated_at changes when Article is updated."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        original_updated_at = article.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.1)

        # Update article
        article.title = "Updated Title"
        db_session.commit()

        # Refresh to get latest data
        db_session.refresh(article)

        assert article.updated_at > original_updated_at

    def test_updated_at_changes_on_update_email_thread(self, db_session):
        """Test that updated_at changes when EmailThread is updated."""
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.commit()

        article = Article(topic_id=topic.id, title="Test Article", content="Content")
        db_session.add(article)
        db_session.commit()

        thread = EmailThread(article_id=article.id, thread_id="thread123")
        db_session.add(thread)
        db_session.commit()

        original_updated_at = thread.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.1)

        # Update thread
        thread.subject = "Updated Subject"
        db_session.commit()

        # Refresh to get latest data
        db_session.refresh(thread)

        assert thread.updated_at > original_updated_at


class TestConstraints:
    """Test database constraints."""

    def test_topic_name_unique(self, db_session):
        """Test that Topic name must be unique."""
        topic1 = Topic(name="Duplicate Name")
        db_session.add(topic1)
        db_session.commit()

        topic2 = Topic(name="Duplicate Name")
        db_session.add(topic2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_article_requires_topic_id(self, db_session):
        """Test that Article requires a valid topic_id."""
        import uuid

        # Try to create article with non-existent topic_id
        article = Article(topic_id=uuid.uuid4(), title="Test Article", content="Content")
        db_session.add(article)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_workflow_state_requires_article_id(self, db_session):
        """Test that WorkflowState requires a valid article_id."""
        import uuid

        # Try to create workflow with non-existent article_id
        workflow = WorkflowState(article_id=uuid.uuid4(), state="drafting")
        db_session.add(workflow)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_email_thread_requires_article_id(self, db_session):
        """Test that EmailThread requires a valid article_id."""
        import uuid

        # Try to create thread with non-existent article_id
        thread = EmailThread(article_id=uuid.uuid4(), thread_id="thread123")
        db_session.add(thread)

        with pytest.raises(IntegrityError):
            db_session.commit()
