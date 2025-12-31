"""Tests for user interaction nodes."""

from unittest.mock import patch

import pytest

from src.workflow.nodes import NodeRegistry
from src.workflow.nodes.user_interaction import UserApprovalNode, UserSelectionNode


class TestUserSelectionNode:
    """Tests for UserSelectionNode."""

    def test_node_registered_in_registry(self):
        """Test that UserSelectionNode is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("user_selection")

    def test_node_has_correct_name(self):
        """Test that node has correct name property."""
        node = UserSelectionNode()
        assert node.name == "user_selection"

    @pytest.mark.asyncio
    async def test_successful_topic_selection(self):
        """Test successful topic selection flow."""
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "Python Async", "score": 8.5},
                {"topic": "Type Hints", "score": 7.2},
                {"topic": "FastAPI", "score": 6.8},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()

        # Mock only the external dependencies
        with patch("src.workflow.nodes.user_interaction.display_topics_for_selection"):
            with patch("src.workflow.nodes.user_interaction.interrupt", return_value=2):
                result = await node.execute(state)

        # Verify
        assert result["selected_topic"] == "Type Hints"
        assert result["current_step"] == "plan_structure"

    @pytest.mark.asyncio
    async def test_selection_via_cli_prompt(self):
        """Test topic selection via CLI when interrupt returns None."""
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "Python Async", "score": 8.5},
                {"topic": "Type Hints", "score": 7.2},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()

        with patch("src.workflow.nodes.user_interaction.display_topics_for_selection"):
            with patch("src.workflow.nodes.user_interaction.interrupt", return_value=None):
                with patch(
                    "src.workflow.nodes.user_interaction.prompt_user_topic_selection",
                    return_value=1,
                ):
                    result = await node.execute(state)

        assert result["selected_topic"] == "Python Async"
        assert result["current_step"] == "plan_structure"

    @pytest.mark.asyncio
    async def test_missing_scored_topics_raises_error(self):
        """Test that missing scored_topics raises error."""
        state = {
            "workflow_id": "test-123",
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"
        assert any("scored_topics" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def test_empty_scored_topics_raises_error(self):
        """Test that empty scored_topics list raises error."""
        state = {
            "workflow_id": "test-123",
            "scored_topics": [],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_invalid_selection_index_raises_error(self):
        """Test that invalid selection index raises error."""
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "Python Async", "score": 8.5},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()

        with patch("src.workflow.nodes.user_interaction.display_topics_for_selection"):
            with patch("src.workflow.nodes.user_interaction.interrupt", return_value=99):
                result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_zero_selection_index_raises_error(self):
        """Test that zero selection index raises error."""
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "Python Async", "score": 8.5},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()

        with patch("src.workflow.nodes.user_interaction.display_topics_for_selection"):
            with patch("src.workflow.nodes.user_interaction.interrupt", return_value=0):
                result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_topic_missing_topic_field(self):
        """Test error when selected topic data missing 'topic' field."""
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"score": 8.5},  # Missing 'topic' field
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()

        with patch("src.workflow.nodes.user_interaction.display_topics_for_selection"):
            with patch("src.workflow.nodes.user_interaction.interrupt", return_value=1):
                result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_handled(self):
        """Test that KeyboardInterrupt is handled gracefully."""
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "Python Async", "score": 8.5},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()

        with patch("src.workflow.nodes.user_interaction.display_topics_for_selection"):
            with patch(
                "src.workflow.nodes.user_interaction.interrupt", side_effect=KeyboardInterrupt()
            ):
                result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"
        assert any("cancelled" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def test_first_topic_selection(self):
        """Test selecting first topic."""
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "First Topic", "score": 9.0},
                {"topic": "Second Topic", "score": 8.0},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()

        with patch("src.workflow.nodes.user_interaction.display_topics_for_selection"):
            with patch("src.workflow.nodes.user_interaction.interrupt", return_value=1):
                result = await node.execute(state)

        assert result["selected_topic"] == "First Topic"

    @pytest.mark.asyncio
    async def test_last_topic_selection(self):
        """Test selecting last topic."""
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "First Topic", "score": 9.0},
                {"topic": "Second Topic", "score": 8.0},
                {"topic": "Last Topic", "score": 7.0},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()

        with patch("src.workflow.nodes.user_interaction.display_topics_for_selection"):
            with patch("src.workflow.nodes.user_interaction.interrupt", return_value=3):
                result = await node.execute(state)

        assert result["selected_topic"] == "Last Topic"


class TestUserApprovalNode:
    """Tests for UserApprovalNode."""

    def test_node_registered_in_registry(self):
        """Test that UserApprovalNode is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("user_approval")

    def test_node_has_correct_name(self):
        """Test that node has correct name property."""
        node = UserApprovalNode()
        assert node.name == "user_approval"

    @pytest.mark.asyncio
    async def test_successful_approval(self):
        """Test successful article approval."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Great article content",
                "seo_title": "Amazing Title",
                "word_count": 1500,
            },
            "revision_count": 0,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch(
                "src.workflow.nodes.user_interaction.interrupt",
                return_value={"decision": "approve"},
            ):
                result = await node.execute(state)

        assert result["user_approval"] is True
        assert result["current_step"] == "save_article"

    @pytest.mark.asyncio
    async def test_revision_request(self):
        """Test revision request with feedback."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Article content",
                "seo_title": "Title",
            },
            "revision_count": 1,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch(
                "src.workflow.nodes.user_interaction.interrupt",
                return_value={"decision": "revise", "feedback": "Please add more examples"},
            ):
                result = await node.execute(state)

        assert result["user_approval"] is False
        assert result["user_feedback"] == "Please add more examples"
        assert result["current_step"] == "revise_article"

    @pytest.mark.asyncio
    async def test_approval_via_cli_prompt(self):
        """Test approval via CLI when interrupt returns None."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            "revision_count": 0,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch("src.workflow.nodes.user_interaction.interrupt", return_value=None):
                with patch(
                    "src.workflow.nodes.user_interaction.prompt_user_approval",
                    return_value=("approve", None),
                ):
                    result = await node.execute(state)

        assert result["user_approval"] is True
        assert result["current_step"] == "save_article"

    @pytest.mark.asyncio
    async def test_revision_via_cli_prompt(self):
        """Test revision via CLI when interrupt returns None."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            "revision_count": 0,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch("src.workflow.nodes.user_interaction.interrupt", return_value=None):
                with patch(
                    "src.workflow.nodes.user_interaction.prompt_user_approval",
                    return_value=("revise", "Add code examples"),
                ):
                    result = await node.execute(state)

        assert result["user_approval"] is False
        assert result["user_feedback"] == "Add code examples"
        assert result["current_step"] == "revise_article"

    @pytest.mark.asyncio
    async def test_missing_reviewed_article_raises_error(self):
        """Test that missing reviewed_article raises error."""
        state = {
            "workflow_id": "test-123",
            "revision_count": 0,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_max_revisions_reached_auto_approves(self):
        """Test that max revisions reached auto-approves article."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            "revision_count": 3,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()
        result = await node.execute(state)

        # Verify auto-approval (no mocking needed, this is pure logic)
        assert result["user_approval"] is True
        assert result["current_step"] == "save_article"

    @pytest.mark.asyncio
    async def test_revision_without_feedback_raises_error(self):
        """Test that revision without feedback raises error."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            "revision_count": 0,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch(
                "src.workflow.nodes.user_interaction.interrupt",
                return_value={"decision": "revise", "feedback": ""},
            ):
                result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_invalid_decision_raises_error(self):
        """Test that invalid decision raises error."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            "revision_count": 0,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch(
                "src.workflow.nodes.user_interaction.interrupt",
                return_value={"decision": "invalid"},
            ):
                result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_handled(self):
        """Test that KeyboardInterrupt is handled gracefully."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            "revision_count": 0,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch(
                "src.workflow.nodes.user_interaction.interrupt", side_effect=KeyboardInterrupt()
            ):
                result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"
        assert any("cancelled" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def test_revision_count_at_limit_minus_one(self):
        """Test revision allowed when count is one less than max."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            "revision_count": 2,
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch(
                "src.workflow.nodes.user_interaction.interrupt",
                return_value={"decision": "revise", "feedback": "Fix this"},
            ):
                result = await node.execute(state)

        # Should allow revision
        assert result["user_approval"] is False
        assert result["current_step"] == "revise_article"

    @pytest.mark.asyncio
    async def test_default_max_revisions_used(self):
        """Test that default max_revisions is used when not provided."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            "revision_count": 0,
            # max_revisions not provided, should default to 3
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch(
                "src.workflow.nodes.user_interaction.interrupt",
                return_value={"decision": "approve"},
            ):
                result = await node.execute(state)

        assert result["user_approval"] is True

    @pytest.mark.asyncio
    async def test_revision_count_defaults_to_zero(self):
        """Test that revision_count defaults to 0 when not provided."""
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            # revision_count not provided
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()

        with patch("src.workflow.nodes.user_interaction.display_article_for_review"):
            with patch(
                "src.workflow.nodes.user_interaction.interrupt",
                return_value={"decision": "approve"},
            ):
                result = await node.execute(state)

        assert result["user_approval"] is True
