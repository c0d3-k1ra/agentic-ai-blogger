"""Sequential workflow orchestrator (happy path only).

This module provides a pure, deterministic sequential workflow execution
without agents, LLM calls, email, database, or async operations.

Design Principles:
- Pure function (no side effects)
- Immutable state (returns new instances)
- Explicit step sequence (no branching)
- Errors captured in state (not raised)
"""

from datetime import datetime, timezone
from typing import Final

from src.workflow.state import WorkflowState, WorkflowStatus

# Hardcoded sequential steps
WORKFLOW_STEPS: Final[list[str]] = [
    "initialize",
    "collect_inputs",
    "plan_structure",
    "research",
    "write_draft",
    "review",
    "finalize",
]


def run_sequential_workflow(
    state: WorkflowState,
    *,
    fail_at_step: str | None = None,
) -> WorkflowState:
    """Execute workflow steps sequentially.

    This is a pure function that processes a workflow by advancing through
    predefined steps. It returns a new WorkflowState without mutating the input.

    Args:
        state: Initial workflow state (immutable)
        fail_at_step: Optional step name to simulate failure for testing

    Returns:
        New WorkflowState with updated progress. The returned state will have:
        - status: RUNNING during execution, COMPLETED on success, FAILED on error
        - current_step: Advanced through the step sequence
        - updated_at: Refreshed on each step transition
        - error_message: Populated if fail_at_step is triggered

    Behavior:
        - Status transitions: PENDING → RUNNING → COMPLETED
        - On failure: Status becomes FAILED, error_message populated
        - Each step updates current_step and updated_at
        - Original state is never modified

    Example:
        >>> from uuid import uuid4
        >>> state = WorkflowState(workflow_id=uuid4(), topic_name="Test")
        >>> result = run_sequential_workflow(state)
        >>> result.status == WorkflowStatus.COMPLETED
        True
        >>> result.current_step == "finalize"
        True
    """
    # Start with a copy to ensure immutability
    current_state = state

    # Transition to RUNNING if starting from PENDING
    if current_state.status == WorkflowStatus.PENDING:
        current_state = current_state.model_copy(
            deep=True,
            update={
                "status": WorkflowStatus.RUNNING,
                "updated_at": datetime.now(timezone.utc),
            },
        )

    # Execute each step sequentially
    for step in WORKFLOW_STEPS:
        # Check for simulated failure
        if fail_at_step and step == fail_at_step:
            return current_state.model_copy(
                deep=True,
                update={
                    "status": WorkflowStatus.FAILED,
                    "current_step": step,
                    "error_message": f"Simulated failure at step: {step}",
                    "updated_at": datetime.now(timezone.utc),
                },
            )

        # Advance to next step
        current_state = current_state.model_copy(
            deep=True,
            update={
                "current_step": step,
                "updated_at": datetime.now(timezone.utc),
            },
        )

    # Mark workflow as completed
    return current_state.model_copy(
        deep=True,
        update={
            "status": WorkflowStatus.COMPLETED,
            "updated_at": datetime.now(timezone.utc),
        },
    )
