"""
Tests for workflow state definitions.

This test suite verifies:
- Enum values and validation
- Model instantiation and defaults
- JSON serialization/deserialization
- Field validation
- Timestamp handling (timezone-aware)
- UUID handling
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.workflow.state import WorkflowArtifacts, WorkflowState, WorkflowStatus


class TestWorkflowStatus:
    """Test WorkflowStatus enum."""

    def test_all_status_values_exist(self):
        """Test that all expected status values are defined."""
        assert WorkflowStatus.PENDING == "pending"
        assert WorkflowStatus.RUNNING == "running"
        assert WorkflowStatus.PAUSED == "paused"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.FAILED == "failed"

    def test_status_is_string_enum(self):
        """Test that WorkflowStatus is a string enum."""
        status = WorkflowStatus.PENDING
        assert isinstance(status, str)
        assert status == "pending"

    def test_status_values_are_unique(self):
        """Test that all status values are unique."""
        values = [status.value for status in WorkflowStatus]
        assert len(values) == len(set(values))

    def test_status_count(self):
        """Test that we have exactly 5 status values."""
        assert len(WorkflowStatus) == 5


class TestWorkflowArtifacts:
    """Test WorkflowArtifacts model."""

    def test_default_values_are_none(self):
        """Test that all artifact fields default to None."""
        artifacts = WorkflowArtifacts()
        assert artifacts.outline is None
        assert artifacts.research is None
        assert artifacts.draft is None
        assert artifacts.review is None

    def test_set_outline(self):
        """Test setting outline artifact."""
        artifacts = WorkflowArtifacts(outline="# Introduction\n# Main Content")
        assert artifacts.outline == "# Introduction\n# Main Content"

    def test_set_research(self):
        """Test setting research artifact."""
        research_data = {"sources": ["paper1.pdf"], "key_points": ["point1"]}
        artifacts = WorkflowArtifacts(research=research_data)
        assert artifacts.research == research_data
        assert artifacts.research["sources"] == ["paper1.pdf"]

    def test_set_draft(self):
        """Test setting draft artifact."""
        artifacts = WorkflowArtifacts(draft="This is the article draft content.")
        assert artifacts.draft == "This is the article draft content."

    def test_set_review(self):
        """Test setting review artifact."""
        review_data = {"score": 8, "feedback": "Good work", "suggestions": ["Add more examples"]}
        artifacts = WorkflowArtifacts(review=review_data)
        assert artifacts.review == review_data
        assert artifacts.review["score"] == 8

    def test_set_all_artifacts(self):
        """Test setting all artifacts at once."""
        artifacts = WorkflowArtifacts(
            outline="# Outline",
            research={"sources": []},
            draft="Draft content",
            review={"score": 9},
        )
        assert artifacts.outline is not None
        assert artifacts.research is not None
        assert artifacts.draft is not None
        assert artifacts.review is not None

    def test_json_serialization(self):
        """Test that artifacts can be serialized to JSON."""
        artifacts = WorkflowArtifacts(outline="# Test", research={"data": "value"}, draft="Content")
        json_str = artifacts.model_dump_json()
        assert isinstance(json_str, str)
        assert '"outline":"# Test"' in json_str

    def test_json_deserialization(self):
        """Test that artifacts can be restored from JSON."""
        original = WorkflowArtifacts(outline="# Test", research={"key": "value"})
        json_str = original.model_dump_json()
        restored = WorkflowArtifacts.model_validate_json(json_str)
        assert restored.outline == original.outline
        assert restored.research == original.research


class TestWorkflowStateInstantiation:
    """Test WorkflowState model instantiation."""

    def test_minimal_required_fields(self):
        """Test creating state with only required fields."""
        workflow_id = uuid4()
        state = WorkflowState(workflow_id=workflow_id, topic_name="Test Topic")

        assert state.workflow_id == workflow_id
        assert state.topic_name == "Test Topic"
        assert state.topic_id is None
        assert state.article_id is None

    def test_default_current_step(self):
        """Test that current_step defaults to 'initialize'."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        assert state.current_step == "initialize"

    def test_default_status(self):
        """Test that status defaults to PENDING."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        assert state.status == WorkflowStatus.PENDING

    def test_default_artifacts(self):
        """Test that artifacts defaults to empty WorkflowArtifacts."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        assert isinstance(state.artifacts, WorkflowArtifacts)
        assert state.artifacts.outline is None
        assert state.artifacts.research is None

    def test_default_timestamps_auto_generated(self):
        """Test that created_at and updated_at are auto-generated."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.updated_at, datetime)

    def test_timestamps_are_timezone_aware(self):
        """Test that timestamps are timezone-aware (UTC)."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        assert state.created_at.tzinfo is not None
        assert state.created_at.tzinfo == timezone.utc
        assert state.updated_at.tzinfo is not None
        assert state.updated_at.tzinfo == timezone.utc

    def test_default_error_message_is_none(self):
        """Test that error_message defaults to None."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        assert state.error_message is None

    def test_default_metadata_is_empty_dict(self):
        """Test that metadata defaults to empty dict."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        assert state.metadata == {}

    def test_all_fields_set(self):
        """Test creating state with all fields set."""
        workflow_id = uuid4()
        topic_id = uuid4()
        article_id = uuid4()
        created = datetime.now(timezone.utc)
        updated = datetime.now(timezone.utc)

        state = WorkflowState(
            workflow_id=workflow_id,
            topic_id=topic_id,
            article_id=article_id,
            topic_name="Complete Topic",
            current_step="drafting",
            status=WorkflowStatus.RUNNING,
            created_at=created,
            updated_at=updated,
            error_message="Some error",
            metadata={"key": "value"},
        )

        assert state.workflow_id == workflow_id
        assert state.topic_id == topic_id
        assert state.article_id == article_id
        assert state.topic_name == "Complete Topic"
        assert state.current_step == "drafting"
        assert state.status == WorkflowStatus.RUNNING
        assert state.created_at == created
        assert state.updated_at == updated
        assert state.error_message == "Some error"
        assert state.metadata == {"key": "value"}


