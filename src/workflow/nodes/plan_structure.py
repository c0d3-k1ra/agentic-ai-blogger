"""PlanStructureNode - Generates article outline from selected topic.

Integrates StructurePlannerAgent into the LangGraph workflow.
"""

from src.agents.structure_planner import generate_outline
from src.workflow.nodes import BaseNode, NodeRegistry, handle_node_errors, log_node_execution


@NodeRegistry.register("plan_structure")
class PlanStructureNode(BaseNode):
    """Workflow node that generates article outline from selected topic."""

    @property
    def name(self) -> str:
        """Return node identifier."""
        return "plan_structure"

    @handle_node_errors
    @log_node_execution
    async def execute(self, state: dict) -> dict:
        """Generate article outline from selected topic.

        Args:
            state: Workflow state containing:
                - selected_topic: The chosen article topic

        Returns:
            State updates with:
                - article_outline: Generated outline structure
                - current_step: Transition to "research"
        """
        # Extract selected topic
        selected_topic = state.get("selected_topic", "").strip()

        # Validate input
        if not selected_topic:
            raise ValueError("selected_topic is required and cannot be empty")

        # Generate outline (deterministic, no LLM)
        outline = generate_outline(selected_topic)

        # Return state updates
        return {
            "article_outline": outline,
            "current_step": "research",
        }
