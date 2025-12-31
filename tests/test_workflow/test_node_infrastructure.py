"""Tests for LangGraph node infrastructure.

Tests cover:
- BaseNode abstract class
- Error handling decorator
- Logging decorator
- Retry decorator
- NodeRegistry
"""

import asyncio
import logging
from typing import Any

import pytest

from src.workflow.graph_state import ArticleWorkflowState
from src.workflow.nodes import (
    BaseNode,
    NodeRegistry,
    handle_node_errors,
    log_node_execution,
    retry_on_error,
)


class TestBaseNode:
    """Tests for BaseNode abstract class."""

    def test_cannot_instantiate_base_node(self):
        """Test that BaseNode cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseNode()  # type: ignore

    def test_subclass_must_implement_execute(self):
        """Test that subclass must implement execute method."""

        class IncompleteNode(BaseNode):
            @property
            def name(self) -> str:
                return "incomplete"

            # Missing execute() implementation

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteNode()  # type: ignore

    def test_subclass_must_implement_name(self):
        """Test that subclass must implement name property."""

        class IncompleteNode(BaseNode):
            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {}

            # Missing name property

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteNode()  # type: ignore

    def test_valid_node_implementation(self):
        """Test that valid implementation can be instantiated."""

        class ValidNode(BaseNode):
            @property
            def name(self) -> str:
                return "valid_node"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {"current_step": "next"}

        node = ValidNode()
        assert node.name == "valid_node"

    @pytest.mark.asyncio
    async def test_node_execute_returns_dict(self):
        """Test that node execute method returns dict."""

        class TestNode(BaseNode):
            @property
            def name(self) -> str:
                return "test_node"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {
                    "current_step": "next_step",
                    "some_data": "test_value",
                }

        node = TestNode()
        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        result = await node.execute(state)

        assert isinstance(result, dict)
        assert result["current_step"] == "next_step"
        assert result["some_data"] == "test_value"


class TestErrorHandlingDecorator:
    """Tests for handle_node_errors decorator."""

    @pytest.mark.asyncio
    async def test_success_case_no_errors(self):
        """Test decorator with successful execution."""

        @handle_node_errors
        async def success_node(state: ArticleWorkflowState) -> dict:
            return {"current_step": "next", "data": "success"}

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        result = await success_node(state)

        assert result["current_step"] == "next"
        assert result["data"] == "success"
        assert "errors" not in result

    @pytest.mark.asyncio
    async def test_caught_exception_added_to_errors(self):
        """Test that exceptions are caught and added to errors."""

        @handle_node_errors
        async def failing_node(state: ArticleWorkflowState) -> dict:
            raise ValueError("Something went wrong")

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        result = await failing_node(state)

        assert "errors" in result
        assert len(result["errors"]) == 1
        assert "failing_node" in result["errors"][0]
        assert "ValueError" in result["errors"][0]
        assert "Something went wrong" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_current_step_set_to_failed(self):
        """Test that current_step is set to 'failed' on error."""

        @handle_node_errors
        async def failing_node(state: ArticleWorkflowState) -> dict:
            raise RuntimeError("Test error")

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        result = await failing_node(state)

        assert result["current_step"] == "failed"

    @pytest.mark.asyncio
    async def test_different_exception_types(self):
        """Test handling of different exception types."""

        @handle_node_errors
        async def node_with_type_error(state: ArticleWorkflowState) -> dict:
            raise TypeError("Type mismatch")

        @handle_node_errors
        async def node_with_key_error(state: ArticleWorkflowState) -> dict:
            raise KeyError("Missing key")

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        result1 = await node_with_type_error(state)
        assert "TypeError" in result1["errors"][0]
        assert "Type mismatch" in result1["errors"][0]

        result2 = await node_with_key_error(state)
        assert "KeyError" in result2["errors"][0]
        assert "Missing key" in result2["errors"][0]


class TestLoggingDecorator:
    """Tests for log_node_execution decorator."""

    @pytest.mark.asyncio
    async def test_start_log_emitted(self, caplog):
        """Test that start log is emitted."""

        @log_node_execution
        async def test_node(state: ArticleWorkflowState) -> dict:
            return {"current_step": "next"}

        state: ArticleWorkflowState = {
            "workflow_id": "wf-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        with caplog.at_level(logging.INFO):
            await test_node(state)

        assert any("Starting node: test_node" in record.message for record in caplog.records)
        assert any("[wf-123]" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_end_log_emitted(self, caplog):
        """Test that end log is emitted."""

        @log_node_execution
        async def test_node(state: ArticleWorkflowState) -> dict:
            return {"current_step": "next"}

        state: ArticleWorkflowState = {
            "workflow_id": "wf-456",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        with caplog.at_level(logging.INFO):
            await test_node(state)

        assert any("Completed node: test_node" in record.message for record in caplog.records)
        assert any("[wf-456]" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_duration_logged(self, caplog):
        """Test that duration is logged."""

        @log_node_execution
        async def slow_node(state: ArticleWorkflowState) -> dict:
            await asyncio.sleep(0.1)  # Simulate slow operation
            return {"current_step": "next"}

        state: ArticleWorkflowState = {
            "workflow_id": "wf-789",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        with caplog.at_level(logging.INFO):
            await slow_node(state)

        # Check that duration is in the completed log
        completed_logs = [r.message for r in caplog.records if "Completed node" in r.message]
        assert len(completed_logs) > 0
        assert "s)" in completed_logs[0]  # Duration format: (0.10s)

    @pytest.mark.asyncio
    async def test_error_log_on_exception(self, caplog):
        """Test that error log is emitted on exception."""

        @log_node_execution
        async def failing_node(state: ArticleWorkflowState) -> dict:
            raise ValueError("Test error")

        state: ArticleWorkflowState = {
            "workflow_id": "wf-error",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                await failing_node(state)

        assert any("Failed node: failing_node" in record.message for record in caplog.records)
        assert any("[wf-error]" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_workflow_id_in_logs(self, caplog):
        """Test that workflow ID is included in all logs."""

        @log_node_execution
        async def test_node(state: ArticleWorkflowState) -> dict:
            return {"current_step": "next"}

        state: ArticleWorkflowState = {
            "workflow_id": "unique-id-12345",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        with caplog.at_level(logging.INFO):
            await test_node(state)

        assert any("[unique-id-12345]" in record.message for record in caplog.records)


class TestRetryDecorator:
    """Tests for retry_on_error decorator."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Test no retries on successful first attempt."""
        call_count = 0

        @retry_on_error(max_retries=3)
        async def success_node(state: ArticleWorkflowState) -> dict:
            nonlocal call_count
            call_count += 1
            return {"current_step": "next"}

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        result = await success_node(state)

        assert result["current_step"] == "next"
        assert call_count == 1  # Called only once

    @pytest.mark.asyncio
    async def test_success_after_one_retry(self):
        """Test success after one retry."""
        call_count = 0

        @retry_on_error(max_retries=3, backoff_factor=0.01)
        async def flaky_node(state: ArticleWorkflowState) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("First attempt fails")
            return {"current_step": "next"}

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        result = await flaky_node(state)

        assert result["current_step"] == "next"
        assert call_count == 2  # First failed, second succeeded

    @pytest.mark.asyncio
    async def test_success_after_multiple_retries(self):
        """Test success after multiple retries."""
        call_count = 0

        @retry_on_error(max_retries=5, backoff_factor=0.01)
        async def very_flaky_node(state: ArticleWorkflowState) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError(f"Attempt {call_count} fails")
            return {"current_step": "next"}

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        result = await very_flaky_node(state)

        assert result["current_step"] == "next"
        assert call_count == 4  # 3 failures + 1 success

    @pytest.mark.asyncio
    async def test_failure_after_max_retries(self):
        """Test that exception is raised after max retries."""
        call_count = 0

        @retry_on_error(max_retries=2, backoff_factor=0.01)
        async def always_fails(state: ArticleWorkflowState) -> dict:
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        with pytest.raises(ValueError, match="Always fails"):
            await always_fails(state)

        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff works correctly."""
        call_times = []

        @retry_on_error(max_retries=3, backoff_factor=0.1)
        async def timed_node(state: ArticleWorkflowState) -> dict:
            import time

            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Retry me")
            return {"current_step": "next"}

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        await timed_node(state)

        # Check that delays follow exponential backoff pattern
        # backoff_factor=0.1: 0.1^0=1.0s, 0.1^1=0.1s, 0.1^2=0.01s
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # First delay should be ~1.0s (0.1^0 = 1.0)
        assert 0.9 < delay1 < 1.2

        # Second delay should be ~0.1s (0.1^1 = 0.1)
        assert 0.05 < delay2 < 0.15

    @pytest.mark.asyncio
    async def test_custom_exception_types(self):
        """Test retry only on specific exception types."""

        @retry_on_error(
            max_retries=2,
            backoff_factor=0.01,
            exceptions=(ValueError,),  # Only retry ValueError
        )
        async def selective_retry(state: ArticleWorkflowState) -> dict:
            raise TypeError("Not retried")

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        # TypeError should not be retried
        with pytest.raises(TypeError, match="Not retried"):
            await selective_retry(state)

    @pytest.mark.asyncio
    async def test_retry_with_value_error_only(self):
        """Test retry works with ValueError but not others."""
        value_error_count = 0
        type_error_count = 0

        @retry_on_error(max_retries=2, backoff_factor=0.01, exceptions=(ValueError,))
        async def value_error_node(state: ArticleWorkflowState) -> dict:
            nonlocal value_error_count
            value_error_count += 1
            if value_error_count < 2:
                raise ValueError("Retry me")
            return {"current_step": "next"}

        @retry_on_error(max_retries=2, backoff_factor=0.01, exceptions=(ValueError,))
        async def type_error_node(state: ArticleWorkflowState) -> dict:
            nonlocal type_error_count
            type_error_count += 1
            raise TypeError("Don't retry me")

        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "test",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        # ValueError should be retried
        result = await value_error_node(state)
        assert result["current_step"] == "next"
        assert value_error_count == 2

        # TypeError should not be retried
        with pytest.raises(TypeError):
            await type_error_node(state)
        assert type_error_count == 1  # No retries


class TestNodeRegistry:
    """Tests for NodeRegistry."""

    def setup_method(self):
        """Clear registry before each test."""
        NodeRegistry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        NodeRegistry.clear()

    def test_register_node(self):
        """Test registering a node."""

        @NodeRegistry.register("test_node")
        class TestNode(BaseNode):
            @property
            def name(self) -> str:
                return "test_node"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {}

        assert NodeRegistry.is_registered("test_node")

    def test_retrieve_registered_node(self):
        """Test retrieving a registered node."""

        @NodeRegistry.register("my_node")
        class MyNode(BaseNode):
            @property
            def name(self) -> str:
                return "my_node"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {}

        retrieved = NodeRegistry.get("my_node")
        assert retrieved == MyNode

    def test_list_registered_nodes(self):
        """Test listing all registered nodes."""

        @NodeRegistry.register("node_a")
        class NodeA(BaseNode):
            @property
            def name(self) -> str:
                return "node_a"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {}

        @NodeRegistry.register("node_b")
        class NodeB(BaseNode):
            @property
            def name(self) -> str:
                return "node_b"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {}

        nodes = NodeRegistry.list_nodes()
        assert nodes == ["node_a", "node_b"]  # Sorted

    def test_error_on_missing_node(self):
        """Test error when retrieving non-existent node."""
        with pytest.raises(KeyError, match="Node 'nonexistent' not registered"):
            NodeRegistry.get("nonexistent")

    def test_error_message_shows_available_nodes(self):
        """Test error message includes available nodes."""

        @NodeRegistry.register("available_node")
        class AvailableNode(BaseNode):
            @property
            def name(self) -> str:
                return "available_node"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {}

        with pytest.raises(KeyError, match="Available nodes: available_node"):
            NodeRegistry.get("missing_node")

    def test_clear_registry(self):
        """Test clearing the registry."""

        @NodeRegistry.register("temp_node")
        class TempNode(BaseNode):
            @property
            def name(self) -> str:
                return "temp_node"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {}

        assert NodeRegistry.is_registered("temp_node")

        NodeRegistry.clear()

        assert not NodeRegistry.is_registered("temp_node")
        assert NodeRegistry.list_nodes() == []

    def test_is_registered_true(self):
        """Test is_registered returns True for registered nodes."""

        @NodeRegistry.register("check_node")
        class CheckNode(BaseNode):
            @property
            def name(self) -> str:
                return "check_node"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {}

        assert NodeRegistry.is_registered("check_node") is True

    def test_is_registered_false(self):
        """Test is_registered returns False for unregistered nodes."""
        assert NodeRegistry.is_registered("nonexistent") is False

    def test_duplicate_registration_raises_error(self):
        """Test that registering the same name twice raises error."""

        @NodeRegistry.register("duplicate")
        class FirstNode(BaseNode):
            @property
            def name(self) -> str:
                return "duplicate"

            async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                return {}

        with pytest.raises(ValueError, match="Node 'duplicate' is already registered"):

            @NodeRegistry.register("duplicate")
            class SecondNode(BaseNode):
                @property
                def name(self) -> str:
                    return "duplicate"

                async def execute(self, state: ArticleWorkflowState) -> dict[str, Any]:
                    return {}
