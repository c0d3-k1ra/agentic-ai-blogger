"""RevisionNode - Applies user feedback to revise article.

Integrates RevisionAgent into the LangGraph workflow.
"""

from src.agents.revision import revise_article
from src.workflow.nodes import BaseNode, NodeRegistry, handle_node_errors, log_node_execution


@NodeRegistry.register("revision")
class RevisionNode(BaseNode):
    """Workflow node that applies user feedback to revise article."""

    @property
    def name(self) -> str:
        """Return node identifier."""
        return "revision"

    @handle_node_errors
    @log_node_execution
    async def execute(self, state: dict) -> dict:
        """Apply user feedback to revise article content.

        Args:
            state: Workflow state containing:
                - draft_content: Current article content to revise
                - user_feedback: User feedback describing desired changes
                - selected_topic: The article topic (for context)
                - revision_number: Current revision cycle (default: 0)

        Returns:
            State updates with:
                - revised_article: RevisedArticle with updated content
                - draft_content: Updated with revised content (for next iteration)
                - revision_number: Incremented revision counter
                - current_step: Transition back to "review"
        """
        # Extract inputs
        draft_content = state.get("draft_content")
        user_feedback = state.get("user_feedback")
        topic = state.get("selected_topic")
        current_revision = state.get("revision_number", 0)

        # Validate inputs
        if not draft_content or not draft_content.strip():
            raise ValueError("draft_content is required and cannot be empty")

        if not user_feedback or not user_feedback.strip():
            raise ValueError("user_feedback is required and cannot be empty")

        if not topic or not topic.strip():
            raise ValueError("selected_topic is required for revision context")

        # Apply revision
        new_revision_number = current_revision + 1
        revised = await revise_article(
            draft_content, user_feedback, topic=topic, revision_number=new_revision_number
        )

        # Return state updates
        return {
            "revised_article": revised,
            "draft_content": revised.content,  # Update draft for next iteration
            "revision_number": new_revision_number,
            "current_step": "review",  # Go back to review after revision
        }
