"""Analyze Trends Node - Rank and select best topic from scouted topics.

This node integrates the TrendAnalyzerAgent into the LangGraph workflow,
scoring and ranking topics to select the most valuable one for article generation.

Node Behavior:
- Input: scouted_topics from state
- Process: Score topics using heuristic analysis, select best
- Output: analyzed_trends (all scored topics), selected_topic
- Next Step: plan_structure

Error Handling:
- Empty topic list handled gracefully (returns error state)
- Errors converted to state["errors"] via @handle_node_errors
- Automatic retries on transient failures via @retry_on_error
"""

from src.agents.trend_analyzer import analyze_trends
from src.workflow.graph_state import ArticleWorkflowState
from src.workflow.nodes import (
    BaseNode,
    NodeRegistry,
    handle_node_errors,
    log_node_execution,
    retry_on_error,
)


@NodeRegistry.register("analyze_trends")
class AnalyzeTrendsNode(BaseNode):
    """LangGraph node for analyzing and ranking scouted topics.

    Wraps the TrendAnalyzerAgent's analyze_trends function in a workflow node
    with proper error handling, logging, and retry logic.

    The node evaluates topic quality using deterministic heuristics:
    - Length optimization (40-80 chars ideal)
    - Keyword richness (non-stopword ratio)
    - Specificity bonuses (concrete terms)
    - Generic penalties (beginner phrases)

    The node is stateless and thread-safe - all state is passed via the
    ArticleWorkflowState parameter.

    Example:
        >>> node = AnalyzeTrendsNode()
        >>> state = {
        ...     "scouted_topics": ["Python", "Advanced Python Performance"],
        ...     "workflow_id": "test-123"
        ... }
        >>> result = await node.execute(state)
        >>> result["selected_topic"]
        'Advanced Python Performance'
        >>> result["current_step"]
        'plan_structure'
    """

    @property
    def name(self) -> str:
        """Return the node's unique identifier.

        This name is used for:
        - NodeRegistry registration
        - Logging and monitoring
        - Graph edge definitions
        - Error reporting

        Returns:
            The string "analyze_trends"
        """
        return "analyze_trends"

    @handle_node_errors
    @log_node_execution
    @retry_on_error(max_retries=2, backoff_factor=2.0, exceptions=(ValueError,))
    async def execute(self, state: ArticleWorkflowState) -> dict:
        """Analyze scouted topics and select the best one.

        Scores all topics using deterministic heuristics and selects the
        highest-scoring topic for article generation. Returns both the
        full analysis and the selected topic.

        Args:
            state: Current workflow state containing:
                - scouted_topics: List of topic strings to analyze (required)
                - workflow_id: Unique workflow identifier (for logging)

        Returns:
            State updates dict containing either:

            Success case:
                - analyzed_trends: List of ScoredTopic objects (all topics ranked)
                - selected_topic: The highest-scoring topic string
                - current_step: "plan_structure" (next workflow step)

            Error case (empty topic list):
                - errors: ["No topics to analyze"]
                - current_step: "failed"

        Raises:
            ValueError: If topics list is invalid (caught by decorator)

        Side Effects:
            - Logs execution start/end via @log_node_execution
            - May retry up to 2 times on ValueError via @retry_on_error
            - Errors converted to state["errors"] via @handle_node_errors

        Example State Flow:
            Input:
                {
                    "scouted_topics": [
                        "Introduction to Python",
                        "Advanced Python Performance Optimization"
                    ],
                    "workflow_id": "wf-123",
                    "current_step": "analyze_trends"
                }

            Output:
                {
                    "analyzed_trends": [
                        ScoredTopic(topic="Advanced Python Performance...", score=0.95),
                        ScoredTopic(topic="Introduction to Python", score=0.25)
                    ],
                    "selected_topic": "Advanced Python Performance Optimization",
                    "current_step": "plan_structure"
                }

        Design Notes:
            - Pure function call to analyze_trends (no side effects)
            - No database access or external APIs
            - No LLM calls (deterministic heuristics only)
            - Thread-safe (no shared state)
            - Graceful degradation on empty input
        """
        # Extract scouted topics from state
        scouted_topics = state.get("scouted_topics", [])

        # Validate input: ensure we have topics to analyze
        if not scouted_topics:
            return {
                "errors": ["No topics to analyze"],
                "current_step": "failed",
            }

        # Analyze topics using TrendAnalyzerAgent
        # This is a pure function call with no side effects
        # Returns list of ScoredTopic objects sorted by descending score
        analyzed = analyze_trends(topics=scouted_topics, max_topics=len(scouted_topics))

        # Select the best topic (first in sorted list)
        # analyze_trends guarantees at least one result if input is non-empty
        selected = analyzed[0].topic

        # Return state updates
        return {
            "analyzed_trends": analyzed,
            "selected_topic": selected,
            "current_step": "plan_structure",
        }
