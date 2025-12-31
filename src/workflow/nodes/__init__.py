"""LangGraph workflow node infrastructure.

This module provides the base infrastructure for all workflow nodes:
- BaseNode abstract class: Contract for all nodes
- Error handling decorator: Graceful error capture
- Logging decorator: Automatic execution logging
- Retry decorator: Automatic retry with exponential backoff
- NodeRegistry: Node registration and discovery

Example Usage:
    >>> from src.workflow.nodes import (
    ...     BaseNode,
    ...     handle_node_errors,
    ...     log_node_execution,
    ...     retry_on_error,
    ...     NodeRegistry
    ... )
    >>>
    >>> @NodeRegistry.register("my_node")
    ... class MyNode(BaseNode):
    ...     @property
    ...     def name(self) -> str:
    ...         return "my_node"
    ...
    ...     @handle_node_errors
    ...     @log_node_execution
    ...     @retry_on_error(max_retries=3)
    ...     async def execute(self, state):
    ...         return {"current_step": "next_step"}
"""

import asyncio
import functools
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

from src.workflow.graph_state import ArticleWorkflowState

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


class BaseNode(ABC):
    """Abstract base class for workflow nodes.

    All workflow nodes must:
    1. Accept ArticleWorkflowState as input
    2. Return dict of state updates (not full state)
    3. Handle errors gracefully (use @handle_node_errors)
    4. Log execution (use @log_node_execution)
    5. Implement retry logic if needed (use @retry_on_error)

    Example:
        >>> class MyNode(BaseNode):
        ...     @property
        ...     def name(self) -> str:
        ...         return "my_node"
        ...
        ...     async def execute(self, state: ArticleWorkflowState) -> dict:
        ...         return {"current_step": "next_step"}
    """

    @abstractmethod
    async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
        """Execute node logic and return state updates.

        Args:
            state: Current workflow state

        Returns:
            Dictionary of state updates to apply. Should NOT return
            the full state, only the fields that need updating.

        Note:
            Should not raise exceptions when decorated with
            @handle_node_errors - errors will be captured in
            the returned state dict.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return node name for logging and identification.

        Returns:
            String name of the node, typically matching the
            function or class name.
        """
        pass


def handle_node_errors(func: F) -> F:
    """Decorator to handle node execution errors gracefully.

    Catches all exceptions during node execution and converts them
    to error state updates instead of crashing the workflow.

    Args:
        func: Async function to wrap (node execute method)

    Returns:
        Wrapped function that catches exceptions

    Example:
        >>> @handle_node_errors
        ... async def my_node(state):
        ...     raise ValueError("Something went wrong")
        ...     return {"current_step": "next"}
        >>>
        >>> result = await my_node({})
        >>> "errors" in result
        True
        >>> result["current_step"]
        'failed'
    """

    @functools.wraps(func)
    async def wrapper(self_or_state, *args, **kwargs) -> dict[str, Any]:
        # Handle both instance methods (self, state) and functions (state)
        if isinstance(self_or_state, BaseNode):
            # Instance method: self_or_state is self, first arg is state
            state = args[0] if args else kwargs.get("state", {})
            try:
                return await func(self_or_state, state, *args[1:], **kwargs)
            except Exception as e:
                node_name = self_or_state.name
                error_msg = f"Node '{node_name}' failed: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {
                    "errors": [error_msg],
                    "current_step": "failed",
                }
        else:
            # Regular function: self_or_state is state
            state = self_or_state
            try:
                return await func(state, *args, **kwargs)
            except Exception as e:
                node_name = getattr(func, "__name__", "unknown_node")
                error_msg = f"Node '{node_name}' failed: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {
                    "errors": [error_msg],
                    "current_step": "failed",
                }

    return wrapper  # type: ignore


def log_node_execution(func: F) -> F:
    """Decorator to log node execution start, end, and duration.

    Logs:
    - Node name
    - Workflow ID
    - Execution start timestamp
    - Execution end timestamp
    - Execution duration in seconds

    Args:
        func: Async function to wrap (node execute method)

    Returns:
        Wrapped function with logging

    Example:
        >>> @log_node_execution
        ... async def my_node(state):
        ...     return {"current_step": "next"}
        >>>
        >>> # Logs:
        >>> # INFO: [wf-123] Starting node: my_node
        >>> # INFO: [wf-123] Completed node: my_node (0.05s)
    """

    @functools.wraps(func)
    async def wrapper(self_or_state, *args, **kwargs) -> dict[str, Any]:
        # Handle both instance methods (self, state) and functions (state)
        if isinstance(self_or_state, BaseNode):
            # Instance method: self_or_state is self, first arg is state
            state = args[0] if args else kwargs.get("state", {})
            node_name = self_or_state.name
            workflow_id = state.get("workflow_id", "unknown")

            logger.info(f"[{workflow_id}] Starting execution of node: {node_name}")
            start_time = time.time()

            try:
                result = await func(self_or_state, state, *args[1:], **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"[{workflow_id}] Completed execution of node: {node_name} ({duration:.2f}s)"
                )
                return result
            except Exception:
                duration = time.time() - start_time
                logger.error(
                    f"[{workflow_id}] Failed execution of node: {node_name} ({duration:.2f}s)"
                )
                raise
        else:
            # Regular function: self_or_state is state
            state = self_or_state
            node_name = getattr(func, "__name__", "unknown_node")
            workflow_id = state.get("workflow_id", "unknown")

            logger.info(f"[{workflow_id}] Starting node: {node_name}")
            start_time = time.time()

            try:
                result = await func(state, *args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"[{workflow_id}] Completed node: {node_name} ({duration:.2f}s)")
                return result
            except Exception:
                duration = time.time() - start_time
                logger.error(f"[{workflow_id}] Failed node: {node_name} ({duration:.2f}s)")
                raise

    return wrapper  # type: ignore


