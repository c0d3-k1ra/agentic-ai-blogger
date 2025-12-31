"""LangGraph workflow graph definition.

This module defines the main StateGraph that orchestrates the article generation
workflow by connecting all nodes together with proper edges and conditional routing.

The workflow follows this flow:
1. scout_topics → analyze_trends → user_selection
2. user_selection → plan_structure → research_sections
3. research_sections → write_sections → review_article
4. review_article → user_approval
5. user_approval → (approve) save_article OR (revise) revise_article
6. revise_article → review_article (loop, max 3 times)
"""

import logging
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from src.workflow.graph_state import ArticleWorkflowState
from src.workflow.nodes.analyze_trends import AnalyzeTrendsNode
from src.workflow.nodes.plan_structure import PlanStructureNode
from src.workflow.nodes.publish import PublishNode
from src.workflow.nodes.research import ResearchNode
from src.workflow.nodes.review import ReviewNode
from src.workflow.nodes.revision import RevisionNode
from src.workflow.nodes.scout_topics import ScoutTopicsNode
from src.workflow.nodes.user_interaction import UserApprovalNode, UserSelectionNode
from src.workflow.nodes.write_draft import WriteDraftNode

logger = logging.getLogger(__name__)


def should_continue_after_approval(
    state: ArticleWorkflowState,
) -> Literal["save_article", "revise_article"]:
    """Conditional routing after user approval.

    Routes to either publish or revision based on user's decision.

    Args:
        state: Current workflow state with user_approval

    Returns:
        "save_article" if approved, "revise_article" if revision requested
    """
    user_approval = state.get("user_approval", False)

    if user_approval:
        logger.info(f"[{state.get('workflow_id')}] User approved → routing to save_article")
        return "save_article"
    else:
        logger.info(
            f"[{state.get('workflow_id')}] User requested revision → routing to revise_article"
        )
        return "revise_article"


def create_workflow_graph(checkpointer=None) -> StateGraph:
    """Create and configure the article generation workflow graph.

    The graph connects all workflow nodes and defines the execution flow:
    - Linear flow from topic scouting to article publication
    - User interrupts for topic selection and article approval
    - Conditional routing based on user decisions
    - Revision loop with max iteration limit

    Args:
        checkpointer: Optional checkpoint saver for persistence and interrupts.
            If None, uses MemorySaver() for in-memory checkpointing.
            For production, consider SqliteSaver or PostgresSaver.

    Returns:
        Compiled StateGraph ready for execution

    Example:
        >>> from langgraph.checkpoint.memory import MemorySaver
        >>> graph = create_workflow_graph(checkpointer=MemorySaver())
        >>> initial_state = create_initial_state("wf-123", "Python async")
        >>> config = {"configurable": {"thread_id": "thread-1"}}
        >>> # Run until first interrupt
        >>> result = graph.invoke(initial_state, config)
        >>> # Resume with user input
        >>> result = graph.invoke({"selected_topic": "..."}, config)
    """
    # Initialize graph with state schema
    workflow = StateGraph(ArticleWorkflowState)

    # Initialize all node instances
    scout_node = ScoutTopicsNode()
    analyze_node = AnalyzeTrendsNode()
    user_select_node = UserSelectionNode()
    plan_node = PlanStructureNode()
    research_node = ResearchNode()
    write_node = WriteDraftNode()
    review_node = ReviewNode()
    user_approval_node = UserApprovalNode()
    revision_node = RevisionNode()
    publish_node = PublishNode()

    # Add nodes to graph
    workflow.add_node("scout_topics", scout_node.execute)
    workflow.add_node("analyze_trends", analyze_node.execute)
    workflow.add_node("user_selection", user_select_node.execute)
    workflow.add_node("plan_structure", plan_node.execute)
    workflow.add_node("research_sections", research_node.execute)
    workflow.add_node("write_sections", write_node.execute)
    workflow.add_node("review_article", review_node.execute)
    workflow.add_node("user_approval", user_approval_node.execute)
    workflow.add_node("revise_article", revision_node.execute)
    workflow.add_node("save_article", publish_node.execute)

    # Define workflow edges (linear flow)
    workflow.add_edge("scout_topics", "analyze_trends")
    workflow.add_edge("analyze_trends", "user_selection")
    workflow.add_edge("user_selection", "plan_structure")
    workflow.add_edge("plan_structure", "research_sections")
    workflow.add_edge("research_sections", "write_sections")
    workflow.add_edge("write_sections", "review_article")
    workflow.add_edge("review_article", "user_approval")

    # Conditional routing after user approval
    workflow.add_conditional_edges(
        "user_approval",
        should_continue_after_approval,
        {
            "save_article": "save_article",
            "revise_article": "revise_article",
        },
    )

    # Revision loop - goes back to review
    workflow.add_edge("revise_article", "review_article")

    # Set entry and finish points
    workflow.set_entry_point("scout_topics")
    workflow.set_finish_point("save_article")

    # Use provided checkpointer or default to MemorySaver
    if checkpointer is None:
        checkpointer = MemorySaver()
        logger.info("Using MemorySaver for in-memory checkpointing")

    # Compile graph with checkpointer for interrupt support
    compiled_graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["user_selection", "user_approval"],  # Pause before these nodes
    )

    logger.info("Workflow graph compiled successfully with interrupts enabled")
    return compiled_graph


def get_workflow_visualization() -> str:
    """Get a text-based visualization of the workflow graph.

    Returns:
        String representation of the workflow graph structure

    Example:
        >>> print(get_workflow_visualization())
        Article Generation Workflow:
        ...
    """
    visualization = """
    Article Generation Workflow:
    ============================

    START
      ↓
    scout_topics
      ↓
    analyze_trends
      ↓
    user_selection [INTERRUPT]
      ↓
    plan_structure
      ↓
    research_sections
      ↓
    write_sections
      ↓
    review_article
      ↓
    user_approval [INTERRUPT]
      ↓
      ├─[approve]→ save_article → END
      │
      └─[revise]→ revise_article
                      ↓
                 review_article (loop back)

    Interrupts:
    - user_selection: Manual topic selection from analyzed trends
    - user_approval: Approve article or request revision with feedback

    Revision Loop:
    - Max revisions: 3 (configured in initial state)
    - After max: Auto-approves and proceeds to publish
    """
    return visualization


# Convenience function for quick setup
def create_default_workflow() -> StateGraph:
    """Create workflow with default configuration (MemorySaver).

    Convenience function for quick setup without configuration.

    Returns:
        Compiled workflow graph with in-memory checkpointing

    Example:
        >>> workflow = create_default_workflow()
        >>> config = {"configurable": {"thread_id": "my-thread"}}
        >>> result = workflow.invoke(initial_state, config)
    """
    return create_workflow_graph()


__all__ = [
    "create_workflow_graph",
    "create_default_workflow",
    "get_workflow_visualization",
    "should_continue_after_approval",
]
