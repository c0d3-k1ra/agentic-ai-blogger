"""Unit tests for PublishNode.

Tests the integration of database persistence into the LangGraph workflow,
verifying proper article/topic creation, error handling, and state updates.

Test Coverage:
- Node registration and properties
- Successful article publication
- Topic creation (new topic)
- Topic reuse (existing topic)
- Metadata storage validation
- Error handling for missing/invalid inputs
- Database session management
- Logging integration
"""

from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from src.agents.reviewer import ReviewedArticle
from src.agents.structure_planner import Outline, Section
from src.workflow.nodes import NodeRegistry
from src.workflow.nodes.publish import PublishNode


class TestPublishNode:
    """Test suite for PublishNode workflow integration."""

    def setup_method(self) -> None:
        """Ensure node is registered before each test."""
        if not NodeRegistry.is_registered("publish"):
            from src.workflow.nodes.publish import PublishNode

            NodeRegistry.register("publish")(PublishNode)

    def test_node_registered_in_registry(self) -> None:
        """Verify node is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("publish")
        node_class = NodeRegistry.get("publish")
        assert node_class == PublishNode
        node = node_class()
        assert isinstance(node, PublishNode)

    def test_node_has_correct_name(self) -> None:
        """Verify node name property returns correct identifier."""
        node = PublishNode()
        assert node.name == "publish"

    @pytest.mark.asyncio
    async def test_successful_publish_with_new_topic(self) -> None:
        """Verify node successfully publishes article and creates new topic."""
        node = PublishNode()

        reviewed = ReviewedArticle(
            polished_content="# Article\nContent here.",
            seo_title="Great Article Title",
            seo_subtitle="Amazing subtitle for SEO",
            tags=("python", "programming", "tutorial"),
            word_count=250,
            readability_score="High School",
            improvements_made="Various improvements",
        )

        outline = Outline(
            topic="Python Programming",
            sections=(
                Section(
                    title="Introduction",
                    subsections=("Overview", "Background"),
                ),
            ),
        )

        state = {
            "reviewed_article": reviewed,
            "selected_topic": "Python Programming",
            "article_outline": outline,
            "workflow_id": "test-wf-001",
        }

        # Mock database operations
        mock_session = MagicMock()
        mock_topic = Mock()
        mock_topic.id = uuid4()
        mock_article = Mock()
        mock_article.id = uuid4()
        mock_article.status = "draft"

        with (
            patch("src.workflow.nodes.publish.get_session") as mock_get_session,
            patch("src.workflow.nodes.publish.get_topic_by_name") as mock_get_topic,
            patch("src.workflow.nodes.publish.create_topic") as mock_create_topic,
            patch("src.workflow.nodes.publish.create_article") as mock_create_article,
        ):
            # Setup mocks
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_get_topic.return_value = None  # Topic doesn't exist
            mock_create_topic.return_value = mock_topic
            mock_create_article.return_value = mock_article

            result = await node.execute(state)

        # Verify state updates
        assert "article_id" in result
        assert "published_at" in result
        assert "current_step" in result
        assert result["current_step"] == "complete"

        # Verify topic was created
        mock_create_topic.assert_called_once()
        call_kwargs = mock_create_topic.call_args[1]
        assert call_kwargs["name"] == "Python Programming"

        # Verify article was created
        mock_create_article.assert_called_once()
        call_kwargs = mock_create_article.call_args[1]
        assert call_kwargs["topic_id"] == mock_topic.id
        assert call_kwargs["title"] == reviewed.seo_title
        assert call_kwargs["content"] == reviewed.polished_content

    @pytest.mark.asyncio
    async def test_successful_publish_with_existing_topic(self) -> None:
        """Verify node reuses existing topic instead of creating new one."""
        node = PublishNode()

        reviewed = ReviewedArticle(
            polished_content="# Content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1", "tag2"),
            word_count=100,
            readability_score="College",
            improvements_made="Improvements",
        )

        state = {
            "reviewed_article": reviewed,
            "selected_topic": "Existing Topic",
            "workflow_id": "test-wf-002",
        }

        # Mock database operations
        mock_session = MagicMock()
        existing_topic = Mock()
        existing_topic.id = uuid4()
        mock_article = Mock()
        mock_article.id = uuid4()

        with (
            patch("src.workflow.nodes.publish.get_session") as mock_get_session,
            patch("src.workflow.nodes.publish.get_topic_by_name") as mock_get_topic,
            patch("src.workflow.nodes.publish.create_topic") as mock_create_topic,
            patch("src.workflow.nodes.publish.create_article") as mock_create_article,
        ):
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_get_topic.return_value = existing_topic  # Topic exists
            mock_create_article.return_value = mock_article

            await node.execute(state)

        # Verify topic was NOT created
        mock_create_topic.assert_not_called()

        # Verify article was created with existing topic
        mock_create_article.assert_called_once()
        call_kwargs = mock_create_article.call_args[1]
        assert call_kwargs["topic_id"] == existing_topic.id

    @pytest.mark.asyncio
    async def test_metadata_includes_all_fields(self) -> None:
        """Verify metadata includes all ReviewedArticle fields."""
        node = PublishNode()

        reviewed = ReviewedArticle(
            polished_content="Content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1", "tag2", "tag3"),
            word_count=150,
            readability_score="High School",
            improvements_made="Improved clarity",
        )

        state = {
            "reviewed_article": reviewed,
            "selected_topic": "Topic",
            "workflow_id": "test-wf-003",
        }

        mock_session = MagicMock()
        mock_topic = Mock()
        mock_topic.id = uuid4()
        mock_article = Mock()
        mock_article.id = uuid4()

        with (
            patch("src.workflow.nodes.publish.get_session") as mock_get_session,
            patch("src.workflow.nodes.publish.get_topic_by_name", return_value=mock_topic),
            patch("src.workflow.nodes.publish.create_article") as mock_create_article,
        ):
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_create_article.return_value = mock_article

            await node.execute(state)

        # Verify metadata contains all fields
        call_kwargs = mock_create_article.call_args[1]
        metadata = call_kwargs["metadata"]

        assert metadata["seo_title"] == reviewed.seo_title
        assert metadata["seo_subtitle"] == reviewed.seo_subtitle
        assert metadata["tags"] == list(reviewed.tags)
        assert metadata["word_count"] == reviewed.word_count
        assert metadata["readability_score"] == reviewed.readability_score
        assert metadata["improvements_made"] == reviewed.improvements_made

    @pytest.mark.asyncio
    async def test_metadata_includes_outline_when_present(self) -> None:
        """Verify metadata includes outline structure when available."""
        node = PublishNode()

        reviewed = ReviewedArticle(
            polished_content="Content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1",),
            word_count=100,
            readability_score="College",
            improvements_made="Improvements",
        )

        outline = Outline(
            topic="Test Topic",
            sections=(
                Section(
                    title="Section 1",
                    subsections=("Sub 1", "Sub 2"),
                ),
                Section(
                    title="Section 2",
                    subsections=("Sub 3",),
                ),
            ),
        )

        state = {
            "reviewed_article": reviewed,
            "selected_topic": "Test Topic",
            "article_outline": outline,
            "workflow_id": "test-wf-004",
        }

        mock_session = MagicMock()
        mock_topic = Mock()
        mock_topic.id = uuid4()
        mock_article = Mock()
        mock_article.id = uuid4()

        with (
            patch("src.workflow.nodes.publish.get_session") as mock_get_session,
            patch("src.workflow.nodes.publish.get_topic_by_name", return_value=mock_topic),
            patch("src.workflow.nodes.publish.create_article") as mock_create_article,
        ):
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            mock_create_article.return_value = mock_article

            await node.execute(state)

        # Verify outline is in metadata
        call_kwargs = mock_create_article.call_args[1]
        metadata = call_kwargs["metadata"]

        assert "outline" in metadata
        assert metadata["outline"]["topic"] == outline.topic
        assert len(metadata["outline"]["sections"]) == 2

    @pytest.mark.asyncio
    async def test_article_status_set_to_published(self) -> None:
        """Verify article status is set to published."""
        node = PublishNode()

        reviewed = ReviewedArticle(
            polished_content="Content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1",),
            word_count=100,
            readability_score="College",
            improvements_made="Improvements",
        )

        state = {
            "reviewed_article": reviewed,
            "selected_topic": "Topic",
            "workflow_id": "test-wf-005",
        }

        mock_session = MagicMock()
        mock_topic = Mock()
        mock_topic.id = uuid4()
        mock_article = Mock()
        mock_article.id = uuid4()
        mock_article.status = "draft"  # Initial status

        with (
            patch("src.workflow.nodes.publish.get_session") as mock_get_session,
            patch("src.workflow.nodes.publish.get_topic_by_name", return_value=mock_topic),
            patch("src.workflow.nodes.publish.create_article", return_value=mock_article),
        ):
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            await node.execute(state)

        # Verify status was updated to published
        assert mock_article.status == "published"
        assert mock_article.published_at is not None

    @pytest.mark.asyncio
    async def test_missing_reviewed_article_raises_error(self) -> None:
        """Verify missing reviewed_article results in error state."""
        node = PublishNode()
        state = {
            "selected_topic": "Topic",
            "workflow_id": "test-wf-006",
        }

        result = await node.execute(state)

        # @handle_node_errors should catch ValueError and set error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_none_reviewed_article_raises_error(self) -> None:
        """Verify None reviewed_article results in error state."""
        node = PublishNode()
        state = {
            "reviewed_article": None,
            "selected_topic": "Topic",
            "workflow_id": "test-wf-007",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_invalid_reviewed_article_raises_error(self) -> None:
        """Verify invalid reviewed_article (missing attributes) results in error."""
        node = PublishNode()
        state = {
            "reviewed_article": {"not": "a ReviewedArticle"},
            "selected_topic": "Topic",
            "workflow_id": "test-wf-008",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_missing_topic_raises_error(self) -> None:
        """Verify missing selected_topic results in error state."""
        node = PublishNode()

        reviewed = ReviewedArticle(
            polished_content="Content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1",),
            word_count=100,
            readability_score="College",
            improvements_made="Improvements",
        )

        state = {
            "reviewed_article": reviewed,
            "workflow_id": "test-wf-009",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_empty_topic_raises_error(self) -> None:
        """Verify empty selected_topic results in error state."""
        node = PublishNode()

        reviewed = ReviewedArticle(
            polished_content="Content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1",),
            word_count=100,
            readability_score="College",
            improvements_made="Improvements",
        )

        state = {
            "reviewed_article": reviewed,
            "selected_topic": "",
            "workflow_id": "test-wf-010",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_logging_decorator_applied(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify @log_node_execution decorator logs execution."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = PublishNode()

        reviewed = ReviewedArticle(
            polished_content="Content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1",),
            word_count=100,
            readability_score="College",
            improvements_made="Improvements",
        )

        state = {
            "reviewed_article": reviewed,
            "selected_topic": "Topic",
            "workflow_id": "test-wf-011",
        }

        mock_session = MagicMock()
        mock_topic = Mock()
        mock_topic.id = uuid4()
        mock_article = Mock()
        mock_article.id = uuid4()

        with (
            patch("src.workflow.nodes.publish.get_session") as mock_get_session,
            patch("src.workflow.nodes.publish.get_topic_by_name", return_value=mock_topic),
            patch("src.workflow.nodes.publish.create_article", return_value=mock_article),
        ):
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            await node.execute(state)

        # Check for start and end logs
        log_messages = [record.message for record in caplog.records]
        start_logs = [m for m in log_messages if "Starting execution" in m and "publish" in m]
        end_logs = [m for m in log_messages if "Completed execution" in m and "publish" in m]

        assert len(start_logs) > 0, "Should log execution start"
        assert len(end_logs) > 0, "Should log execution end"

    @pytest.mark.asyncio
    async def test_workflow_id_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify workflow_id is included in log messages."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = PublishNode()
        workflow_id = "test-wf-012"

        reviewed = ReviewedArticle(
            polished_content="Content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1",),
            word_count=100,
            readability_score="College",
            improvements_made="Improvements",
        )

        state = {
            "reviewed_article": reviewed,
            "selected_topic": "Topic",
            "workflow_id": workflow_id,
        }

        mock_session = MagicMock()
        mock_topic = Mock()
        mock_topic.id = uuid4()
        mock_article = Mock()
        mock_article.id = uuid4()

        with (
            patch("src.workflow.nodes.publish.get_session") as mock_get_session,
            patch("src.workflow.nodes.publish.get_topic_by_name", return_value=mock_topic),
            patch("src.workflow.nodes.publish.create_article", return_value=mock_article),
        ):
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            await node.execute(state)

        # Check that workflow_id appears in logs
        log_messages = [record.message for record in caplog.records]
        workflow_logs = [m for m in log_messages if workflow_id in m]

        assert len(workflow_logs) > 0, f"Should include workflow_id {workflow_id} in logs"

    @pytest.mark.asyncio
    async def test_article_id_is_string_uuid(self) -> None:
        """Verify returned article_id is a string representation of UUID."""
        node = PublishNode()

        reviewed = ReviewedArticle(
            polished_content="Content",
            seo_title="Title",
            seo_subtitle="Subtitle",
            tags=("tag1",),
            word_count=100,
            readability_score="College",
            improvements_made="Improvements",
        )

        state = {
            "reviewed_article": reviewed,
            "selected_topic": "Topic",
            "workflow_id": "test-wf-013",
        }

        mock_session = MagicMock()
        mock_topic = Mock()
        mock_topic.id = uuid4()
        mock_article = Mock()
        mock_article_id = uuid4()
        mock_article.id = mock_article_id

        with (
            patch("src.workflow.nodes.publish.get_session") as mock_get_session,
            patch("src.workflow.nodes.publish.get_topic_by_name", return_value=mock_topic),
            patch("src.workflow.nodes.publish.create_article", return_value=mock_article),
        ):
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            result = await node.execute(state)

        # Verify article_id is string and can be parsed as UUID
        article_id = result["article_id"]
        assert isinstance(article_id, str)
        assert UUID(article_id) == mock_article_id
