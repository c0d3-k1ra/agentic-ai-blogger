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
    @patch("src.workflow.nodes.user_interaction.display_topics_for_selection")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    @patch("src.workflow.nodes.user_interaction.prompt_user_topic_selection")
    async def test_successful_topic_selection(self, mock_prompt, mock_interrupt, mock_display):
        """Test successful topic selection flow."""
        # Setup
        mock_interrupt.return_value = 2  # User selects topic 2
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
        result = await node.execute(state)

        # Verify
        assert result["selected_topic"] == "Type Hints"
        assert result["current_step"] == "plan_structure"
        mock_display.assert_called_once()
        mock_interrupt.assert_called_once()
        mock_prompt.assert_not_called()  # Not called when interrupt returns value

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_topics_for_selection")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    @patch("src.workflow.nodes.user_interaction.prompt_user_topic_selection")
    async def test_selection_via_cli_prompt(self, mock_prompt, mock_interrupt, mock_display):
        """Test topic selection via CLI when interrupt returns None."""
        # Setup
        mock_interrupt.return_value = None  # No value from interrupt
        mock_prompt.return_value = 1  # User selects via CLI
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "Python Async", "score": 8.5},
                {"topic": "Type Hints", "score": 7.2},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()
        result = await node.execute(state)

        # Verify
        assert result["selected_topic"] == "Python Async"
        assert result["current_step"] == "plan_structure"
        mock_prompt.assert_called_once_with(2)

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
    @patch("src.workflow.nodes.user_interaction.display_topics_for_selection")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_invalid_selection_index_raises_error(self, mock_interrupt, mock_display):
        """Test that invalid selection index raises error."""
        mock_interrupt.return_value = 99  # Invalid index
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "Python Async", "score": 8.5},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_topics_for_selection")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_zero_selection_index_raises_error(self, mock_interrupt, mock_display):
        """Test that zero selection index raises error."""
        mock_interrupt.return_value = 0  # Invalid (must be 1-based)
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "Python Async", "score": 8.5},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_topics_for_selection")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_topic_missing_topic_field(self, mock_interrupt, mock_display):
        """Test error when selected topic data missing 'topic' field."""
        mock_interrupt.return_value = 1
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"score": 8.5},  # Missing 'topic' field
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_topics_for_selection")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_keyboard_interrupt_handled(self, mock_interrupt, mock_display):
        """Test that KeyboardInterrupt is handled gracefully."""
        mock_interrupt.side_effect = KeyboardInterrupt()
        state = {
            "workflow_id": "test-123",
            "scored_topics": [
                {"topic": "Python Async", "score": 8.5},
            ],
            "current_step": "get_user_selection",
        }

        node = UserSelectionNode()
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"
        assert "cancelled" in result["errors"][0].lower()


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
    @patch("src.workflow.nodes.user_interaction.display_article_for_review")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_successful_approval(self, mock_interrupt, mock_display):
        """Test successful article approval."""
        # Setup
        mock_interrupt.return_value = {"decision": "approve"}
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
        result = await node.execute(state)

        # Verify
        assert result["user_approval"] is True
        assert result["current_step"] == "save_article"
        mock_display.assert_called_once()
        mock_interrupt.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_article_for_review")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_revision_request(self, mock_interrupt, mock_display):
        """Test revision request with feedback."""
        # Setup
        mock_interrupt.return_value = {
            "decision": "revise",
            "feedback": "Please add more examples",
        }
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
        result = await node.execute(state)

        # Verify
        assert result["user_approval"] is False
        assert result["user_feedback"] == "Please add more examples"
        assert result["current_step"] == "revise_article"

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_article_for_review")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    @patch("src.workflow.nodes.user_interaction.prompt_user_approval")
    async def test_approval_via_cli_prompt(self, mock_prompt, mock_interrupt, mock_display):
        """Test approval via CLI when interrupt returns None."""
        # Setup
        mock_interrupt.return_value = None
        mock_prompt.return_value = ("approve", None)
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
        result = await node.execute(state)

        # Verify
        assert result["user_approval"] is True
        assert result["current_step"] == "save_article"
        mock_prompt.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_article_for_review")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    @patch("src.workflow.nodes.user_interaction.prompt_user_approval")
    async def test_revision_via_cli_prompt(self, mock_prompt, mock_interrupt, mock_display):
        """Test revision via CLI when interrupt returns None."""
        # Setup
        mock_interrupt.return_value = None
        mock_prompt.return_value = ("revise", "Add code examples")
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
        result = await node.execute(state)

        # Verify
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

        # Verify auto-approval
        assert result["user_approval"] is True
        assert result["current_step"] == "save_article"

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_article_for_review")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_revision_without_feedback_raises_error(self, mock_interrupt, mock_display):
        """Test that revision without feedback raises error."""
        mock_interrupt.return_value = {"decision": "revise", "feedback": ""}
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
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_article_for_review")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_invalid_decision_raises_error(self, mock_interrupt, mock_display):
        """Test that invalid decision raises error."""
        mock_interrupt.return_value = {"decision": "invalid"}
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
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_article_for_review")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_keyboard_interrupt_handled(self, mock_interrupt, mock_display):
        """Test that KeyboardInterrupt is handled gracefully."""
        mock_interrupt.side_effect = KeyboardInterrupt()
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
        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"
        assert "cancelled" in result["errors"][0].lower()

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.user_interaction.display_article_for_review")
    @patch("src.workflow.nodes.user_interaction.interrupt")
    async def test_revision_count_tracked_correctly(self, mock_interrupt, mock_display):
        """Test that revision count is considered in max check."""
        mock_interrupt.return_value = {"decision": "revise", "feedback": "Fix this"}
        state = {
            "workflow_id": "test-123",
            "reviewed_article": {
                "polished_content": "Content",
            },
            "revision_count": 2,  # One more revision allowed
            "max_revisions": 3,
            "current_step": "get_user_approval",
        }

        node = UserApprovalNode()
        result = await node.execute(state)

        # Should allow revision
        assert result["user_approval"] is False
        assert result["current_step"] == "revise_article"
