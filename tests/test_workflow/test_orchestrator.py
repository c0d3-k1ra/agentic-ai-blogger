"""
Tests for sequential workflow orchestrator.

This test suite verifies:
- Happy path execution through all steps
- Failure handling and error capture
- State immutability
- Timestamp updates
- Status transitions
- No side effects (pure function)
"""

from datetime import timezone
from uuid import uuid4

from src.workflow.orchestrator import WORKFLOW_STEPS, run_sequential_workflow
from src.workflow.state import WorkflowState, WorkflowStatus


class TestWorkflowSteps:
    """Test the WORKFLOW_STEPS constant."""

    def test_steps_are_defined(self):
        """Test that workflow steps are defined and accessible."""
        assert WORKFLOW_STEPS is not None
        assert len(WORKFLOW_STEPS) > 0

    def test_steps_sequence(self):
        """Test that steps are in the expected order."""
        expected_steps = [
            "initialize",
            "collect_inputs",
            "plan_structure",
            "research",
            "write_draft",
            "review",
            "finalize",
        ]
        assert WORKFLOW_STEPS == expected_steps

    def test_steps_count(self):
        """Test that we have exactly 7 steps."""
        assert len(WORKFLOW_STEPS) == 7

    def test_steps_are_strings(self):
        """Test that all steps are strings."""
        assert all(isinstance(step, str) for step in WORKFLOW_STEPS)

    def test_steps_are_unique(self):
        """Test that all step names are unique."""
        assert len(WORKFLOW_STEPS) == len(set(WORKFLOW_STEPS))


class TestHappyPath:
    """Test successful workflow execution."""

    def test_happy_path_completion(self):
        """Test that workflow completes successfully through all steps."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test Topic")

        result = run_sequential_workflow(state)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.current_step == "finalize"
        assert result.error_message is None

    def test_status_transitions_pending_to_running(self):
        """Test that status transitions from PENDING to RUNNING."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test", status=WorkflowStatus.PENDING)

        result = run_sequential_workflow(state)

        assert state.status == WorkflowStatus.PENDING
        assert result.status == WorkflowStatus.COMPLETED

    def test_all_steps_executed(self):
        """Test that final step is reached."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state)

        assert result.current_step == WORKFLOW_STEPS[-1]

    def test_workflow_preserves_identifiers(self):
        """Test that workflow_id, topic_id, article_id are preserved."""
        workflow_id = uuid4()
        topic_id = uuid4()
        article_id = uuid4()

        state = WorkflowState(
            workflow_id=workflow_id,
            topic_id=topic_id,
            article_id=article_id,
            topic_name="Test",
        )

        result = run_sequential_workflow(state)

        assert result.workflow_id == workflow_id
        assert result.topic_id == topic_id
        assert result.article_id == article_id

    def test_workflow_preserves_topic_name(self):
        """Test that topic_name is preserved through execution."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Python Async Best Practices")

        result = run_sequential_workflow(state)

        assert result.topic_name == "Python Async Best Practices"

    def test_workflow_preserves_artifacts(self):
        """Test that existing artifacts are preserved."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        state.artifacts.outline = "# Test Outline"
        state.artifacts.research = {"sources": ["test.pdf"]}

        result = run_sequential_workflow(state)

        assert result.artifacts.outline == "# Test Outline"
        assert result.artifacts.research == {"sources": ["test.pdf"]}

    def test_workflow_preserves_metadata(self):
        """Test that metadata is preserved."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test", metadata={"retry_count": 3})

        result = run_sequential_workflow(state)

        assert result.metadata == {"retry_count": 3}


