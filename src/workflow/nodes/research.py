"""ResearchNode - Conducts comprehensive research for article sections.

Integrates ResearcherAgent into the LangGraph workflow.
"""

from src.agents.researcher import research_section
from src.workflow.nodes import BaseNode, NodeRegistry, handle_node_errors, log_node_execution


@NodeRegistry.register("research")
class ResearchNode(BaseNode):
    """Workflow node that conducts research for all article sections."""

    @property
    def name(self) -> str:
        """Return node identifier."""
        return "research"

    @handle_node_errors
    @log_node_execution
    async def execute(self, state: dict) -> dict:
        """Conduct research for all sections in article outline.

        Args:
            state: Workflow state containing:
                - article_outline: The generated outline structure
                - selected_topic: The article topic (for context)

        Returns:
            State updates with:
                - research_data: List of ResearchDossier objects (one per section)
                - current_step: Transition to "write_draft"
        """
        # Extract outline
        outline = state.get("article_outline")

        # Validate input
        if outline is None:
            raise ValueError("article_outline is required")

        if not hasattr(outline, "sections") or not outline.sections:
            raise ValueError("article_outline must have sections")

        # Research each section
        research_data = []
        for section in outline.sections:
            dossier = await research_section(outline, section)
            research_data.append(dossier)

        # Return state updates
        return {
            "research_data": research_data,
            "current_step": "write_draft",
        }
