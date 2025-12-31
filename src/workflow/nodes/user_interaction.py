"""User interaction nodes for workflow interrupts.

This module provides nodes that pause workflow execution to collect user input:
- UserSelectionNode: Pause for manual topic selection
- UserApprovalNode: Pause for article approval/revision decision

These nodes use LangGraph's interrupt mechanism to pause execution and resume
after user provides input via CLI.
"""

import logging

from langgraph.types import interrupt

from src.workflow.cli_helpers import (
    display_article_for_review,
    display_topics_for_selection,
    prompt_user_approval,
    prompt_user_topic_selection,
)
from src.workflow.graph_state import ArticleWorkflowState
from src.workflow.nodes import BaseNode, NodeRegistry, handle_node_errors, log_node_execution

logger = logging.getLogger(__name__)


@NodeRegistry.register("user_selection")
class UserSelectionNode(BaseNode):
    """Node that pauses workflow for user to manually select a topic.

    Workflow Behavior:
        1. Receives analyzed/scored topics from AnalyzeTrendsNode
        2. Displays topics with scores to user
        3. Pauses execution (interrupt)
        4. Collects user's topic selection
        5. Updates state with selected topic
        6. Proceeds to PlanStructureNode

    State Requirements:
        - scored_topics: List of analyzed topics with scores

    State Updates:
        - selected_topic: User's chosen topic
        - current_step: Next step after selection

    Example:
        >>> state = {
        ...     "workflow_id": "abc-123",
        ...     "scored_topics": [
        ...         {"topic": "Python Async", "score": 8.5},
        ...         {"topic": "Type Hints", "score": 7.2}
        ...     ],
        ...     "current_step": "get_user_selection"
        ... }
        >>> node = UserSelectionNode()
        >>> result = await node.execute(state)
        >>> # User sees topics and is prompted to select one
        >>> # Workflow pauses here until user responds
    """

    @property
    def name(self) -> str:
        """Return node name."""
        return "user_selection"

    @handle_node_errors
    @log_node_execution
    async def execute(self, state: ArticleWorkflowState) -> dict:
        """Execute user topic selection interaction.

        Args:
            state: Current workflow state with scored_topics

        Returns:
            State updates with selected_topic

        Raises:
            ValueError: If scored_topics is missing or empty
        """
        workflow_id = state.get("workflow_id", "unknown")
        scored_topics = state.get("scored_topics", [])

        # Validate required data
        if not scored_topics:
            raise ValueError("No scored_topics found in state for user selection")

        logger.info(f"[{workflow_id}] Prompting user to select from {len(scored_topics)} topics")

        # Display topics to user
        display_topics_for_selection(scored_topics)

        # Pause workflow and wait for user input via interrupt
        try:
            # Use LangGraph's interrupt to pause execution
            selection_index = interrupt(
                value={
                    "type": "topic_selection",
                    "topics": scored_topics,
                    "message": "Please select a topic",
                }
            )

            # If we get here, user provided input (workflow resumed)
            # If selection_index is None, collect it via CLI
            if selection_index is None:
                selection_index = prompt_user_topic_selection(len(scored_topics))

            # Validate selection
            if not (1 <= selection_index <= len(scored_topics)):
                raise ValueError(f"Invalid selection: {selection_index}")

            # Get selected topic (convert from 1-based to 0-based index)
            selected_topic_data = scored_topics[selection_index - 1]
            selected_topic = selected_topic_data.get("topic")

            if not selected_topic:
                raise ValueError("Selected topic data is missing 'topic' field")

            logger.info(
                f"[{workflow_id}] User selected topic: '{selected_topic}' (index {selection_index})"
            )

            return {
                "selected_topic": selected_topic,
                "current_step": "plan_structure",
            }

        except KeyboardInterrupt:
            logger.warning(f"[{workflow_id}] User cancelled topic selection")
            raise ValueError("Topic selection cancelled by user")


