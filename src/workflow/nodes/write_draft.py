"""WriteDraftNode - Generates article draft from research.

Integrates WriterAgent into the LangGraph workflow.
"""

from src.agents.writer import write_section
from src.workflow.nodes import BaseNode, NodeRegistry, handle_node_errors, log_node_execution


@NodeRegistry.register("write_draft")
class WriteDraftNode(BaseNode):
    """Workflow node that generates article draft from outline and research."""

    @property
    def name(self) -> str:
        """Return node identifier."""
        return "write_draft"

    @handle_node_errors
    @log_node_execution
    async def execute(self, state: dict) -> dict:
        """Generate article draft by writing all sections.

        Args:
            state: Workflow state containing:
                - article_outline: The generated outline structure
                - research_data: List of ResearchDossier objects (one per section)

        Returns:
            State updates with:
                - draft_sections: List of WrittenSection objects
                - draft_content: Combined markdown content of all sections
                - current_step: Transition to "review"
        """
        # Extract outline and research data
        outline = state.get("article_outline")
        research_data = state.get("research_data")

        # Validate inputs
        if outline is None:
            raise ValueError("article_outline is required")

        if not hasattr(outline, "sections") or not outline.sections:
            raise ValueError("article_outline must have sections")

        if research_data is None:
            raise ValueError("research_data is required")

        if len(research_data) != len(outline.sections):
            raise ValueError(
                f"research_data length ({len(research_data)}) must match "
                f"sections length ({len(outline.sections)})"
            )

        # Write each section
        draft_sections = []
        for section in outline.sections:
            written = await write_section(outline, section, target_words=500)
            draft_sections.append(written)

        # Combine all sections into full article
        combined_parts = [f"# {outline.topic}\n"]

        for written_section in draft_sections:
            # Add section heading and content
            combined_parts.append(f"\n## {written_section.section_title}\n")
            combined_parts.append(f"{written_section.content}\n")

        draft_content = "\n".join(combined_parts).strip()

        # Return state updates
        return {
            "draft_sections": draft_sections,
            "draft_content": draft_content,
            "current_step": "review",
        }
