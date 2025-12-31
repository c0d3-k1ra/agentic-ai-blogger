"""Unit tests for RevisionNode.

Tests the integration of RevisionAgent into the LangGraph workflow,
verifying proper revision execution, error handling, and state updates.

Test Coverage:
- Node registration and properties
- Successful article revision based on feedback
- State updates and transitions
- Error handling for missing/invalid inputs
- Revision number tracking
- Draft content updates
- Logging integration
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.revision import RevisedArticle
from src.workflow.nodes import NodeRegistry
from src.workflow.nodes.revision import RevisionNode


class TestRevisionNode:
    """Test suite for RevisionNode workflow integration."""

    def setup_method(self) -> None:
        """Ensure node is registered before each test."""
        if not NodeRegistry.is_registered("revision"):
            from src.workflow.nodes.revision import RevisionNode

            NodeRegistry.register("revision")(RevisionNode)

    def test_node_registered_in_registry(self) -> None:
        """Verify node is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("revision")
        node_class = NodeRegistry.get("revision")
        assert node_class == RevisionNode
        node = node_class()
        assert isinstance(node, RevisionNode)

    def test_node_has_correct_name(self) -> None:
        """Verify node name property returns correct identifier."""
        node = RevisionNode()
        assert node.name == "revision"

    @pytest.mark.asyncio
    async def test_successful_revision(self) -> None:
        """Verify node successfully revises article based on feedback."""
        node = RevisionNode()

        draft_content = "# Original Article\nOriginal content here."
        feedback = "Make the introduction more engaging"
        topic = "Python Programming"

        state = {
            "draft_content": draft_content,
            "user_feedback": feedback,
            "selected_topic": topic,
            "revision_number": 0,
            "workflow_id": "test-wf-001",
        }

        # Mock revise_article
        mock_revised = RevisedArticle(
            content="# Original Article\nRevised, more engaging content here.",
            changes_summary="Made introduction more engaging and added examples",
            word_count=180,
            revision_number=1,
        )

        with patch(
            "src.workflow.nodes.revision.revise_article", new=AsyncMock(return_value=mock_revised)
        ):
            result = await node.execute(state)

        # Verify state updates
        assert "revised_article" in result
        assert "draft_content" in result
        assert "revision_number" in result
        assert "current_step" in result

        # Verify transitions back to review
        assert result["current_step"] == "review"

        # Verify revision tracking
        assert result["revision_number"] == 1

        # Verify draft content updated
        assert result["draft_content"] == mock_revised.content

    @pytest.mark.asyncio
    async def test_revise_article_called_with_correct_params(self) -> None:
        """Verify revise_article is called with correct parameters."""
        node = RevisionNode()

        draft_content = "# Article\nContent."
        feedback = "Add more examples"
        topic = "Machine Learning"
        current_revision = 2

        state = {
            "draft_content": draft_content,
            "user_feedback": feedback,
            "selected_topic": topic,
            "revision_number": current_revision,
            "workflow_id": "test-wf-002",
        }

        mock_revised = RevisedArticle(
            content="Revised content",
            changes_summary="Added examples",
            word_count=100,
            revision_number=3,
        )

        mock_revise = AsyncMock(return_value=mock_revised)

        with patch("src.workflow.nodes.revision.revise_article", new=mock_revise):
            await node.execute(state)

        # Verify revise_article was called correctly
        mock_revise.assert_called_once()
        call_args = mock_revise.call_args
        assert call_args[0][0] == draft_content  # First arg is content
        assert call_args[0][1] == feedback  # Second arg is feedback
        assert call_args[1]["topic"] == topic
        assert call_args[1]["revision_number"] == 3  # Incremented

    @pytest.mark.asyncio
    async def test_revision_number_increments(self) -> None:
        """Verify revision_number is properly incremented."""
        node = RevisionNode()

        state = {
            "draft_content": "# Article\nContent.",
            "user_feedback": "Improve clarity",
            "selected_topic": "Docker",
            "revision_number": 5,
            "workflow_id": "test-wf-003",
        }

        mock_revised = RevisedArticle(
            content="Improved content",
            changes_summary="Improved clarity",
            word_count=120,
            revision_number=6,
        )

        with patch(
            "src.workflow.nodes.revision.revise_article", new=AsyncMock(return_value=mock_revised)
        ):
            result = await node.execute(state)

        # Verify revision number was incremented
        assert result["revision_number"] == 6

    @pytest.mark.asyncio
    async def test_default_revision_number_zero(self) -> None:
        """Verify revision_number defaults to 0 if not in state."""
        node = RevisionNode()

        state = {
            "draft_content": "# Article\nContent.",
            "user_feedback": "Add examples",
            "selected_topic": "Kubernetes",
            # No revision_number in state
            "workflow_id": "test-wf-004",
        }

        mock_revised = RevisedArticle(
            content="Revised content",
            changes_summary="Added examples",
            word_count=150,
            revision_number=1,
        )

        with patch(
            "src.workflow.nodes.revision.revise_article", new=AsyncMock(return_value=mock_revised)
        ):
            result = await node.execute(state)

        # Should start from 0 and increment to 1
        assert result["revision_number"] == 1

    @pytest.mark.asyncio
    async def test_missing_draft_content_raises_error(self) -> None:
        """Verify missing draft_content results in error state."""
        node = RevisionNode()
        state = {
            "user_feedback": "Improve it",
            "selected_topic": "Python",
            "workflow_id": "test-wf-005",
        }

        result = await node.execute(state)

        # @handle_node_errors should catch ValueError and set error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_empty_draft_content_raises_error(self) -> None:
        """Verify empty draft_content results in error state."""
        node = RevisionNode()
        state = {
            "draft_content": "",
            "user_feedback": "Improve it",
            "selected_topic": "Python",
            "workflow_id": "test-wf-006",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_missing_feedback_raises_error(self) -> None:
        """Verify missing user_feedback results in error state."""
        node = RevisionNode()
        state = {
            "draft_content": "# Article\nContent.",
            "selected_topic": "Python",
            "workflow_id": "test-wf-007",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_empty_feedback_raises_error(self) -> None:
        """Verify empty user_feedback results in error state."""
        node = RevisionNode()
        state = {
            "draft_content": "# Article\nContent.",
            "user_feedback": "",
            "selected_topic": "Python",
            "workflow_id": "test-wf-008",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_missing_topic_raises_error(self) -> None:
        """Verify missing selected_topic results in error state."""
        node = RevisionNode()
        state = {
            "draft_content": "# Article\nContent.",
            "user_feedback": "Improve it",
            "workflow_id": "test-wf-009",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_logging_decorator_applied(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify @log_node_execution decorator logs execution."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = RevisionNode()
        state = {
            "draft_content": "# Test\nContent.",
            "user_feedback": "Improve clarity",
            "selected_topic": "Python",
            "workflow_id": "test-wf-010",
        }

        mock_revised = RevisedArticle(
            content="Revised content",
            changes_summary="Improved clarity",
            word_count=80,
            revision_number=1,
        )

        with patch(
            "src.workflow.nodes.revision.revise_article", new=AsyncMock(return_value=mock_revised)
        ):
            await node.execute(state)

        # Check for start and end logs
        log_messages = [record.message for record in caplog.records]
        start_logs = [m for m in log_messages if "Starting execution" in m and "revision" in m]
        end_logs = [m for m in log_messages if "Completed execution" in m and "revision" in m]

        assert len(start_logs) > 0, "Should log execution start"
        assert len(end_logs) > 0, "Should log execution end"

    @pytest.mark.asyncio
    async def test_workflow_id_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify workflow_id is included in log messages."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = RevisionNode()
        workflow_id = "test-wf-011"
        state = {
            "draft_content": "# Test\nContent.",
            "user_feedback": "Add examples",
            "selected_topic": "React",
            "workflow_id": workflow_id,
        }

        mock_revised = RevisedArticle(
            content="Revised content",
            changes_summary="Added examples",
            word_count=90,
            revision_number=1,
        )

        with patch(
            "src.workflow.nodes.revision.revise_article", new=AsyncMock(return_value=mock_revised)
        ):
            await node.execute(state)

        # Check that workflow_id appears in logs
        log_messages = [record.message for record in caplog.records]
        workflow_logs = [m for m in log_messages if workflow_id in m]

        assert len(workflow_logs) > 0, f"Should include workflow_id {workflow_id} in logs"

    @pytest.mark.asyncio
    async def test_revised_article_structure(self) -> None:
        """Verify revised_article has all required fields."""
        node = RevisionNode()
        state = {
            "draft_content": "# Original\nOriginal content.",
            "user_feedback": "Make it better",
            "selected_topic": "Rust",
            "revision_number": 0,
            "workflow_id": "test-wf-012",
        }

        mock_revised = RevisedArticle(
            content="# Original\nImproved content with examples and clarity.",
            changes_summary="Enhanced readability, added code examples, improved structure",
            word_count=275,
            revision_number=1,
        )

        with patch(
            "src.workflow.nodes.revision.revise_article", new=AsyncMock(return_value=mock_revised)
        ):
            result = await node.execute(state)

        revised = result["revised_article"]

        # Verify all fields are present
        assert revised.content
        assert revised.changes_summary
        assert revised.word_count > 0
        assert revised.revision_number == 1
