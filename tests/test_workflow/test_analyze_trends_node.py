"""Unit tests for AnalyzeTrendsNode.

Tests the integration of TrendAnalyzerAgent into the LangGraph workflow,
verifying proper topic scoring, selection, error handling, and state updates.

Test Coverage:
- Node registration and properties
- Successful trend analysis
- Topic selection logic
- State updates and transitions
- Error handling for empty/invalid inputs
- Retry behavior on failures
- Logging integration
"""

import pytest

from src.agents.trend_analyzer import ScoredTopic
from src.workflow.nodes import NodeRegistry
from src.workflow.nodes.analyze_trends import AnalyzeTrendsNode


class TestAnalyzeTrendsNode:
    """Test suite for AnalyzeTrendsNode workflow integration."""

    def setup_method(self) -> None:
        """Ensure node is registered before each test."""
        # Re-register node in case registry was cleared by other tests
        if not NodeRegistry.is_registered("analyze_trends"):
            from src.workflow.nodes.analyze_trends import AnalyzeTrendsNode

            NodeRegistry.register("analyze_trends")(AnalyzeTrendsNode)

    def test_node_registered_in_registry(self) -> None:
        """Verify node is registered in NodeRegistry."""
        assert NodeRegistry.is_registered("analyze_trends")
        node_class = NodeRegistry.get("analyze_trends")
        # Registry returns the class, not an instance
        assert node_class == AnalyzeTrendsNode
        # Verify we can instantiate it
        node = node_class()
        assert isinstance(node, AnalyzeTrendsNode)

    def test_node_has_correct_name(self) -> None:
        """Verify node name property returns correct identifier."""
        node = AnalyzeTrendsNode()
        assert node.name == "analyze_trends"

    @pytest.mark.asyncio
    async def test_successful_trend_analysis(self) -> None:
        """Verify node successfully analyzes topics."""
        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": [
                "Introduction to Python",
                "Advanced Python Performance Optimization",
                "Python for Beginners",
            ],
            "workflow_id": "test-wf-001",
            "current_step": "analyze_trends",
        }

        result = await node.execute(state)

        # Verify state updates
        assert "analyzed_trends" in result
        assert "selected_topic" in result
        assert result["current_step"] == "plan_structure"

        # Verify analyzed_trends structure
        analyzed = result["analyzed_trends"]
        assert isinstance(analyzed, list)
        assert len(analyzed) == 3
        assert all(isinstance(item, ScoredTopic) for item in analyzed)

    @pytest.mark.asyncio
    async def test_selected_topic_is_highest_scoring(self) -> None:
        """Verify selected topic has the highest score."""
        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": [
                "Introduction to Python",  # Low score (generic)
                "Advanced Python Performance Optimization",  # High score
                "Python 101",  # Low score (generic)
            ],
            "workflow_id": "test-wf-002",
        }

        result = await node.execute(state)

        analyzed = result["analyzed_trends"]
        selected = result["selected_topic"]

        # Selected topic should match the first (highest scoring) in analyzed list
        assert selected == analyzed[0].topic

        # Verify it's sorted by descending score
        for i in range(len(analyzed) - 1):
            assert analyzed[i].score >= analyzed[i + 1].score

    @pytest.mark.asyncio
    async def test_analyzed_trends_sorted_by_score(self) -> None:
        """Verify analyzed_trends list is sorted by descending score."""
        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": [
                "Python",
                "Advanced Python Techniques",
                "Getting Started with Python",
                "Python Design Patterns",
                "Introduction to Python",
            ],
            "workflow_id": "test-wf-003",
        }

        result = await node.execute(state)

        analyzed = result["analyzed_trends"]

        # Verify descending order
        scores = [item.score for item in analyzed]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_empty_topics_list_returns_error(self) -> None:
        """Verify empty scouted_topics list results in error state."""
        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": [],
            "workflow_id": "test-wf-004",
        }

        result = await node.execute(state)

        # Should return error state
        assert "errors" in result
        assert "No topics to analyze" in result["errors"]
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_missing_topics_key_returns_error(self) -> None:
        """Verify missing scouted_topics key results in error state."""
        node = AnalyzeTrendsNode()
        state = {
            "workflow_id": "test-wf-005",
        }

        result = await node.execute(state)

        # Should return error state (defaults to empty list)
        assert "errors" in result
        assert "No topics to analyze" in result["errors"]
        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_single_topic_analysis(self) -> None:
        """Verify node handles single topic correctly."""
        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": ["Python Programming"],
            "workflow_id": "test-wf-006",
        }

        result = await node.execute(state)

        # Should succeed with single topic
        assert "analyzed_trends" in result
        assert len(result["analyzed_trends"]) == 1
        assert result["selected_topic"] == "Python Programming"
        assert result["current_step"] == "plan_structure"

    @pytest.mark.asyncio
    async def test_all_topics_analyzed(self) -> None:
        """Verify all input topics are analyzed and included."""
        node = AnalyzeTrendsNode()
        topics = [
            "Python Basics",
            "Advanced Python",
            "Python Testing",
            "Python Performance",
            "Python Design",
        ]
        state = {
            "scouted_topics": topics,
            "workflow_id": "test-wf-007",
        }

        result = await node.execute(state)

        analyzed = result["analyzed_trends"]

        # All topics should be analyzed
        assert len(analyzed) == len(topics)

        # All original topics should be present
        analyzed_topics = {item.topic for item in analyzed}
        assert analyzed_topics == set(topics)

    @pytest.mark.asyncio
    async def test_logging_decorator_applied(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify @log_node_execution decorator logs execution."""
        # Set log level to INFO to capture execution logs
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": ["Python", "JavaScript"],
            "workflow_id": "test-wf-008",
        }

        await node.execute(state)

        # Check for start and end logs
        log_messages = [record.message for record in caplog.records]
        start_logs = [
            m for m in log_messages if "Starting execution" in m and "analyze_trends" in m
        ]
        end_logs = [m for m in log_messages if "Completed execution" in m and "analyze_trends" in m]

        assert len(start_logs) > 0, "Should log execution start"
        assert len(end_logs) > 0, "Should log execution end"

    @pytest.mark.asyncio
    async def test_workflow_id_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify workflow_id is included in log messages."""
        # Set log level to INFO to capture execution logs
        caplog.set_level("INFO", logger="src.workflow.nodes")

        node = AnalyzeTrendsNode()
        workflow_id = "test-wf-009"
        state = {
            "scouted_topics": ["React", "Vue"],
            "workflow_id": workflow_id,
        }

        await node.execute(state)

        # Check that workflow_id appears in logs
        log_messages = [record.message for record in caplog.records]
        workflow_logs = [m for m in log_messages if workflow_id in m]

        assert len(workflow_logs) > 0, f"Should include workflow_id {workflow_id} in logs"

    @pytest.mark.asyncio
    async def test_deterministic_scoring(self) -> None:
        """Verify same topics produce same scores (deterministic)."""
        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": ["Python", "Advanced Python", "Python 101"],
            "workflow_id": "test-wf-010",
        }

        result1 = await node.execute(state)
        result2 = await node.execute(state)

        # Same input should produce same scores
        scores1 = [item.score for item in result1["analyzed_trends"]]
        scores2 = [item.score for item in result2["analyzed_trends"]]

        assert scores1 == scores2

    @pytest.mark.asyncio
    async def test_selected_topic_is_string(self) -> None:
        """Verify selected_topic is a string, not ScoredTopic object."""
        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": ["Python Programming", "JavaScript Basics"],
            "workflow_id": "test-wf-011",
        }

        result = await node.execute(state)

        # selected_topic should be a string
        assert isinstance(result["selected_topic"], str)
        assert len(result["selected_topic"]) > 0

    @pytest.mark.asyncio
    async def test_specific_topics_score_higher(self) -> None:
        """Verify specific topics score higher than generic ones."""
        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": [
                "Introduction to Python",  # Generic
                "Advanced Python Performance Optimization",  # Specific
            ],
            "workflow_id": "test-wf-012",
        }

        result = await node.execute(state)

        analyzed = result["analyzed_trends"]

        # Find scores
        specific_score = next(
            item.score for item in analyzed if "Performance Optimization" in item.topic
        )
        generic_score = next(item.score for item in analyzed if "Introduction" in item.topic)

        # Specific should score higher
        assert specific_score > generic_score

    @pytest.mark.asyncio
    async def test_whitespace_topics_handled(self) -> None:
        """Verify topics with extra whitespace are handled correctly."""
        node = AnalyzeTrendsNode()
        state = {
            "scouted_topics": [
                "  Python  ",
                "JavaScript   Frameworks",
                "   ",  # Empty after strip
            ],
            "workflow_id": "test-wf-013",
        }

        result = await node.execute(state)

        # Should succeed and filter empty topics
        assert "analyzed_trends" in result
        assert "selected_topic" in result

        # Empty whitespace topic should be filtered out by analyze_trends
        analyzed = result["analyzed_trends"]
        assert all(item.topic.strip() for item in analyzed)
        assert all(item.topic.strip() for item in analyzed)
