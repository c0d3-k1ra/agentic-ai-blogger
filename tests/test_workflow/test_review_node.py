"""Unit tests for ReviewNode.

Tests the integration of ReviewerAgent into the LangGraph workflow,
verifying proper review execution, error handling, and state updates.

Test Coverage:
- Node registration and properties
- Successful article review and optimization
- State updates and transitions
- Error handling for missing/invalid inputs
- SEO metadata validation
- Logging integration
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.reviewer import ReviewedArticle
from src.workflow.nodes import NodeRegistry
from src.workflow.nodes.review import ReviewNode


class TestReviewNode:
    """Test suite for ReviewNode workflow integration."""

    def setup_method(self) -> None:
        """Ensure node is registered before each test."""
        if not NodeRegistry.is_registered("review"):
            from src.workflow.nodes.review import ReviewNode

            NodeRegistry.register("review")(ReviewNode)

    def test_node_registered_in_registry(self) -> None:
        """Verify node is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("review")
        node_class = NodeRegistry.get("review")
        assert node_class == ReviewNode
        node = node_class()
        assert isinstance(node, ReviewNode)

    def test_node_has_correct_name(self) -> None:
        """Verify node name property returns correct identifier."""
        node = ReviewNode()
        assert node.name == "review"

    @pytest.mark.asyncio
    async def test_successful_review(self) -> None:
        """Verify node successfully reviews article draft."""
        node = ReviewNode()

        draft_content = "# Introduction\nThis is a test article."
        topic = "Python Programming"

        state = {
            "draft_content": draft_content,
            "selected_topic": topic,
            "workflow_id": "test-wf-001",
        }

        # Mock review_article
        mock_reviewed = ReviewedArticle(
            polished_content="# Improved Introduction\nThis is an improved article.",
            seo_title="Python Programming: Complete Guide",
            seo_subtitle="Learn Python with practical examples",
            tags=("python", "programming", "tutorial", "guide", "coding"),
            word_count=150,
            readability_score="High School",
            improvements_made="Improved clarity and SEO",
        )

        with patch(
            "src.workflow.nodes.review.review_article", new=AsyncMock(return_value=mock_reviewed)
        ):
            result = await node.execute(state)

        # Verify state updates
        assert "reviewed_article" in result
        assert "current_step" in result
        assert result["current_step"] == "publish"

        # Verify reviewed article
        reviewed = result["reviewed_article"]
        assert isinstance(reviewed, ReviewedArticle)
        assert reviewed.seo_title
        assert len(reviewed.tags) >= 5

    @pytest.mark.asyncio
    async def test_review_article_called_with_correct_params(self) -> None:
        """Verify review_article is called with correct parameters."""
        node = ReviewNode()

        draft_content = "# Test Article\nContent here."
        topic = "Machine Learning"

        state = {
            "draft_content": draft_content,
            "selected_topic": topic,
            "workflow_id": "test-wf-002",
        }

        mock_reviewed = ReviewedArticle(
            polished_content="Polished content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1", "tag2", "tag3", "tag4", "tag5"),
            word_count=100,
            readability_score="College",
            improvements_made="Various improvements",
        )

        mock_review = AsyncMock(return_value=mock_reviewed)

        with patch("src.workflow.nodes.review.review_article", new=mock_review):
            await node.execute(state)

        # Verify review_article was called correctly
        mock_review.assert_called_once()
        call_args = mock_review.call_args
        assert call_args[0][0] == topic  # First arg is topic
        assert call_args[0][1] == draft_content  # Second arg is content
        assert call_args[1]["min_tags"] == 5
        assert call_args[1]["max_tags"] == 7

    @pytest.mark.asyncio
    async def test_missing_draft_content_raises_error(self) -> None:
        """Verify missing draft_content results in error state."""
        node = ReviewNode()
        state = {
            "selected_topic": "Python",
            "workflow_id": "test-wf-003",
        }

        result = await node.execute(state)

        # @handle_node_errors should catch ValueError and set error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_empty_draft_content_raises_error(self) -> None:
        """Verify empty draft_content results in error state."""
        node = ReviewNode()
        state = {
            "draft_content": "",
            "selected_topic": "Python",
            "workflow_id": "test-wf-004",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_whitespace_draft_content_raises_error(self) -> None:
        """Verify whitespace-only draft_content results in error state."""
        node = ReviewNode()
        state = {
            "draft_content": "   \n\t  ",
            "selected_topic": "Python",
            "workflow_id": "test-wf-005",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_missing_topic_raises_error(self) -> None:
        """Verify missing selected_topic results in error state."""
        node = ReviewNode()
        state = {
            "draft_content": "# Article\nContent here.",
            "workflow_id": "test-wf-006",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_empty_topic_raises_error(self) -> None:
        """Verify empty selected_topic results in error state."""
        node = ReviewNode()
        state = {
            "draft_content": "# Article\nContent here.",
            "selected_topic": "",
            "workflow_id": "test-wf-007",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_logging_decorator_applied(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify @log_node_execution decorator logs execution."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = ReviewNode()
        state = {
            "draft_content": "# Test\nContent.",
            "selected_topic": "Python",
            "workflow_id": "test-wf-008",
        }

        mock_reviewed = ReviewedArticle(
            polished_content="Polished",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1", "tag2", "tag3", "tag4", "tag5"),
            word_count=50,
            readability_score="High School",
            improvements_made="Improvements",
        )

        with patch(
            "src.workflow.nodes.review.review_article", new=AsyncMock(return_value=mock_reviewed)
        ):
            await node.execute(state)

        # Check for start and end logs
        log_messages = [record.message for record in caplog.records]
        start_logs = [m for m in log_messages if "Starting execution" in m and "review" in m]
        end_logs = [m for m in log_messages if "Completed execution" in m and "review" in m]

        assert len(start_logs) > 0, "Should log execution start"
        assert len(end_logs) > 0, "Should log execution end"

    @pytest.mark.asyncio
    async def test_workflow_id_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify workflow_id is included in log messages."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = ReviewNode()
        workflow_id = "test-wf-009"
        state = {
            "draft_content": "# Test\nContent.",
            "selected_topic": "React",
            "workflow_id": workflow_id,
        }

        mock_reviewed = ReviewedArticle(
            polished_content="Polished",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1", "tag2", "tag3", "tag4", "tag5"),
            word_count=50,
            readability_score="College",
            improvements_made="Improvements",
        )

        with patch(
            "src.workflow.nodes.review.review_article", new=AsyncMock(return_value=mock_reviewed)
        ):
            await node.execute(state)

        # Check that workflow_id appears in logs
        log_messages = [record.message for record in caplog.records]
        workflow_logs = [m for m in log_messages if workflow_id in m]

        assert len(workflow_logs) > 0, f"Should include workflow_id {workflow_id} in logs"

    @pytest.mark.asyncio
    async def test_reviewed_article_structure(self) -> None:
        """Verify reviewed_article has all required fields."""
        node = ReviewNode()
        state = {
            "draft_content": "# Test Article\nOriginal content.",
            "selected_topic": "Docker",
            "workflow_id": "test-wf-010",
        }

        mock_reviewed = ReviewedArticle(
            polished_content="# Test Article\nPolished content.",
            seo_title="Docker Containers: A Complete Guide",
            seo_subtitle="Master Docker with practical examples and best practices",
            tags=("docker", "containers", "devops", "kubernetes", "deployment"),
            word_count=250,
            readability_score="High School",
            improvements_made="Enhanced clarity, added examples, improved SEO",
        )

        with patch(
            "src.workflow.nodes.review.review_article", new=AsyncMock(return_value=mock_reviewed)
        ):
            result = await node.execute(state)

        reviewed = result["reviewed_article"]

        # Verify all fields are present
        assert reviewed.polished_content
        assert reviewed.seo_title
        assert reviewed.seo_subtitle
        assert len(reviewed.tags) >= 5
        assert reviewed.word_count > 0
        assert reviewed.readability_score
        assert reviewed.improvements_made
