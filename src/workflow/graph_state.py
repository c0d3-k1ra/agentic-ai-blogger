"""LangGraph state schema for article generation workflow.

This module defines the TypedDict state structure used by LangGraph to track
the article generation workflow. The state is designed to be:
- Serializable (can be saved to checkpoints)
- Type-safe (mypy validated)
- Immutable-friendly (nodes return state updates, not mutations)
- Debuggable (tracks errors and progress)

State Flow:
    1. User provides query
    2. Topics generated and scored
    3. User selects topic
    4. Outline created
    5. Sections researched
    6. Sections written
    7. Article reviewed
    8. User approves or requests revision
    9. Article revised (if needed, max 3 times)
    10. Final article saved

Example:
    >>> state: ArticleWorkflowState = {
    ...     "workflow_id": "abc-123",
    ...     "user_query": "Python async programming",
    ...     "current_step": "scout_topics",
    ...     "revision_count": 0,
    ...     "max_revisions": 3,
    ...     "errors": [],
    ...     "retry_count": 0
    ... }
"""

from operator import add
from typing import Annotated, Literal, TypedDict

# Type aliases for clarity
WorkflowStep = Literal[
    "scout_topics",
    "analyze_trends",
    "get_user_selection",
    "plan_structure",
    "research_sections",
    "write_sections",
    "review_article",
    "get_user_approval",
    "revise_article",
    "save_article",
    "completed",
    "failed",
]


class ArticleWorkflowState(TypedDict, total=False):
    """Complete state for article generation workflow.

    This TypedDict defines all possible state fields. Fields marked as required
    (in __required_keys__) must be present. All other fields are optional and
    will be populated as the workflow progresses.

    Required Fields:
        workflow_id: Unique identifier for this workflow instance
        user_query: Initial topic query from user
        current_step: Current workflow step
        revision_count: Number of revisions completed
        max_revisions: Maximum allowed revisions
        errors: List of error messages (accumulates)
        retry_count: Number of retry attempts

    Optional Fields - User Inputs:
        selected_topic: Topic chosen by user (from scored list)
        user_feedback: User's revision feedback
        user_approval: Whether user approved the article

    Optional Fields - Agent Outputs:
        topic_candidates: List of topic suggestions (from scout)
        scored_topics: Ranked topics with scores (from analyzer)
        outline: Article outline structure (from planner)
        research_dossiers: Research data per section (from researcher)
        written_sections: Written content per section (from writer)
        reviewed_article: Polished article with SEO (from reviewer)
        revised_article: Revised article content (from revision)

    Optional Fields - Metadata:
        article_id: Database ID once article is saved
        topic_id: Database ID of selected topic
        final_article: Complete final article data
    """

    # Required fields - must be present in initial state
    workflow_id: str
    user_query: str
    current_step: WorkflowStep
    revision_count: int
    max_revisions: int
    errors: Annotated[list[str], add]  # Accumulates errors
    retry_count: int

    # Optional fields - User inputs
    selected_topic: str
    user_feedback: str
    user_approval: bool

    # Optional fields - Agent outputs
    topic_candidates: list[dict]
    scored_topics: list[dict]
    outline: dict
    research_dossiers: dict[str, dict]  # section_title -> research dossier
    written_sections: dict[str, dict]  # section_title -> written content
    reviewed_article: dict
    revised_article: dict

    # Optional fields - Database IDs
    article_id: str
    topic_id: str

    # Optional fields - Final output
    final_article: dict


# Validation helpers


def validate_required_fields(state: dict) -> tuple[bool, list[str]]:
    """Validate that required state fields are present.

    Args:
        state: State dictionary to validate

    Returns:
        Tuple of (is_valid, list_of_missing_fields)

    Examples:
        >>> state = {"workflow_id": "123", "user_query": "test"}
        >>> valid, missing = validate_required_fields(state)
        >>> valid
        False
        >>> "current_step" in missing
        True
    """
    required = {
        "workflow_id",
        "user_query",
        "current_step",
        "revision_count",
        "max_revisions",
        "errors",
        "retry_count",
    }

    missing = [field for field in required if field not in state]
    return len(missing) == 0, missing


def validate_workflow_step(step: str) -> bool:
    """Validate that step is a valid workflow step.

    Args:
        step: Step name to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_workflow_step("scout_topics")
        True
        >>> validate_workflow_step("invalid_step")
        False
    """
    valid_steps = {
        "scout_topics",
        "analyze_trends",
        "get_user_selection",
        "plan_structure",
        "research_sections",
        "write_sections",
        "review_article",
        "get_user_approval",
        "revise_article",
        "save_article",
        "completed",
        "failed",
    }
    return step in valid_steps


def validate_revision_count(state: dict) -> tuple[bool, str]:
    """Validate revision count is within limits.

    Args:
        state: State dictionary containing revision counts

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> state = {"revision_count": 2, "max_revisions": 3}
        >>> valid, error = validate_revision_count(state)
        >>> valid
        True
        >>> state = {"revision_count": 5, "max_revisions": 3}
        >>> valid, error = validate_revision_count(state)
        >>> valid
        False
    """
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 3)

    if revision_count < 0:
        return False, "revision_count cannot be negative"

    if max_revisions < 1:
        return False, "max_revisions must be at least 1"

    if revision_count > max_revisions:
        return False, f"revision_count ({revision_count}) exceeds max_revisions ({max_revisions})"

    return True, ""


def create_initial_state(
    workflow_id: str,
    user_query: str,
    *,
    max_revisions: int = 3,
) -> ArticleWorkflowState:
    """Create initial workflow state with required fields.

    Args:
        workflow_id: Unique workflow identifier
        user_query: User's topic query
        max_revisions: Maximum allowed revisions (default: 3)

    Returns:
        Initial state dictionary with required fields

    Raises:
        ValueError: If inputs are invalid

    Examples:
        >>> state = create_initial_state("abc-123", "Python async")
        >>> state["workflow_id"]
        'abc-123'
        >>> state["current_step"]
        'scout_topics'
        >>> state["revision_count"]
        0
    """
    if not workflow_id or not workflow_id.strip():
        raise ValueError("workflow_id cannot be empty")

    if not user_query or not user_query.strip():
        raise ValueError("user_query cannot be empty")

    if max_revisions < 1:
        raise ValueError("max_revisions must be at least 1")

    return ArticleWorkflowState(
        workflow_id=workflow_id.strip(),
        user_query=user_query.strip(),
        current_step="scout_topics",
        revision_count=0,
        max_revisions=max_revisions,
        errors=[],
        retry_count=0,
    )
