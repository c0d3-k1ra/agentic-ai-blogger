"""
Database models for the tech article generator.

This module defines the core SQLAlchemy models using PostgreSQL-specific features:
- UUID primary keys with server-side generation
- JSONB fields for flexible data storage
- PostgreSQL ENUMs for type-safe status fields
- Explicit indexes and relationships
"""

from datetime import datetime
from typing import List

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, event, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""


class Topic(Base):
    """
    Topic model representing article categories/subjects.

    Relationships:
    - One-to-many with Article (RESTRICT on delete - cannot delete topic with articles)
    """
    __tablename__ = "topics"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    keywords: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    meta_data: Mapped[dict] = mapped_column(
        "metadata",  # Column name in database
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    articles: Mapped[List["Article"]] = relationship(
        "Article",
        back_populates="topic",
        cascade="none",  # RESTRICT behavior - no cascade
    )

    # Indexes
    __table_args__ = (
        Index("ix_topics_name", "name"),
        Index("ix_topics_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, name={self.name})>"


class Article(Base):
    """
    Article model representing generated articles.

    Relationships:
    - Many-to-one with Topic (RESTRICT on Topic delete)
    - One-to-many with WorkflowState (CASCADE on Article delete)
    - One-to-many with EmailThread (CASCADE on Article delete)
    """
    __tablename__ = "articles"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    topic_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_data: Mapped[dict] = mapped_column(
        "metadata",  # Column name in database
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "draft",
            "in_review",
            "published",
            "archived",
            name="article_status_enum",
            create_type=True,
        ),
        nullable=False,
        server_default="draft",
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    topic: Mapped["Topic"] = relationship("Topic", back_populates="articles")
    workflow_states: Mapped[List["WorkflowState"]] = relationship(
        "WorkflowState",
        back_populates="article",
        cascade="all, delete-orphan",
    )
    email_threads: Mapped[List["EmailThread"]] = relationship(
        "EmailThread",
        back_populates="article",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_articles_topic_id", "topic_id"),
        Index("ix_articles_status", "status"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (f"<Article(id={self.id}, title={self.title}, "
                f"status={self.status})>")


class WorkflowState(Base):
    """
    WorkflowState model tracking article workflow progression.

    Relationships:
    - Many-to-one with Article (CASCADE on Article delete)
    """
    __tablename__ = "workflow_states"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    article_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(
        Enum(
            "idea",
            "researching",
            "drafting",
            "reviewing",
            "published",
            name="workflow_state_enum",
            create_type=True,
        ),
        nullable=False,
    )
    state_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    transitioned_by: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    article: Mapped["Article"] = relationship(
        "Article",
        back_populates="workflow_states",
    )

    # Indexes
    __table_args__ = (
        Index("ix_workflow_states_article_id", "article_id"),
        Index("ix_workflow_states_state", "state"),
        Index("ix_workflow_states_transitioned_at", "transitioned_at"),
    )

    def __repr__(self) -> str:
        return (f"<WorkflowState(id={self.id}, article_id={self.article_id}, "
                f"state={self.state})>")


class EmailThread(Base):
    """
    EmailThread model tracking email conversations about articles.

    Relationships:
    - Many-to-one with Article (CASCADE on Article delete)
    """
    __tablename__ = "email_threads"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    article_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=True)
    participants: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    messages: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "open",
            "closed",
            "archived",
            name="email_thread_status_enum",
            create_type=True,
        ),
        nullable=False,
        server_default="open",
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    article: Mapped["Article"] = relationship(
        "Article",
        back_populates="email_threads",
    )

    # Indexes
    __table_args__ = (
        Index("ix_email_threads_article_id", "article_id"),
        Index("ix_email_threads_thread_id", "thread_id"),
        Index("ix_email_threads_status", "status"),
        Index("ix_email_threads_last_activity_at", "last_activity_at"),
    )

    def __repr__(self) -> str:
        return (f"<EmailThread(id={self.id}, article_id={self.article_id}, "
                f"status={self.status})>")


# Event listener for auto-updating updated_at on Topic
@event.listens_for(Topic, "before_update")
def receive_before_update_topic(_mapper, _connection, target):
    """Update the updated_at timestamp before updating a Topic."""
    target.updated_at = datetime.utcnow()


# Event listener for auto-updating updated_at on Article
@event.listens_for(Article, "before_update")
def receive_before_update_article(_mapper, _connection, target):
    """Update the updated_at timestamp before updating an Article."""
    target.updated_at = datetime.utcnow()


# Event listener for auto-updating updated_at on EmailThread
@event.listens_for(EmailThread, "before_update")
def receive_before_update_email_thread(_mapper, _connection, target):
    """Update the updated_at timestamp before updating an EmailThread."""
    target.updated_at = datetime.utcnow()
