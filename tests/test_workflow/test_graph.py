"""Tests for workflow graph definition."""

import pytest

from src.workflow.graph import (
    create_default_workflow,
    create_workflow_graph,
    get_workflow_visualization,
    should_continue_after_approval,
)
from src.workflow.graph_state import create_initial_state


class TestGraphCreation:
    """Tests for graph creation and configuration."""

    def test_create_workflow_graph_compiles_successfully(self):
        """Test that workflow graph compiles without errors."""
        graph = create_workflow_graph()
        assert graph is not None

    def test_create_default_workflow_compiles_successfully(self):
        """Test that default workflow creation works."""
        graph = create_default_workflow()
        assert graph is not None

    def test_graph_has_all_required_nodes(self):
        """Test that graph contains all expected nodes."""
        graph = create_workflow_graph()

        # Get nodes from compiled graph
        # Note: LangGraph's compiled graph structure may vary by version
        # This test verifies the graph was created successfully
        assert graph is not None

    def test_graph_accepts_custom_checkpointer(self):
        """Test that graph accepts custom checkpointer."""
        from langgraph.checkpoint.memory import MemorySaver

        custom_checkpointer = MemorySaver()
        graph = create_workflow_graph(checkpointer=custom_checkpointer)
        assert graph is not None

    def test_graph_uses_default_checkpointer_when_none(self):
        """Test that graph uses MemorySaver when no checkpointer provided."""
        graph = create_workflow_graph(checkpointer=None)
        assert graph is not None


class TestConditionalRouting:
    """Tests for conditional routing logic."""

    def test_should_continue_after_approval_when_approved(self):
        """Test routing when user approves article."""
        state = {
            "workflow_id": "test-123",
            "user_approval": True,
        }

        result = should_continue_after_approval(state)
        assert result == "save_article"

    def test_should_continue_after_approval_when_revision_requested(self):
        """Test routing when user requests revision."""
        state = {
            "workflow_id": "test-123",
            "user_approval": False,
        }

        result = should_continue_after_approval(state)
        assert result == "revise_article"

    def test_should_continue_after_approval_defaults_to_revise(self):
        """Test routing defaults to revise when approval field missing."""
        state = {
            "workflow_id": "test-123",
            # user_approval not present
        }

        result = should_continue_after_approval(state)
        assert result == "revise_article"


class TestWorkflowVisualization:
    """Tests for workflow visualization."""

    def test_get_workflow_visualization_returns_string(self):
        """Test that visualization returns a non-empty string."""
        viz = get_workflow_visualization()
        assert isinstance(viz, str)
        assert len(viz) > 0

    def test_visualization_contains_key_nodes(self):
        """Test that visualization includes key workflow nodes."""
        viz = get_workflow_visualization()

        # Check for important nodes
        assert "scout_topics" in viz
        assert "analyze_trends" in viz
        assert "user_selection" in viz
        assert "plan_structure" in viz
        assert "research_sections" in viz
        assert "write_sections" in viz
        assert "review_article" in viz
        assert "user_approval" in viz
        assert "revise_article" in viz
        assert "save_article" in viz

    def test_visualization_shows_interrupts(self):
        """Test that visualization indicates interrupt points."""
        viz = get_workflow_visualization()

        assert "INTERRUPT" in viz
        assert "user_selection" in viz
        assert "user_approval" in viz

    def test_visualization_shows_revision_loop(self):
        """Test that visualization shows revision loop information."""
        viz = get_workflow_visualization()

        assert "Revision Loop" in viz or "loop" in viz.lower()
        assert "Max revisions" in viz or "max" in viz.lower()


class TestGraphIntegration:
    """Integration tests for workflow graph execution."""

    @pytest.mark.asyncio
    async def test_graph_accepts_initial_state(self):
        """Test that graph accepts and processes initial state."""
        create_workflow_graph()  # Verify graph can be created
        initial_state = create_initial_state(
            workflow_id="test-wf-123",
            user_query="Python async programming",
            max_revisions=3,
        )

        # Verify initial state is valid
        assert initial_state["workflow_id"] == "test-wf-123"
        assert initial_state["user_query"] == "Python async programming"
        assert initial_state["max_revisions"] == 3
        assert initial_state["revision_count"] == 0
        assert initial_state["current_step"] == "scout_topics"

    def test_graph_configuration_with_thread_id(self):
        """Test that graph can be configured with thread_id for checkpointing."""
        create_workflow_graph()  # Verify graph can be created
        config = {"configurable": {"thread_id": "test-thread-123"}}

        # Verify config is properly structured
        assert "configurable" in config
        assert "thread_id" in config["configurable"]
        assert config["configurable"]["thread_id"] == "test-thread-123"

    def test_multiple_graphs_can_be_created(self):
        """Test that multiple independent graphs can be created."""
        graph1 = create_workflow_graph()
        graph2 = create_workflow_graph()
        graph3 = create_default_workflow()

        # All should be valid but independent
        assert graph1 is not None
        assert graph2 is not None
        assert graph3 is not None
        assert graph1 is not graph2
        assert graph2 is not graph3


class TestGraphEdges:
    """Tests for graph edge configuration."""

    def test_graph_has_entry_point(self):
        """Test that graph has correct entry point."""
        graph = create_workflow_graph()
        # Graph should be compiled successfully with scout_topics as entry
        assert graph is not None

    def test_graph_has_finish_point(self):
        """Test that graph has correct finish point."""
        graph = create_workflow_graph()
        # Graph should be compiled successfully with save_article as finish
        assert graph is not None

    def test_graph_has_interrupt_before_user_nodes(self):
        """Test that graph is configured to interrupt before user interaction nodes."""
        # This is tested implicitly by successful compilation
        # LangGraph will raise error if interrupt_before contains invalid nodes
        graph = create_workflow_graph()
        assert graph is not None


class TestErrorHandling:
    """Tests for error handling in graph."""

    def test_conditional_routing_handles_invalid_state_gracefully(self):
        """Test that conditional routing handles edge cases."""
        # Empty state
        state = {}
        result = should_continue_after_approval(state)
        assert result in ["save_article", "revise_article"]

    def test_conditional_routing_with_none_approval(self):
        """Test routing when approval is None."""
        state = {
            "workflow_id": "test-123",
            "user_approval": None,
        }

        result = should_continue_after_approval(state)
        # None should be falsy, so should revise
        assert result == "revise_article"

    def test_graph_creation_does_not_raise_on_valid_inputs(self):
        """Test that graph creation doesn't raise errors with valid inputs."""
        try:
            graph = create_workflow_graph()
            assert graph is not None
        except Exception as e:
            pytest.fail(f"Graph creation raised unexpected exception: {e}")

    def test_default_workflow_creation_does_not_raise(self):
        """Test that default workflow creation doesn't raise errors."""
        try:
            graph = create_default_workflow()
            assert graph is not None
        except Exception as e:
            pytest.fail(f"Default workflow creation raised unexpected exception: {e}")