class TestWorkflowStateValidation:
    """Test WorkflowState field validation."""

    def test_missing_workflow_id_raises_error(self):
        """Test that missing workflow_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowState(topic_name="Test")  # type: ignore

        assert "workflow_id" in str(exc_info.value)

    def test_missing_topic_name_raises_error(self):
        """Test that missing topic_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowState(workflow_id=uuid4())  # type: ignore

        assert "topic_name" in str(exc_info.value)

    def test_invalid_workflow_id_type_raises_error(self):
        """Test that invalid workflow_id type raises ValidationError."""
        with pytest.raises(ValidationError):
            WorkflowState(workflow_id="not-a-uuid", topic_name="Test")  # type: ignore

    def test_invalid_status_type_raises_error(self):
        """Test that invalid status type raises ValidationError."""
        with pytest.raises(ValidationError):
            WorkflowState(
                workflow_id=uuid4(),
                topic_name="Test",
                status="invalid_status",  # type: ignore
            )

    def test_optional_fields_accept_none(self):
        """Test that optional fields accept None explicitly."""
        state = WorkflowState(
            workflow_id=uuid4(),
            topic_name="Test",
            topic_id=None,
            article_id=None,
            error_message=None,
        )
        assert state.topic_id is None
        assert state.article_id is None
        assert state.error_message is None


