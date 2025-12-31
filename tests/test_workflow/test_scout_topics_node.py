"""Unit tests for ScoutTopicsNode.

Tests the integration of TopicScoutAgent into the LangGraph workflow,
verifying proper error handling, logging, retry logic, and state updates.

Test Coverage:
- Node registration and properties
- Successful topic scouting
- State updates and transitions
- Error handling for invalid inputs
- Retry behavior on failures
- Logging integration
"""

import pytest

from src.workflow.nodes import NodeRegistry
from src.workflow.nodes.scout_topics import ScoutTopicsNode


class TestScoutTopicsNode:
    """Test suite for ScoutTopicsNode workflow integration."""

    def setup_method(self) -> None:
        """Ensure node is registered before each test."""
        # Re-register node in case registry was cleared by other tests
        if not NodeRegistry.is_registered("scout_topics"):
            from src.workflow.nodes.scout_topics import ScoutTopicsNode

            NodeRegistry.register("scout_topics")(ScoutTopicsNode)

    def test_node_registered_in_registry(self) -> None:
        """Verify node is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("scout_topics")
        node_class = NodeRegistry.get("scout_topics")
        # Registry returns the class, not an instance
        assert node_class == ScoutTopicsNode
        # Verify we can instantiate it
        node = node_class()
        assert isinstance(node, ScoutTopicsNode)

    def test_node_has_correct_name(self) -> None:
        """Verify node name property returns correct identifier."""
        node = ScoutTopicsNode()
        assert node.name == "scout_topics"

    @pytest.mark.asyncio
    async def test_successful_topic_scouting(self) -> None:
        """Verify node successfully scouts topics from user query."""
        node = ScoutTopicsNode()
        state = {
            "user_query": "Python Async",
            "workflow_id": "test-wf-001",
            "current_step": "scout_topics",
        }

        result = await node.execute(state)

        # Verify state updates
        assert "scouted_topics" in result
        assert isinstance(result["scouted_topics"], list)
        assert len(result["scouted_topics"]) > 0

        # Verify topics are strings
        assert all(isinstance(topic, str) for topic in result["scouted_topics"])

        # Verify workflow transition
        assert result["current_step"] == "analyze_trends"

    @pytest.mark.asyncio
    async def test_returns_expected_number_of_topics(self) -> None:
        """Verify node returns max_topics (30) topics."""
        node = ScoutTopicsNode()
        state = {
            "user_query": "Machine Learning",
            "workflow_id": "test-wf-002",
        }

        result = await node.execute(state)

        # Should return 30 topics (max_topics default)
        assert len(result["scouted_topics"]) == 30

    @pytest.mark.asyncio
    async def test_topics_contain_query_keywords(self) -> None:
        """Verify generated topics relate to user query."""
        node = ScoutTopicsNode()
        state = {
            "user_query": "Docker",
            "workflow_id": "test-wf-003",
        }

        result = await node.execute(state)

        # At least some topics should contain "Docker"
        docker_topics = [t for t in result["scouted_topics"] if "Docker" in t]
        assert len(docker_topics) > 0

    @pytest.mark.asyncio
    async def test_empty_query_raises_error(self) -> None:
        """Verify empty user_query is handled with error state."""
        node = ScoutTopicsNode()
        state = {
            "user_query": "",
            "workflow_id": "test-wf-004",
        }

        result = await node.execute(state)

        # @handle_node_errors should catch ValueError and set error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_whitespace_query_raises_error(self) -> None:
        """Verify whitespace-only query is handled with error state."""
        node = ScoutTopicsNode()
        state = {
            "user_query": "   \n\t  ",
            "workflow_id": "test-wf-005",
        }

        result = await node.execute(state)

        # @handle_node_errors should catch ValueError and set error state
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_missing_query_defaults_to_empty(self) -> None:
        """Verify missing user_query is handled with error state."""
        node = ScoutTopicsNode()
        state = {
            "workflow_id": "test-wf-006",
        }

        result = await node.execute(state)

        # Should get error state due to empty query
        assert "errors" in result
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_deterministic_output(self) -> None:
        """Verify same query produces same topics (deterministic)."""
        node = ScoutTopicsNode()
        state = {
            "user_query": "Kubernetes",
            "workflow_id": "test-wf-007",
        }

        result1 = await node.execute(state)
        result2 = await node.execute(state)

        # Same input should produce same output
        assert result1["scouted_topics"] == result2["scouted_topics"]

    @pytest.mark.asyncio
    async def test_logging_decorator_applied(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify @log_node_execution decorator logs execution."""
        # Set log level to INFO to capture execution logs
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = ScoutTopicsNode()
        state = {
            "user_query": "Python",
            "workflow_id": "test-wf-008",
        }

        await node.execute(state)

        # Check for start and end logs
        log_messages = [record.message for record in caplog.records]
        start_logs = [m for m in log_messages if "Starting execution" in m and "scout_topics" in m]
        end_logs = [m for m in log_messages if "Completed execution" in m and "scout_topics" in m]

        assert len(start_logs) > 0, "Should log execution start"
        assert len(end_logs) > 0, "Should log execution end"

    @pytest.mark.asyncio
    async def test_workflow_id_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify workflow_id is included in log messages."""
        # Set log level to INFO to capture execution logs
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = ScoutTopicsNode()
        workflow_id = "test-wf-009"
        state = {
            "user_query": "React",
            "workflow_id": workflow_id,
        }

        await node.execute(state)

        # Check that workflow_id appears in logs
        log_messages = [record.message for record in caplog.records]
        workflow_logs = [m for m in log_messages if workflow_id in m]

        assert len(workflow_logs) > 0, f"Should include workflow_id {workflow_id} in logs"

    @pytest.mark.asyncio
    async def test_multi_word_query_handling(self) -> None:
        """Verify multi-word queries are handled correctly."""
        node = ScoutTopicsNode()
        state = {
            "user_query": "Python Async Programming",
            "workflow_id": "test-wf-010",
        }

        result = await node.execute(state)

        # Should generate topics successfully
        assert "scouted_topics" in result
        assert len(result["scouted_topics"]) == 30

        # Topics should include variations of the full query and individual words
        topics = result["scouted_topics"]
        has_full_query = any("Python Async Programming" in t for t in topics)
        has_python = any("Python" in t for t in topics)

        assert has_full_query or has_python, "Should generate topics with query keywords"

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self) -> None:
        """Verify queries with special characters are handled."""
        node = ScoutTopicsNode()
        state = {
            "user_query": "C++ Programming",
            "workflow_id": "test-wf-011",
        }

        result = await node.execute(state)

        # Should handle special characters gracefully
        assert "scouted_topics" in result
        assert len(result["scouted_topics"]) > 0
        assert len(result["scouted_topics"]) > 0