@NodeRegistry.register("user_approval")
class UserApprovalNode(BaseNode):
    """Node that pauses workflow for user to approve or revise article.

    Workflow Behavior:
        1. Receives reviewed article from ReviewNode
        2. Displays article with metadata to user
        3. Pauses execution (interrupt)
        4. Collects user's decision (approve/revise)
        5. If revise: collects feedback and routes to RevisionNode
        6. If approve: routes to PublishNode

    State Requirements:
        - reviewed_article: Polished article from ReviewNode
        - revision_count: Current revision count
        - max_revisions: Maximum allowed revisions

    State Updates:
        - user_approval: Boolean approval decision
        - user_feedback: Revision feedback (if revising)
        - current_step: Next step (publish or revise)

    Example:
        >>> state = {
        ...     "workflow_id": "abc-123",
        ...     "reviewed_article": {
        ...         "polished_content": "Article text...",
        ...         "seo_title": "Great Title",
        ...         "word_count": 1500
        ...     },
        ...     "revision_count": 0,
        ...     "max_revisions": 3,
        ...     "current_step": "get_user_approval"
        ... }
        >>> node = UserApprovalNode()
        >>> result = await node.execute(state)
        >>> # User sees article and is prompted to approve/revise
        >>> # Workflow pauses here until user responds
    """

    @property
    def name(self) -> str:
        """Return node name."""
        return "user_approval"

    @handle_node_errors
    @log_node_execution
    async def execute(self, state: ArticleWorkflowState) -> dict:
        """Execute user article approval interaction.

        Args:
            state: Current workflow state with reviewed_article

        Returns:
            State updates with approval decision and next step

        Raises:
            ValueError: If reviewed_article is missing or max revisions exceeded
        """
        workflow_id = state.get("workflow_id", "unknown")
        reviewed_article = state.get("reviewed_article")
        revision_count = state.get("revision_count", 0)
        max_revisions = state.get("max_revisions", 3)

        # Validate required data
        if not reviewed_article:
            raise ValueError("No reviewed_article found in state for user approval")

        # Check revision limits
        if revision_count >= max_revisions:
            logger.warning(
                f"[{workflow_id}] Maximum revisions ({max_revisions}) reached. "
                "Auto-approving article."
            )
            return {
                "user_approval": True,
                "current_step": "save_article",
            }

        logger.info(
            f"[{workflow_id}] Prompting user to approve article "
            f"(revision {revision_count}/{max_revisions})"
        )

        # Display article to user
        display_article_for_review(reviewed_article)

        # Pause workflow and wait for user input via interrupt
        try:
            # Use LangGraph's interrupt to pause execution
            user_input = interrupt(
                value={
                    "type": "article_approval",
                    "article": reviewed_article,
                    "revision_count": revision_count,
                    "max_revisions": max_revisions,
                    "message": "Please approve or request revision",
                }
            )

            # If we get here, user provided input (workflow resumed)
            # If user_input is None, collect it via CLI
            if user_input is None:
                decision, feedback = prompt_user_approval()
            else:
                # Extract from provided input
                decision = user_input.get("decision")
                feedback = user_input.get("feedback")

            # Process decision
            if decision == "approve":
                logger.info(f"[{workflow_id}] User approved article for publication")
                return {
                    "user_approval": True,
                    "current_step": "save_article",
                }

            elif decision == "revise":
                if not feedback:
                    raise ValueError("Revision feedback cannot be empty")

                logger.info(
                    f"[{workflow_id}] User requested revision. Feedback: {feedback[:100]}..."
                )
                return {
                    "user_approval": False,
                    "user_feedback": feedback,
                    "current_step": "revise_article",
                }

            else:
                raise ValueError(f"Invalid approval decision: {decision}")

        except KeyboardInterrupt:
            logger.warning(f"[{workflow_id}] User cancelled article approval")
            raise ValueError("Article approval cancelled by user")


# Export nodes for easy import
__all__ = [
    "UserSelectionNode",
    "UserApprovalNode",
]