class TestWorkflowStateJSONSerialization:
    """Test JSON serialization and deserialization."""

    def test_basic_state_json_round_trip(self):
        """Test basic state can round-trip through JSON."""
        original = WorkflowState(workflow_id=uuid4(), topic_name="Test Topic")

        json_str = original.model_dump_json()
        restored = WorkflowState.model_validate_json(json_str)

        assert restored.workflow_id == original.workflow_id
        assert restored.topic_name == original.topic_name
        assert restored.status == original.status
        assert restored.current_step == original.current_step

    def test_complex_state_json_round_trip(self):
        """Test complex state with all fields can round-trip through JSON."""
        workflow_id = uuid4()
        topic_id = uuid4()
        article_id = uuid4()

        original = WorkflowState(
            workflow_id=workflow_id,
            topic_id=topic_id,
            article_id=article_id,
            topic_name="Complex Topic",
            current_step="reviewing",
            status=WorkflowStatus.RUNNING,
            error_message="Test error",
            metadata={"retries": 3, "agent": "agent-1"},
        )
        original.artifacts.outline = "# Test Outline"
        original.artifacts.research = {"sources": ["source1", "source2"]}
        original.artifacts.draft = "Draft content here"
        original.artifacts.review = {"score": 8, "feedback": "Good"}

        json_str = original.model_dump_json()
        restored = WorkflowState.model_validate_json(json_str)

        assert restored.workflow_id == original.workflow_id
        assert restored.topic_id == original.topic_id
        assert restored.article_id == original.article_id
        assert restored.topic_name == original.topic_name
        assert restored.current_step == original.current_step
        assert restored.status == original.status
        assert restored.error_message == original.error_message
        assert restored.metadata == original.metadata
        assert restored.artifacts.outline == original.artifacts.outline
        assert restored.artifacts.research == original.artifacts.research
        assert restored.artifacts.draft == original.artifacts.draft
        assert restored.artifacts.review == original.artifacts.review

    def test_uuid_serialization(self):
        """Test that UUIDs are serialized as strings."""
        workflow_id = uuid4()
        state = WorkflowState(workflow_id=workflow_id, topic_name="Test")

        json_str = state.model_dump_json()
        assert str(workflow_id) in json_str

    def test_datetime_serialization(self):
        """Test that datetimes are serialized to ISO format."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        json_str = state.model_dump_json()
        # Should contain ISO formatted datetime
        assert "T" in json_str  # ISO format includes 'T'
        assert "Z" in json_str or "+" in json_str  # Timezone indicator

    def test_enum_serialization(self):
        """Test that enum values are serialized as strings."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test", status=WorkflowStatus.RUNNING)

        json_str = state.model_dump_json()
        assert '"status":"running"' in json_str

    def test_nested_dict_in_metadata(self):
        """Test that nested dicts in metadata are preserved."""
        state = WorkflowState(
            workflow_id=uuid4(),
            topic_name="Test",
            metadata={"level1": {"level2": {"level3": "value"}}},
        )

        json_str = state.model_dump_json()
        restored = WorkflowState.model_validate_json(json_str)

        assert restored.metadata["level1"]["level2"]["level3"] == "value"

    def test_list_in_metadata(self):
        """Test that lists in metadata are preserved."""
        state = WorkflowState(
            workflow_id=uuid4(), topic_name="Test", metadata={"items": [1, 2, 3, "four"]}
        )

        json_str = state.model_dump_json()
        restored = WorkflowState.model_validate_json(json_str)

        assert restored.metadata["items"] == [1, 2, 3, "four"]


