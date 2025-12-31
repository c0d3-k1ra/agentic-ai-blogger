"""Unit tests for WriteDraftNode.

Tests the integration of WriterAgent into the LangGraph workflow,
verifying proper draft generation, error handling, and state updates.

Test Coverage:
- Node registration and properties
- Successful draft generation for all sections
- State updates and transitions
- Error handling for missing/invalid inputs
- Draft content structure validation
- Logging integration
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.structure_planner import generate_outline
from src.agents.writer import WrittenSection
from src.workflow.nodes import NodeRegistry
from src.workflow.nodes.write_draft import WriteDraftNode


class TestWriteDraftNode:
    """Test suite for WriteDraftNode workflow integration."""

    def setup_method(self) -> None:
        """Ensure node is registered before each test."""
        if not NodeRegistry.is_registered("write_draft"):
            from src.workflow.nodes.write_draft import WriteDraftNode

            NodeRegistry.register("write_draft")(WriteDraftNode)

    def test_node_registered_in_registry(self) -> None:
        """Verify node is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("write_draft")
        node_class = NodeRegistry.get("write_draft")
        assert node_class == WriteDraftNode
        node = node_class()
        assert isinstance(node, WriteDraftNode)

    def test_node_has_correct_name(self) -> None:
        """Verify node name property returns correct identifier."""
        node = WriteDraftNode()
        assert node.name == "write_draft"

    @pytest.mark.asyncio
    async def test_successful_draft_generation(self) -> None:
        """Verify node successfully generates draft from outline."""
        node = WriteDraftNode()
        outline = generate_outline("Python", max_sections=3)

        # Create mock research data (one per section)
        research_data = [{"section": s.title} for s in outline.sections]

        state = {
            "article_outline": outline,
            "research_data": research_data,
            "workflow_id": "test-wf-001",
        }

        # Mock write_section
        async def mock_write_section(outline, section, **kwargs):
            return WrittenSection(
                section_title=section.title,
                content=f"Content for {section.title}",
                word_count=50,
            )

        with patch("src.workflow.nodes.write_draft.write_section", new=mock_write_section):
            result = await node.execute(state)

        # Verify state updates
        assert "draft_sections" in result
        assert "draft_content" in result
        assert "current_step" in result
        assert result["current_step"] == "review"

        # Verify draft sections
        draft_sections = result["draft_sections"]
        assert len(draft_sections) == len(outline.sections)
        assert all(isinstance(s, WrittenSection) for s in draft_sections)

    @pytest.mark.asyncio
    async def test_draft_content_structure(self) -> None:
        """Verify draft_content has correct markdown structure."""
        node = WriteDraftNode()
        outline = generate_outline("Python Async", max_sections=3)
        research_data = [{"section": s.title} for s in outline.sections]

        state = {
            "article_outline": outline,
            "research_data": research_data,
            "workflow_id": "test-wf-002",
        }

        async def mock_write_section(outline, section, **kwargs):
            return WrittenSection(
                section_title=section.title,
                content=f"Content for {section.title}",
                word_count=50,
            )

        with patch("src.workflow.nodes.write_draft.write_section", new=mock_write_section):
            result = await node.execute(state)

        draft_content = result["draft_content"]

        # Verify structure
        assert draft_content.startswith(f"# {outline.topic}")
        for section in outline.sections:
            assert f"## {section.title}" in draft_content
            assert f"Content for {section.title}" in draft_content

    @pytest.mark.asyncio
    async def test_write_section_called_for_each_section(self) -> None:
        """Verify write_section is called once per outline section."""
        node = WriteDraftNode()
        outline = generate_outline("Machine Learning", max_sections=4)
        research_data = [{"section": s.title} for s in outline.sections]

        state = {
            "article_outline": outline,
            "research_data": research_data,
            "workflow_id": "test-wf-003",
        }

        mock_write = AsyncMock(
            return_value=WrittenSection(
                section_title="Test",
                content="Test content",
                word_count=50,
            )
        )

        with patch("src.workflow.nodes.write_draft.write_section", new=mock_write):
            await node.execute(state)

        # Verify write_section was called for each section
        assert mock_write.call_count == len(outline.sections)

        # Verify correct sections were passed
        for i, call in enumerate(mock_write.call_args_list):
            args, kwargs = call
            assert args[0] == outline  # First arg is outline
            assert args[1] == outline.sections[i]  # Second arg is section
            assert kwargs.get("target_words") == 500

    @pytest.mark.asyncio
    async def test_missing_outline_raises_error(self) -> None:
        """Verify missing article_outline results in error state."""
        node = WriteDraftNode()
        state = {
            "research_data": [{}],
            "workflow_id": "test-wf-004",
        }

        result = await node.execute(state)

        # @handle_node_errors should catch ValueError and set error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_none_outline_raises_error(self) -> None:
        """Verify None article_outline results in error state."""
        node = WriteDraftNode()
        state = {
            "article_outline": None,
            "research_data": [{}],
            "workflow_id": "test-wf-005",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_missing_research_data_raises_error(self) -> None:
        """Verify missing research_data results in error state."""
        node = WriteDraftNode()
        outline = generate_outline("Python", max_sections=3)

        state = {
            "article_outline": outline,
            "workflow_id": "test-wf-006",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_mismatched_research_data_length_raises_error(self) -> None:
        """Verify research_data length must match sections length."""
        node = WriteDraftNode()
        outline = generate_outline("Python", max_sections=3)

        # Wrong number of research items
        state = {
            "article_outline": outline,
            "research_data": [{"section": "only one"}],
            "workflow_id": "test-wf-007",
        }

        result = await node.execute(state)

        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_section_order_preserved(self) -> None:
        """Verify draft preserves outline section order."""
        node = WriteDraftNode()
        outline = generate_outline("Rust Programming", max_sections=5)
        research_data = [{"section": s.title} for s in outline.sections]

        state = {
            "article_outline": outline,
            "research_data": research_data,
            "workflow_id": "test-wf-008",
        }

        async def mock_write_section(outline, section, **kwargs):
            return WrittenSection(
                section_title=section.title,
                content=f"Content for {section.title}",
                word_count=50,
            )

        with patch("src.workflow.nodes.write_draft.write_section", new=mock_write_section):
            result = await node.execute(state)

        draft_sections = result["draft_sections"]

        # Verify order matches outline
        for i, written_section in enumerate(draft_sections):
            assert written_section.section_title == outline.sections[i].title

    @pytest.mark.asyncio
    async def test_logging_decorator_applied(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify @log_node_execution decorator logs execution."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = WriteDraftNode()
        outline = generate_outline("Python", max_sections=2)
        research_data = [{"section": s.title} for s in outline.sections]

        state = {
            "article_outline": outline,
            "research_data": research_data,
            "workflow_id": "test-wf-009",
        }

        mock_written = WrittenSection(
            section_title="Test",
            content="Test content",
            word_count=50,
        )

        with patch(
            "src.workflow.nodes.write_draft.write_section",
            new=AsyncMock(return_value=mock_written),
        ):
            await node.execute(state)

        # Check for start and end logs
        log_messages = [record.message for record in caplog.records]
        start_logs = [m for m in log_messages if "Starting execution" in m and "write_draft" in m]
        end_logs = [m for m in log_messages if "Completed execution" in m and "write_draft" in m]

        assert len(start_logs) > 0, "Should log execution start"
        assert len(end_logs) > 0, "Should log execution end"

    @pytest.mark.asyncio
    async def test_workflow_id_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify workflow_id is included in log messages."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = WriteDraftNode()
        workflow_id = "test-wf-010"
        outline = generate_outline("JavaScript", max_sections=2)
        research_data = [{"section": s.title} for s in outline.sections]

        state = {
            "article_outline": outline,
            "research_data": research_data,
            "workflow_id": workflow_id,
        }

        mock_written = WrittenSection(
            section_title="Test",
            content="Test content",
            word_count=50,
        )

        with patch(
            "src.workflow.nodes.write_draft.write_section",
            new=AsyncMock(return_value=mock_written),
        ):
            await node.execute(state)

        # Check that workflow_id appears in logs
        log_messages = [record.message for record in caplog.records]
        workflow_logs = [m for m in log_messages if workflow_id in m]

        assert len(workflow_logs) > 0, f"Should include workflow_id {workflow_id} in logs"
