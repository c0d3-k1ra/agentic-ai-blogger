"""Unit tests for PlanStructureNode.

Tests the integration of StructurePlannerAgent into the LangGraph workflow,
verifying proper outline generation, error handling, and state updates.

Test Coverage:
- Node registration and properties
- Successful outline generation
- State updates and transitions
- Error handling for empty/invalid inputs
- Outline structure validation
- Logging integration
"""

import pytest

from src.agents.structure_planner import Outline, Section
from src.workflow.nodes import NodeRegistry
from src.workflow.nodes.plan_structure import PlanStructureNode


class TestPlanStructureNode:
    """Test suite for PlanStructureNode workflow integration."""

    def setup_method(self) -> None:
        """Ensure node is registered before each test."""
        # Re-register node in case registry was cleared by other tests
        if not NodeRegistry.is_registered("plan_structure"):
            from src.workflow.nodes.plan_structure import PlanStructureNode

            NodeRegistry.register("plan_structure")(PlanStructureNode)

    def test_node_registered_in_registry(self) -> None:
        """Verify node is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("plan_structure")
        node_class = NodeRegistry.get("plan_structure")
        assert node_class == PlanStructureNode
        node = node_class()
        assert isinstance(node, PlanStructureNode)

    def test_node_has_correct_name(self) -> None:
        """Verify node name property returns correct identifier."""
        node = PlanStructureNode()
        assert node.name == "plan_structure"

    @pytest.mark.asyncio
    async def test_successful_outline_generation(self) -> None:
        """Verify node successfully generates outline from topic."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "Python Async Programming",
            "workflow_id": "test-wf-001",
            "current_step": "plan_structure",
        }

        result = await node.execute(state)

        # Verify state updates
        assert "article_outline" in result
        assert "current_step" in result
        assert result["current_step"] == "research"

        # Verify outline structure
        outline = result["article_outline"]
        assert isinstance(outline, Outline)
        assert outline.topic == "Python Async Programming"
        assert len(outline.sections) > 0

    @pytest.mark.asyncio
    async def test_outline_has_introduction_and_conclusion(self) -> None:
        """Verify generated outline always has intro and conclusion."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "Machine Learning",
            "workflow_id": "test-wf-002",
        }

        result = await node.execute(state)
        outline = result["article_outline"]

        # Check first and last sections
        assert "Introduction" in outline.sections[0].title
        assert "Conclusion" in outline.sections[-1].title

    @pytest.mark.asyncio
    async def test_sections_are_section_objects(self) -> None:
        """Verify all sections are Section objects with subsections."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "Docker Containers",
            "workflow_id": "test-wf-003",
        }

        result = await node.execute(state)
        outline = result["article_outline"]

        # Verify all sections
        for section in outline.sections:
            assert isinstance(section, Section)
            assert isinstance(section.title, str)
            assert len(section.title) > 0
            assert isinstance(section.subsections, tuple)
            assert len(section.subsections) > 0

    @pytest.mark.asyncio
    async def test_empty_topic_raises_error(self) -> None:
        """Verify empty selected_topic results in error state."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "",
            "workflow_id": "test-wf-004",
        }

        result = await node.execute(state)

        # @handle_node_errors should catch ValueError and set error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_whitespace_topic_raises_error(self) -> None:
        """Verify whitespace-only topic results in error state."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "   \n\t  ",
            "workflow_id": "test-wf-005",
        }

        result = await node.execute(state)

        # Should return error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_missing_topic_raises_error(self) -> None:
        """Verify missing selected_topic results in error state."""
        node = PlanStructureNode()
        state = {
            "workflow_id": "test-wf-006",
        }

        result = await node.execute(state)

        # Should return error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_deterministic_output(self) -> None:
        """Verify same topic produces same outline (deterministic)."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "Kubernetes Orchestration",
            "workflow_id": "test-wf-007",
        }

        result1 = await node.execute(state)
        result2 = await node.execute(state)

        # Same input should produce identical outline
        outline1 = result1["article_outline"]
        outline2 = result2["article_outline"]

        assert outline1.topic == outline2.topic
        assert len(outline1.sections) == len(outline2.sections)

        for s1, s2 in zip(outline1.sections, outline2.sections):
            assert s1.title == s2.title
            assert s1.subsections == s2.subsections

    @pytest.mark.asyncio
    async def test_logging_decorator_applied(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify @log_node_execution decorator logs execution."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = PlanStructureNode()
        state = {
            "selected_topic": "Python",
            "workflow_id": "test-wf-008",
        }

        await node.execute(state)

        # Check for start and end logs
        log_messages = [record.message for record in caplog.records]
        start_logs = [
            m for m in log_messages if "Starting execution" in m and "plan_structure" in m
        ]
        end_logs = [m for m in log_messages if "Completed execution" in m and "plan_structure" in m]

        assert len(start_logs) > 0, "Should log execution start"
        assert len(end_logs) > 0, "Should log execution end"

    @pytest.mark.asyncio
    async def test_workflow_id_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify workflow_id is included in log messages."""
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = PlanStructureNode()
        workflow_id = "test-wf-009"
        state = {
            "selected_topic": "React Hooks",
            "workflow_id": workflow_id,
        }

        await node.execute(state)

        # Check that workflow_id appears in logs
        log_messages = [record.message for record in caplog.records]
        workflow_logs = [m for m in log_messages if workflow_id in m]

        assert len(workflow_logs) > 0, f"Should include workflow_id {workflow_id} in logs"

    @pytest.mark.asyncio
    async def test_outline_immutability(self) -> None:
        """Verify generated outline uses immutable structures."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "FastAPI Development",
            "workflow_id": "test-wf-010",
        }

        result = await node.execute(state)
        outline = result["article_outline"]

        # Outline should be frozen dataclass
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            outline.topic = "Changed"

        # Sections should be tuple (immutable)
        assert isinstance(outline.sections, tuple)

        # Each section should be frozen
        section = outline.sections[0]
        with pytest.raises(Exception):
            section.title = "Changed"

    @pytest.mark.asyncio
    async def test_multi_word_topic_handling(self) -> None:
        """Verify multi-word topics are handled correctly."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "Advanced Python Async Await Patterns",
            "workflow_id": "test-wf-011",
        }

        result = await node.execute(state)
        outline = result["article_outline"]

        # Should generate outline successfully
        assert outline.topic == "Advanced Python Async Await Patterns"
        assert len(outline.sections) > 0

        # First section should reference the topic
        assert "Advanced Python Async Await Patterns" in outline.sections[0].title

    @pytest.mark.asyncio
    async def test_special_characters_in_topic(self) -> None:
        """Verify topics with special characters are handled."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "C++ Modern Features",
            "workflow_id": "test-wf-012",
        }

        result = await node.execute(state)
        outline = result["article_outline"]

        # Should handle special characters gracefully
        assert outline.topic == "C++ Modern Features"
        assert len(outline.sections) > 0

    @pytest.mark.asyncio
    async def test_default_section_count(self) -> None:
        """Verify outline generates default number of sections."""
        node = PlanStructureNode()
        state = {
            "selected_topic": "Neural Networks",
            "workflow_id": "test-wf-013",
        }

        result = await node.execute(state)
        outline = result["article_outline"]

        # Default max_sections is 6
        assert len(outline.sections) == 6