def retry_on_error(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator to retry node execution on failure with exponential backoff.

    Automatically retries failed node executions with configurable
    retry count and exponential backoff timing.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
            Wait time = backoff_factor ^ attempt
            e.g., with factor=2.0: 1s, 2s, 4s, 8s...
        exceptions: Tuple of exception types to catch and retry (default: all)

    Returns:
        Decorator function

    Example:
        >>> @retry_on_error(max_retries=3, backoff_factor=2.0)
        ... async def flaky_node(state):
        ...     # Might fail, will be retried automatically
        ...     return {"current_step": "next"}
        >>>
        >>> # If it fails:
        >>> # WARNING: Node 'flaky_node' failed (attempt 1/4). Retrying in 1.0s...
        >>> # WARNING: Node 'flaky_node' failed (attempt 2/4). Retrying in 2.0s...
        >>> # ... (retries with exponential backoff)

    Note:
        After max_retries exhausted, the original exception is re-raised.
        Use @handle_node_errors to convert to error state instead.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            node_name = getattr(func, "__name__", "unknown_node")
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        wait_time = backoff_factor**attempt
                        logger.warning(
                            f"Node '{node_name}' failed "
                            f"(attempt {attempt + 1}/{max_retries + 1}). "
                            f"Retrying in {wait_time:.1f}s... "
                            f"Error: {type(e).__name__}: {str(e)}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"Node '{node_name}' failed after "
                            f"{max_retries + 1} attempts. "
                            f"Final error: {type(e).__name__}: {str(e)}"
                        )

            # All retries exhausted, re-raise last exception
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore

    return decorator


class NodeRegistry:
    """Registry for workflow nodes.

    Provides a centralized registry for node registration and discovery.
    Useful for:
    - Dynamic node loading
    - Node inspection and listing
    - Testing and mocking
    - Dependency injection

    Example:
        >>> @NodeRegistry.register("scout_topics")
        ... class ScoutTopicsNode(BaseNode):
        ...     @property
        ...     def name(self) -> str:
        ...         return "scout_topics"
        ...
        ...     async def execute(self, state):
        ...         return {"current_step": "analyze_trends"}
        >>>
        >>> # Later, retrieve the node
        >>> node_class = NodeRegistry.get("scout_topics")
        >>> node = node_class()
        >>>
        >>> # List all registered nodes
        >>> NodeRegistry.list_nodes()
        ['scout_topics']
    """

    _nodes: dict[str, type[BaseNode]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[type[BaseNode]], type[BaseNode]]:
        """Decorator to register a node class by name.

        Args:
            name: Unique name for the node

        Returns:
            Decorator function that registers the node class

        Raises:
            ValueError: If a node with the same name is already registered

        Example:
            >>> @NodeRegistry.register("my_node")
            ... class MyNode(BaseNode):
            ...     pass
        """

        def decorator(node_class: type[BaseNode]) -> type[BaseNode]:
            if name in cls._nodes:
                raise ValueError(f"Node '{name}' is already registered")

            cls._nodes[name] = node_class
            logger.debug(f"Registered node: {name} -> {node_class.__name__}")
            return node_class

        return decorator

    @classmethod
    def get(cls, name: str) -> type[BaseNode]:
        """Get a registered node class by name.

        Args:
            name: Name of the node to retrieve

        Returns:
            The registered node class

        Raises:
            KeyError: If no node with the given name is registered

        Example:
            >>> node_class = NodeRegistry.get("my_node")
            >>> node = node_class()
        """
        if name not in cls._nodes:
            available = ", ".join(cls._nodes.keys()) or "none"
            raise KeyError(f"Node '{name}' not registered. Available nodes: {available}")
        return cls._nodes[name]

    @classmethod
    def list_nodes(cls) -> list[str]:
        """List all registered node names.

        Returns:
            Sorted list of registered node names

        Example:
            >>> NodeRegistry.list_nodes()
            ['analyze_trends', 'scout_topics', 'write_sections']
        """
        return sorted(cls._nodes.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered nodes.

        Useful for testing to ensure a clean state between tests.

        Example:
            >>> NodeRegistry.clear()
            >>> NodeRegistry.list_nodes()
            []
        """
        cls._nodes.clear()
        logger.debug("Cleared node registry")

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a node is registered.

        Args:
            name: Name to check

        Returns:
            True if registered, False otherwise

        Example:
            >>> NodeRegistry.is_registered("my_node")
            True
        """
        return name in cls._nodes


# Import all node modules to trigger registration
# These imports must be at the bottom after class definitions to avoid circular imports
from src.workflow.nodes import (  # noqa: E402, F401
    analyze_trends,
    plan_structure,
    publish,
    research,
    review,
    revision,
    scout_topics,
    user_interaction,
    write_draft,
)

# Export all public APIs
__all__ = [
    "BaseNode",
    "handle_node_errors",
    "log_node_execution",
    "retry_on_error",
    "NodeRegistry",
]
