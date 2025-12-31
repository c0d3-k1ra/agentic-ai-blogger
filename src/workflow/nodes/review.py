"""ReviewNode - Reviews and optimizes article draft.

Integrates ReviewerAgent into the LangGraph workflow.
"""

from src.agents.reviewer import review_article
from src.workflow.nodes import BaseNode, NodeRegistry, handle_node_errors, log_node_execution


@NodeRegistry.register("review")
class ReviewNode(BaseNode):
    """Workflow node that reviews and optimizes article draft."""

    @property
    def name(self) -> str:
        """Return node identifier."""
        return "review"

    @handle_node_errors
    @log_node_execution
    async def execute(self, state: dict) -> dict:
        """Review article draft for quality, correctness, and SEO.

        Args:
            state: Workflow state containing:
                - draft_content: Combined markdown content of all sections
                - selected_topic: The article topic (for SEO context)

        Returns:
            State updates with:
                - reviewed_article: ReviewedArticle with polished content and metadata
                - current_step: Transition to "publish" or "revision" based on quality
        """
        # Extract draft content and topic
        draft_content = state.get("draft_content")
        topic = state.get("selected_topic")

        # Validate inputs
        if not draft_content or not draft_content.strip():
            raise ValueError("draft_content is required and cannot be empty")

        if not topic or not topic.strip():
            raise ValueError("selected_topic is required for review context")

        # Review the article
        reviewed = await review_article(topic, draft_content, min_tags=5, max_tags=7)

        # Return state updates
        # Note: In a real workflow, you might check quality metrics to decide
        # whether to go to "publish" or "revision". For now, we'll go to "publish".
        return {
            "reviewed_article": reviewed,
            "current_step": "publish",
        }