class TestWorkflowStateArtifactsIntegration:
    """Test artifacts integration with WorkflowState."""

    def test_modify_artifacts_after_creation(self):
        """Test that artifacts can be modified after state creation."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        # Initially empty
        assert state.artifacts.outline is None

        # Modify
        state.artifacts.outline = "# New Outline"
        assert state.artifacts.outline == "# New Outline"

    def test_artifacts_preserved_in_json_round_trip(self):
        """Test that modified artifacts are preserved in JSON round-trip."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        state.artifacts.outline = "# Outline"
        state.artifacts.research = {"data": [1, 2, 3]}

        json_str = state.model_dump_json()
        restored = WorkflowState.model_validate_json(json_str)

        assert restored.artifacts.outline == "# Outline"
        assert restored.artifacts.research == {"data": [1, 2, 3]}

    def test_empty_artifacts_serialization(self):
        """Test that empty artifacts are serialized correctly."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        json_str = state.model_dump_json()
        restored = WorkflowState.model_validate_json(json_str)

        assert restored.artifacts.outline is None
        assert restored.artifacts.research is None
        assert restored.artifacts.draft is None
        assert restored.artifacts.review is None


class TestWorkflowStateStatusTransitions:
    """Test status transitions and tracking."""

    def test_status_can_be_updated(self):
        """Test that status can be updated."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        assert state.status == WorkflowStatus.PENDING

        # Update status (would normally be done by orchestration)
        state = WorkflowState(
            workflow_id=state.workflow_id,
            topic_name=state.topic_name,
            status=WorkflowStatus.RUNNING,
        )
        assert state.status == WorkflowStatus.RUNNING

    def test_all_status_values_accepted(self):
        """Test that all status enum values are accepted."""
        for status in WorkflowStatus:
            state = WorkflowState(workflow_id=uuid4(), topic_name="Test", status=status)
            assert state.status == status


class TestWorkflowStateMetadata:
    """Test metadata field extensibility."""

    def test_metadata_extensibility(self):
        """Test that metadata can store arbitrary key-value pairs."""
        state = WorkflowState(
            workflow_id=uuid4(),
            topic_name="Test",
            metadata={
                "retry_count": 3,
                "last_error": "Connection timeout",
                "agent_id": "agent-123",
                "custom_field": {"nested": "value"},
            },
        )

        assert state.metadata["retry_count"] == 3
        assert state.metadata["last_error"] == "Connection timeout"
        assert state.metadata["agent_id"] == "agent-123"
        assert state.metadata["custom_field"]["nested"] == "value"

    def test_empty_metadata(self):
        """Test that empty metadata dict is valid."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test", metadata={})
        assert state.metadata == {}


class TestWorkflowStateErrorTracking:
    """Test error message tracking."""

    def test_error_message_tracking(self):
        """Test that error messages can be tracked."""
        state = WorkflowState(
            workflow_id=uuid4(),
            topic_name="Test",
            status=WorkflowStatus.FAILED,
            error_message="LLM API timeout after 30s",
        )

        assert state.error_message == "LLM API timeout after 30s"
        assert state.status == WorkflowStatus.FAILED

    def test_error_message_preserved_in_json(self):
        """Test that error message is preserved in JSON round-trip."""
        state = WorkflowState(
            workflow_id=uuid4(),
            topic_name="Test",
            error_message="Test error with special chars: 你好 🚀",
        )

        json_str = state.model_dump_json()
        restored = WorkflowState.model_validate_json(json_str)

        assert restored.error_message == state.error_message


class TestWorkflowStateIDs:
    """Test UUID field handling."""

    def test_workflow_id_is_uuid(self):
        """Test that workflow_id is a UUID type."""
        workflow_id = uuid4()
        state = WorkflowState(workflow_id=workflow_id, topic_name="Test")
        assert isinstance(state.workflow_id, UUID)
        assert state.workflow_id == workflow_id

    def test_optional_uuids_can_be_set(self):
        """Test that optional UUID fields can be set."""
        topic_id = uuid4()
        article_id = uuid4()

        state = WorkflowState(
            workflow_id=uuid4(), topic_name="Test", topic_id=topic_id, article_id=article_id
        )

        assert isinstance(state.topic_id, UUID)
        assert isinstance(state.article_id, UUID)
        assert state.topic_id == topic_id
        assert state.article_id == article_id

    def test_uuid_preserved_in_json_round_trip(self):
        """Test that UUIDs are preserved in JSON round-trip."""
        workflow_id = uuid4()
        topic_id = uuid4()
        article_id = uuid4()

        original = WorkflowState(
            workflow_id=workflow_id, topic_name="Test", topic_id=topic_id, article_id=article_id
        )

        json_str = original.model_dump_json()
        restored = WorkflowState.model_validate_json(json_str)

        assert restored.workflow_id == workflow_id
        assert restored.topic_id == topic_id
        assert restored.article_id == article_id