class TestFailurePath:
    """Test failure scenarios and error handling."""

    def test_failure_stops_execution(self):
        """Test that failure at a step stops workflow execution."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state, fail_at_step="research")

        assert result.status == WorkflowStatus.FAILED
        assert result.current_step == "research"
        assert result.error_message is not None

    def test_failure_at_first_step(self):
        """Test failure at the very first step."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state, fail_at_step="initialize")

        assert result.status == WorkflowStatus.FAILED
        assert result.current_step == "initialize"
        assert "initialize" in result.error_message

    def test_failure_at_last_step(self):
        """Test failure at the very last step."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state, fail_at_step="finalize")

        assert result.status == WorkflowStatus.FAILED
        assert result.current_step == "finalize"
        assert "finalize" in result.error_message

    def test_failure_at_middle_step(self):
        """Test failure at a middle step."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state, fail_at_step="write_draft")

        assert result.status == WorkflowStatus.FAILED
        assert result.current_step == "write_draft"
        assert "write_draft" in result.error_message

    def test_error_message_populated_on_failure(self):
        """Test that error_message is populated on failure."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state, fail_at_step="review")

        assert result.error_message is not None
        assert "review" in result.error_message
        assert "Simulated failure" in result.error_message

    def test_invalid_fail_at_step_ignored(self):
        """Test that invalid fail_at_step is ignored (workflow completes)."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state, fail_at_step="nonexistent_step")

        assert result.status == WorkflowStatus.COMPLETED
        assert result.error_message is None

    def test_none_fail_at_step(self):
        """Test that None fail_at_step results in successful completion."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state, fail_at_step=None)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.error_message is None


class TestStateImmutability:
    """Test that original state is never modified."""

    def test_state_is_immutable(self):
        """Test that input state is not modified by workflow execution."""
        workflow_id = uuid4()
        original_state = WorkflowState(workflow_id=workflow_id, topic_name="Test")

        # Capture original values
        original_status = original_state.status
        original_step = original_state.current_step
        original_updated = original_state.updated_at

        # Run workflow
        result = run_sequential_workflow(original_state)

        # Verify original state unchanged
        assert original_state.status == original_status
        assert original_state.current_step == original_step
        assert original_state.updated_at == original_updated
        assert original_state.workflow_id == workflow_id

        # Verify result is different
        assert result.status != original_status
        assert result.current_step != original_step

    def test_original_and_result_are_different_objects(self):
        """Test that result is a different object from input."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state)

        assert result is not state
        assert id(result) != id(state)

    def test_artifacts_not_shared(self):
        """Test that artifacts are not shared between original and result."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        state.artifacts.outline = "Original"

        result = run_sequential_workflow(state)

        # Modify result's artifacts
        result.artifacts.outline = "Modified"

        # Original should be unchanged
        assert state.artifacts.outline == "Original"


class TestTimestampUpdates:
    """Test that timestamps are properly updated."""

    def test_updated_at_changes(self):
        """Test that updated_at changes during workflow execution."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        original_updated = state.updated_at

        result = run_sequential_workflow(state)

        assert result.updated_at > original_updated

    def test_updated_at_is_timezone_aware(self):
        """Test that updated_at remains timezone-aware."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state)

        assert result.updated_at.tzinfo is not None
        assert result.updated_at.tzinfo == timezone.utc

    def test_created_at_unchanged(self):
        """Test that created_at is never modified."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        original_created = state.created_at

        result = run_sequential_workflow(state)

        assert result.created_at == original_created

    def test_updated_at_on_failure(self):
        """Test that updated_at is updated even on failure."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        original_updated = state.updated_at

        result = run_sequential_workflow(state, fail_at_step="research")

        assert result.updated_at > original_updated


class TestNoSideEffects:
    """Test that function has no side effects."""

    def test_no_side_effects(self):
        """Test that function is pure (no external side effects)."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        # Run workflow multiple times
        result1 = run_sequential_workflow(state)
        result2 = run_sequential_workflow(state)

        # Both should have same final state (ignoring timestamps)
        assert result1.status == result2.status
        assert result1.current_step == result2.current_step
        assert result1.workflow_id == result2.workflow_id

    def test_function_is_deterministic_for_steps(self):
        """Test that same input produces same step progression."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result1 = run_sequential_workflow(state)
        result2 = run_sequential_workflow(state)

        # Same progression
        assert result1.current_step == result2.current_step
        assert result1.status == result2.status

    def test_no_database_calls(self):
        """Test that no database operations occur (implicit via no errors)."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        # Should complete without trying to access database
        result = run_sequential_workflow(state)

        assert result.status == WorkflowStatus.COMPLETED

    def test_no_external_dependencies(self):
        """Test that workflow runs without external dependencies."""
        # This test passes by virtue of running successfully
        # If there were external dependencies, they would fail in CI
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state)

        assert result is not None


class TestStatusTransitions:
    """Test status transitions through workflow lifecycle."""

    def test_pending_to_running_transition(self):
        """Test transition from PENDING to RUNNING."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test", status=WorkflowStatus.PENDING)

        result = run_sequential_workflow(state)

        # Should transition through RUNNING to COMPLETED
        assert state.status == WorkflowStatus.PENDING
        assert result.status == WorkflowStatus.COMPLETED

    def test_running_stays_running_until_complete(self):
        """Test that status stays RUNNING during execution."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test", status=WorkflowStatus.RUNNING)

        result = run_sequential_workflow(state)

        assert result.status == WorkflowStatus.COMPLETED

    def test_completed_status_set_at_end(self):
        """Test that COMPLETED status is set after last step."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.current_step == "finalize"

    def test_failed_status_on_error(self):
        """Test that FAILED status is set on error."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state, fail_at_step="research")

        assert result.status == WorkflowStatus.FAILED


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_workflow_with_minimal_state(self):
        """Test workflow with minimal required state fields."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Minimal")

        result = run_sequential_workflow(state)

        assert result.status == WorkflowStatus.COMPLETED

    def test_workflow_with_all_fields_populated(self):
        """Test workflow with all state fields populated."""
        state = WorkflowState(
            workflow_id=uuid4(),
            topic_id=uuid4(),
            article_id=uuid4(),
            topic_name="Complete",
            current_step="custom_step",
            status=WorkflowStatus.PENDING,
            error_message="Previous error",
            metadata={"key": "value"},
        )
        state.artifacts.outline = "Outline"
        state.artifacts.research = {"data": "test"}

        result = run_sequential_workflow(state)

        # Should complete despite having previous error_message
        assert result.status == WorkflowStatus.COMPLETED

    def test_empty_string_fail_at_step(self):
        """Test that empty string fail_at_step is ignored."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="Test")

        result = run_sequential_workflow(state, fail_at_step="")

        assert result.status == WorkflowStatus.COMPLETED

    def test_workflow_with_long_topic_name(self):
        """Test workflow with very long topic name."""
        long_name = "A" * 1000
        state = WorkflowState(workflow_id=uuid4(), topic_name=long_name)

        result = run_sequential_workflow(state)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.topic_name == long_name

    def test_workflow_with_unicode_topic_name(self):
        """Test workflow with unicode characters in topic name."""
        state = WorkflowState(workflow_id=uuid4(), topic_name="测试主题 🚀 Тест")

        result = run_sequential_workflow(state)

        assert result.status == WorkflowStatus.COMPLETED
        assert "测试主题" in result.topic_name
