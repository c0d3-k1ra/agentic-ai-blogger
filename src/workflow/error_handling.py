"""Error handling and recovery mechanisms for the workflow.

This module provides error handling utilities, retry logic, and recovery
strategies for the article generation workflow. It ensures graceful degradation
and provides mechanisms to recover from transient failures.

Key Components:
- Custom exception classes for different error types
- Retry decorators with exponential backoff
- Error context tracking
- Recovery strategies
- Error logging and reporting
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Optional, Type

logger = logging.getLogger(__name__)


# Custom Exception Classes
class WorkflowError(Exception):
    """Base exception for workflow-related errors."""

    def __init__(self, message: str, workflow_id: Optional[str] = None, **context):
        """Initialize workflow error with context.

        Args:
            message: Error message
            workflow_id: ID of workflow where error occurred
            **context: Additional context information
        """
        super().__init__(message)
        self.workflow_id = workflow_id
        self.context = context
        self.timestamp = time.time()

    def __str__(self):
        """String representation with workflow ID if available."""
        base = super().__str__()
        if self.workflow_id:
            return f"[{self.workflow_id}] {base}"
        return base


class NodeExecutionError(WorkflowError):
    """Error during node execution."""

    def __init__(self, message: str, node_name: str, workflow_id: Optional[str] = None, **context):
        """Initialize node execution error.

        Args:
            message: Error message
            node_name: Name of node where error occurred
            workflow_id: ID of workflow
            **context: Additional context
        """
        super().__init__(message, workflow_id, **context)
        self.node_name = node_name


class APIError(WorkflowError):
    """Error when calling external APIs."""

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: Optional[int] = None,
        workflow_id: Optional[str] = None,
        **context,
    ):
        """Initialize API error.

        Args:
            message: Error message
            api_name: Name of API that failed
            status_code: HTTP status code if applicable
            workflow_id: ID of workflow
            **context: Additional context
        """
        super().__init__(message, workflow_id, **context)
        self.api_name = api_name
        self.status_code = status_code


class StateValidationError(WorkflowError):
    """Error when validating workflow state."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        workflow_id: Optional[str] = None,
        **context,
    ):
        """Initialize state validation error.

        Args:
            message: Error message
            field: State field that failed validation
            workflow_id: ID of workflow
            **context: Additional context
        """
        super().__init__(message, workflow_id, **context)
        self.field = field


class RecoverableError(WorkflowError):
    """Error that can potentially be recovered from with retry."""

    pass


class UnrecoverableError(WorkflowError):
    """Error that cannot be recovered from."""

    pass


# Retry Logic
def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Decorator to retry function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for delay between retries
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def call_api():
            # API call that might fail
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries} retry attempts failed for {func.__name__}: {e}"
                        )

            # If we get here, all retries failed
            raise last_exception

        return wrapper

    return decorator


