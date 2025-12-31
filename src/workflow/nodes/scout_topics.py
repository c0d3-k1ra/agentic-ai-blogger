"""Scout Topics Node - Discover trending topics from seed query.

This node integrates the TopicScoutAgent into the LangGraph workflow,
transforming user queries into candidate article topics.

Node Behavior:
- Input: user_query from state
- Process: Generate topic variations using template expansion
- Output: scouted_topics list, updated current_step
- Next Step: analyze_trends

Error Handling:
- Empty/invalid queries caught by agent validation
- Errors converted to state["errors"] via @handle_node_errors
- Automatic retries on transient failures via @retry_on_error
"""

from src.agents.topic_scout import generate_topics
from src.workflow.graph_state import ArticleWorkflowState
from src.workflow.nodes import (
    BaseNode,
    NodeRegistry,
    handle_node_errors,
    log_node_execution,
    retry_on_error,
)


@NodeRegistry.register("scout_topics")
class ScoutTopicsNode(BaseNode):
    """LangGraph node for discovering article topics from user queries.

    Wraps the TopicScoutAgent's generate_topics function in a workflow node
    with proper error handling, logging, and retry logic.

    The node is stateless and thread-safe - all state is passed via the
    ArticleWorkflowState parameter.

    Example:
        >>> node = ScoutTopicsNode()
        >>> state = {"user_query": "Python Async", "workflow_id": "test-123"}
        >>> result = await node.execute(state)
        >>> result["scouted_topics"]
        ['Introduction to Python Async', 'Getting Started with Python Async', ...]
        >>> result["current_step"]
        'analyze_trends'
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
            The string "scout_topics"
        """
        return "scout_topics"

    @handle_node_errors
    @log_node_execution
    @retry_on_error(max_retries=2, backoff_factor=2.0, exceptions=(ValueError,))
    async def execute(self, state: ArticleWorkflowState) -> dict:
        """Scout for trending topics based on user query.

        Extracts the user_query from state and generates topic variations
        using template-based expansion. The generated topics are deterministic
        and ordered by generation sequence.

        Args:
            state: Current workflow state containing:
                - user_query: The seed topic to expand (required)
                - workflow_id: Unique workflow identifier (for logging)

        Returns:
            State updates dict containing:
                - scouted_topics: List of 30 generated topic strings
                - current_step: "analyze_trends" (next workflow step)

        Raises:
            ValueError: If user_query is missing or invalid (caught by decorator)

        Side Effects:
            - Logs execution start/end via @log_node_execution
            - May retry up to 2 times on ValueError via @retry_on_error
            - Errors converted to state["errors"] via @handle_node_errors

        Example State Flow:
            Input:
                {
                    "user_query": "Python Async",
                    "workflow_id": "wf-123",
                    "current_step": "scout_topics"
                }

            Output:
                {
                    "scouted_topics": ["Introduction to Python Async", ...],
                    "current_step": "analyze_trends"
                }

        Design Notes:
            - Pure function call to generate_topics (no side effects)
            - No database access or external APIs
            - Deterministic output (same query → same topics)
            - Thread-safe (no shared state)
        """
        # Extract user query from state
        user_query = state.get("user_query", "")

        # Generate topics using TopicScoutAgent
        # This is a pure function call with no side effects
        topics = generate_topics(seed_topic=user_query, max_topics=30)

        # Return state updates
        return {
            "scouted_topics": topics,
            "current_step": "analyze_trends",
        }
