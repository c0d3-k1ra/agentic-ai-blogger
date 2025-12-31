"""Unit tests for ResearchNode.

Tests the integration of ResearcherAgent into the LangGraph workflow,
verifying proper research execution, error handling, and state updates.

Test Coverage:
- Node registration and properties
- Successful research for all sections
- State updates and transitions
- Error handling for missing/invalid inputs
- Research data structure validation
- Logging integration
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.researcher import ResearchDossier
from src.agents.structure_planner import Outline, Section, generate_outline
from src.workflow.nodes import NodeRegistry
from src.workflow.nodes.research import ResearchNode


class TestResearchNode:
    """Test suite for ResearchNode workflow integration."""

    def setup_method(self) -> None:
        """Ensure node is registered before each test."""
        # Re-register node in case registry was cleared by other tests
        if not NodeRegistry.is_registered("research"):
            from src.workflow.nodes.research import ResearchNode

            NodeRegistry.register("research")(ResearchNode)

    def test_node_registered_in_registry(self) -> None:
        """Verify node is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("research")
        node_class = NodeRegistry.get("research")
        assert node_class == ResearchNode
        node = node_class()
        assert isinstance(node, ResearchNode)

    def test_node_has_correct_name(self) -> None:
        """Verify node name property returns correct identifier."""
        node = ResearchNode()
        assert node.name == "research"

    @pytest.mark.asyncio
    async def test_successful_research_all_sections(self) -> None:
        """Verify node researches all sections in outline."""
        node = ResearchNode()

        # Create a simple outline
        outline = generate_outline("Python", max_sections=3)

        state = {
            "article_outline": outline,
            "selected_topic": "Python",
            "workflow_id": "test-wf-001",
        }

        # Mock research_section to avoid API calls
        mock_dossier = ResearchDossier(
            section_title="Test Section",
            synthesis="Test synthesis",
            web_results=(),
            papers=(),
            code_examples=(),
            citations=(),
        )

        with patch(
            "src.workflow.nodes.research.research_section", new=AsyncMock(return_value=mock_dossier)
        ):
            result = await node.execute(state)

        # Verify state updates
        assert "research_data" in result
        assert "current_step" in result
        assert result["current_step"] == "write_draft"

        # Verify research data
        research_data = result["research_data"]
        assert isinstance(research_data, list)
        assert len(research_data) == len(outline.sections)
        assert all(isinstance(d, ResearchDossier) for d in research_data)

    @pytest.mark.asyncio
    async def test_research_called_for_each_section(self) -> None:
        """Verify research_section is called once per outline section."""
        node = ResearchNode()

        outline = generate_outline("Machine Learning", max_sections=4)

        state = {
            "article_outline": outline,
            "workflow_id": "test-wf-002",
        }

        mock_dossier = ResearchDossier(
            section_title="Test",
            synthesis="Test",
            web_results=(),
            papers=(),
            code_examples=(),
            citations=(),
        )

        mock_research = AsyncMock(return_value=mock_dossier)

        with patch("src.workflow.nodes.research.research_section", new=mock_research):
            await node.execute(state)

        # Verify research_section was called for each section
        assert mock_research.call_count == len(outline.sections)

        # Verify correct sections were passed
        for i, call in enumerate(mock_research.call_args_list):
            args, kwargs = call
            assert args[0] == outline  # First arg is outline
            assert args[1] == outline.sections[i]  # Second arg is section

    @pytest.mark.asyncio
    async def test_missing_outline_raises_error(self) -> None:
        """Verify missing article_outline results in error state."""
        node = ResearchNode()
        state = {
            "workflow_id": "test-wf-003",
        }

        result = await node.execute(state)

        # @handle_node_errors should catch ValueError and set error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_none_outline_raises_error(self) -> None:
        """Verify None article_outline results in error state."""
        node = ResearchNode()
        state = {
            "article_outline": None,
            "workflow_id": "test-wf-004",
        }

        result = await node.execute(state)

        # Should return error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_outline_without_sections_raises_error(self) -> None:
        """Verify outline without sections results in error state."""
        node = ResearchNode()

        # Create invalid outline-like object
        class FakeOutline:
            pass

        state = {
            "article_outline": FakeOutline(),
            "workflow_id": "test-wf-005",
        }

        result = await node.execute(state)

        # Should return error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_empty_sections_raises_error(self) -> None:
        """Verify outline with empty sections tuple results in error."""
        node = ResearchNode()

        # Create outline with empty sections
        outline = Outline(topic="Test", sections=())

        state = {
            "article_outline": outline,
            "workflow_id": "test-wf-006",
        }

        result = await node.execute(state)

        # Should return error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_logging_decorator_applied(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify @log_node_execution decorator logs execution."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = ResearchNode()
        outline = generate_outline("Python", max_sections=2)

        state = {
            "article_outline": outline,
            "workflow_id": "test-wf-007",
        }

        mock_dossier = ResearchDossier(
            section_title="Test",
            synthesis="Test",
            web_results=(),
            papers=(),
            code_examples=(),
            citations=(),
        )

        with patch(
            "src.workflow.nodes.research.research_section", new=AsyncMock(return_value=mock_dossier)
        ):
            await node.execute(state)

        # Check for start and end logs
        log_messages = [record.message for record in caplog.records]
        start_logs = [m for m in log_messages if "Starting execution" in m and "research" in m]
        end_logs = [m for m in log_messages if "Completed execution" in m and "research" in m]

        assert len(start_logs) > 0, "Should log execution start"
        assert len(end_logs) > 0, "Should log execution end"

    @pytest.mark.asyncio
    async def test_workflow_id_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify workflow_id is included in log messages."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = ResearchNode()
        workflow_id = "test-wf-008"
        outline = generate_outline("JavaScript", max_sections=2)

        state = {
            "article_outline": outline,
            "workflow_id": workflow_id,
        }

        mock_dossier = ResearchDossier(
            section_title="Test",
            synthesis="Test",
            web_results=(),
            papers=(),
            code_examples=(),
            citations=(),
        )

        with patch(
            "src.workflow.nodes.research.research_section", new=AsyncMock(return_value=mock_dossier)
        ):
            await node.execute(state)

        # Check that workflow_id appears in logs
        log_messages = [record.message for record in caplog.records]
        workflow_logs = [m for m in log_messages if workflow_id in m]

        assert len(workflow_logs) > 0, f"Should include workflow_id {workflow_id} in logs"

    @pytest.mark.asyncio
    async def test_research_data_structure(self) -> None:
        """Verify research_data has correct structure."""
        node = ResearchNode()
        outline = generate_outline("Docker", max_sections=3)

        state = {
            "article_outline": outline,
            "workflow_id": "test-wf-009",
        }

        # Create varied mock dossiers
        mock_dossiers = [
            ResearchDossier(
                section_title=section.title,
                synthesis=f"Synthesis for {section.title}",
                web_results=({"title": "Test", "url": "http://test.com"},),
                papers=({"title": "Paper", "entry_id": "arxiv:123"},),
                code_examples=({"name": "repo", "url": "http://github.com/test"},),
                citations=("Citation 1", "Citation 2"),
            )
            for section in outline.sections
        ]

        call_count = 0

        async def mock_research_fn(outline, section):
            nonlocal call_count
            result = mock_dossiers[call_count]
            call_count += 1
            return result

        with patch("src.workflow.nodes.research.research_section", new=mock_research_fn):
            result = await node.execute(state)

        research_data = result["research_data"]

        # Verify each dossier
        for i, dossier in enumerate(research_data):
            assert dossier.section_title == outline.sections[i].title
            assert len(dossier.synthesis) > 0
            assert isinstance(dossier.web_results, tuple)
            assert isinstance(dossier.papers, tuple)
            assert isinstance(dossier.code_examples, tuple)
            assert isinstance(dossier.citations, tuple)

    @pytest.mark.asyncio
    async def test_research_preserves_outline_order(self) -> None:
        """Verify research_data preserves outline section order."""
        node = ResearchNode()
        outline = generate_outline("Rust Programming", max_sections=5)

        state = {
            "article_outline": outline,
            "workflow_id": "test-wf-010",
        }

        # Mock with section-specific dossiers
        async def mock_research_fn(outline, section):
            return ResearchDossier(
                section_title=section.title,
                synthesis=f"Research for {section.title}",
                web_results=(),
                papers=(),
                code_examples=(),
                citations=(),
            )

        with patch("src.workflow.nodes.research.research_section", new=mock_research_fn):
            result = await node.execute(state)

        research_data = result["research_data"]

        # Verify order matches outline
        for i, dossier in enumerate(research_data):
            assert dossier.section_title == outline.sections[i].title

    @pytest.mark.asyncio
    async def test_single_section_outline(self) -> None:
        """Verify node handles outline with single section."""
        node = ResearchNode()

        # Create minimal outline
        section = Section(title="Introduction", subsections=("Overview",))
        outline = Outline(topic="Test", sections=(section,))

        state = {
            "article_outline": outline,
            "workflow_id": "test-wf-011",
        }

        mock_dossier = ResearchDossier(
            section_title="Introduction",
            synthesis="Test",
            web_results=(),
            papers=(),
            code_examples=(),
            citations=(),
        )

        with patch(
            "src.workflow.nodes.research.research_section", new=AsyncMock(return_value=mock_dossier)
        ):
            result = await node.execute(state)

        # Should succeed with single section
        assert "research_data" in result
        assert len(result["research_data"]) == 1
        assert result["current_step"] == "write_draft"