# Error Context Manager
class ErrorContext:
    """Context manager for tracking error information during execution.

    Usage:
        with ErrorContext("node_name", workflow_id="wf-123") as ctx:
            # Code that might fail
            ctx.add_info("key", "value")
    """

    def __init__(self, operation: str, workflow_id: Optional[str] = None):
        """Initialize error context.

        Args:
            operation: Name of operation being performed
            workflow_id: ID of workflow
        """
        self.operation = operation
        self.workflow_id = workflow_id
        self.info: dict[str, Any] = {}
        self.start_time = None

    def __enter__(self):
        """Enter context, recording start time."""
        self.start_time = time.time()
        logger.debug(f"Starting operation: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context, logging duration and any errors."""
        duration = time.time() - self.start_time if self.start_time else 0

        if exc_type is None:
            logger.debug(f"Operation '{self.operation}' completed successfully in {duration:.2f}s")
        else:
            logger.error(
                f"Operation '{self.operation}' failed after {duration:.2f}s: {exc_val}",
                extra={"workflow_id": self.workflow_id, "context": self.info},
            )

        # Don't suppress the exception
        return False

    def add_info(self, key: str, value: Any):
        """Add contextual information.

        Args:
            key: Information key
            value: Information value
        """
        self.info[key] = value


# Error Recovery Strategies
class RecoveryStrategy:
    """Base class for error recovery strategies."""

    def can_recover(self, error: Exception) -> bool:
        """Determine if this strategy can recover from the error.

        Args:
            error: Exception to check

        Returns:
            True if recovery is possible
        """
        raise NotImplementedError

    def recover(self, error: Exception, context: dict) -> Any:
        """Attempt to recover from the error.

        Args:
            error: Exception to recover from
            context: Additional context for recovery

        Returns:
            Recovery result or None if recovery failed
        """
        raise NotImplementedError


class FallbackRecovery(RecoveryStrategy):
    """Recovery strategy that uses fallback values."""

    def __init__(self, fallback_value: Any = None):
        """Initialize with fallback value.

        Args:
            fallback_value: Value to return on recovery
        """
        self.fallback_value = fallback_value

    def can_recover(self, error: Exception) -> bool:
        """Always returns True - fallback can handle any error."""
        return True

    def recover(self, error: Exception, context: dict) -> Any:
        """Return fallback value.

        Args:
            error: Exception (ignored)
            context: Context (ignored)

        Returns:
            Configured fallback value
        """
        logger.info(f"Using fallback recovery for error: {error}")
        return self.fallback_value


class RetryRecovery(RecoveryStrategy):
    """Recovery strategy that retries the operation."""

    def __init__(self, max_attempts: int = 3, delay: float = 1.0):
        """Initialize retry recovery.

        Args:
            max_attempts: Maximum retry attempts
            delay: Delay between retries in seconds
        """
        self.max_attempts = max_attempts
        self.delay = delay

    def can_recover(self, error: Exception) -> bool:
        """Check if error is recoverable (not UnrecoverableError)."""
        return not isinstance(error, UnrecoverableError)

    def recover(self, error: Exception, context: dict) -> Any:
        """Attempt to retry the operation.

        Args:
            error: Exception that occurred
            context: Must contain 'operation' callable to retry

        Returns:
            Result of successful retry

        Raises:
            Exception: If all retry attempts fail
        """
        operation = context.get("operation")
        if not operation or not callable(operation):
            raise ValueError("Recovery context must contain 'operation' callable")

        logger.info(f"Attempting retry recovery for error: {error}")

        for attempt in range(self.max_attempts):
            try:
                time.sleep(self.delay * (attempt + 1))  # Increasing delay
                return operation()
            except Exception as e:
                if attempt == self.max_attempts - 1:
                    logger.error(f"All {self.max_attempts} retry attempts failed: {e}")
                    raise
                logger.warning(f"Retry attempt {attempt + 1} failed: {e}")


# Error Handler
def handle_node_error(
    node_name: str, workflow_id: Optional[str] = None
) -> Callable[[Callable], Callable]:
    """Decorator to handle errors in workflow nodes.

    Wraps node execution with error handling, logging, and context.

    Args:
        node_name: Name of the node
        workflow_id: Optional workflow ID for context

    Returns:
        Decorated function with error handling

    Example:
        @handle_node_error("scout_topics")
        def execute(self, state):
            # Node logic
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract state from args or kwargs
            state = args[0] if len(args) > 0 else kwargs.get("state", {})

            # Get workflow_id from state, kwargs, or fallback to decorator param
            wf_id = None
            if isinstance(state, dict):
                wf_id = state.get("workflow_id")
            if wf_id is None:
                wf_id = kwargs.get("workflow_id", workflow_id)

            try:
                with ErrorContext(f"{node_name}.execute", wf_id) as ctx:
                    # Add current step to context if available
                    if isinstance(state, dict):
                        ctx.add_info("current_step", state.get("current_step"))

                    result = func(*args, **kwargs)
                    return result

            except Exception as e:
                logger.error(
                    f"Node '{node_name}' failed: {e}",
                    exc_info=True,
                    extra={"workflow_id": wf_id, "node": node_name},
                )
                # Re-raise as NodeExecutionError for better error tracking
                raise NodeExecutionError(
                    message=str(e), node_name=node_name, workflow_id=wf_id, original_error=e
                ) from e

        return wrapper

    return decorator


# Validation Helpers
def validate_state_field(
    state: dict, field: str, expected_type: Type, workflow_id: Optional[str] = None
):
    """Validate that a state field exists and has the correct type.

    Args:
        state: Workflow state dictionary
        field: Field name to validate
        expected_type: Expected type of the field
        workflow_id: Optional workflow ID for error context

    Raises:
        StateValidationError: If validation fails
    """
    if field not in state:
        raise StateValidationError(
            f"Required field '{field}' missing from state", field=field, workflow_id=workflow_id
        )

    value = state[field]
    if not isinstance(value, expected_type):
        raise StateValidationError(
            f"Field '{field}' has type {type(value).__name__}, expected {expected_type.__name__}",
            field=field,
            workflow_id=workflow_id,
            actual_type=type(value).__name__,
            expected_type=expected_type.__name__,
        )


__all__ = [
    # Exceptions
    "WorkflowError",
    "NodeExecutionError",
    "APIError",
    "StateValidationError",
    "RecoverableError",
    "UnrecoverableError",
    # Decorators
    "retry_with_backoff",
    "handle_node_error",
    # Context
    "ErrorContext",
    # Recovery
    "RecoveryStrategy",
    "FallbackRecovery",
    "RetryRecovery",
    # Validation
    "validate_state_field",
]
