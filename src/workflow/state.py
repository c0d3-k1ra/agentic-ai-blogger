"""Workflow state definitions.

This module defines the data structures for tracking workflow execution state
without implementing any execution logic, LLM calls, or side effects.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class WorkflowStatus(str, Enum):
    """Workflow execution status.

    Attributes:
        PENDING: Workflow created but not started
        RUNNING: Workflow is actively executing
        PAUSED: Workflow execution paused (can be resumed)
        COMPLETED: Workflow finished successfully
        FAILED: Workflow encountered an error
    """

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowArtifacts(BaseModel):
    """Intermediate artifacts generated during workflow execution.

    Each field represents output from a workflow step. All fields are optional
    as workflows may not reach all steps.

    Attributes:
        outline: Article outline/structure (from planning step)
        research: Research data and sources (from research step)
        draft: Article draft content (from writing step)
        review: Review feedback and suggestions (from review step)
    """

    outline: Optional[str] = None
    research: Optional[Dict[str, Any]] = None
    draft: Optional[str] = None
    review: Optional[Dict[str, Any]] = None


class WorkflowState(BaseModel):
    """Complete state of an article generation workflow.

    This model captures all information needed to track, resume, or debug
    a workflow without containing any execution logic. It is designed to be:
    - Serializable to/from JSON
    - Forward-compatible (can add fields without breaking old states)
    - Self-contained (all debugging info in one place)

    Attributes:
        workflow_id: Unique identifier for this workflow instance
        topic_id: Database ID of the topic (None if not persisted yet)
        article_id: Database ID of the article (None if not created yet)
        topic_name: Human-readable topic name
        current_step: Name of the current/last workflow step
        status: Current execution status
        artifacts: Intermediate outputs from workflow steps
        created_at: When this workflow was created (UTC)
        updated_at: When this workflow was last modified (UTC)
        error_message: Error details if status is FAILED
        metadata: Additional debugging/tracking information
    """

    # Identifiers
    workflow_id: UUID
    topic_id: Optional[UUID] = None
    article_id: Optional[UUID] = None
    topic_name: str

    # Progress tracking
    current_step: str = "initialize"
    status: WorkflowStatus = WorkflowStatus.PENDING

    # Artifacts
    artifacts: WorkflowArtifacts = Field(default_factory=WorkflowArtifacts)

    # Debugging metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_serializer("workflow_id", "topic_id", "article_id", when_used="json")
    def serialize_uuid(self, value: Optional[UUID]) -> Optional[str]:
        """Serialize UUID fields to strings for JSON."""
        return str(value) if value is not None else None

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format strings."""
        return value.isoformat()
