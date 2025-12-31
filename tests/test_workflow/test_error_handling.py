"""Tests for workflow error handling and recovery."""

import time

import pytest

from src.workflow.error_handling import (
    APIError,
    ErrorContext,
    FallbackRecovery,
    NodeExecutionError,
    RecoverableError,
    RetryRecovery,
    StateValidationError,
    UnrecoverableError,
    WorkflowError,
    handle_node_error,
    retry_with_backoff,
    validate_state_field,
)


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_workflow_error_basic(self):
        """Test basic WorkflowError creation."""
        error = WorkflowError("Test error")
        assert str(error) == "Test error"
        assert error.workflow_id is None

    def test_workflow_error_with_workflow_id(self):
        """Test WorkflowError with workflow ID."""
        error = WorkflowError("Test error", workflow_id="wf-123")
        assert str(error) == "[wf-123] Test error"
        assert error.workflow_id == "wf-123"

    def test_workflow_error_with_context(self):
        """Test WorkflowError with additional context."""
        error = WorkflowError("Test error", workflow_id="wf-123", step="scout", retry=2)
        assert error.context["step"] == "scout"
        assert error.context["retry"] == 2
        assert error.timestamp > 0

    def test_node_execution_error(self):
        """Test NodeExecutionError with node name."""
        error = NodeExecutionError("Node failed", node_name="scout_topics", workflow_id="wf-123")
        assert str(error) == "[wf-123] Node failed"
        assert error.node_name == "scout_topics"
        assert error.workflow_id == "wf-123"

    def test_api_error(self):
        """Test APIError with API details."""
        error = APIError(
            "API call failed", api_name="OpenAI", status_code=429, workflow_id="wf-123"
        )
        assert error.api_name == "OpenAI"
        assert error.status_code == 429
        assert error.workflow_id == "wf-123"

    def test_state_validation_error(self):
        """Test StateValidationError with field information."""
        error = StateValidationError("Field missing", field="user_query", workflow_id="wf-123")
        assert error.field == "user_query"
        assert error.workflow_id == "wf-123"

    def test_recoverable_error(self):
        """Test RecoverableError is subclass of WorkflowError."""
        error = RecoverableError("Recoverable issue", workflow_id="wf-123")
        assert isinstance(error, WorkflowError)
        assert isinstance(error, RecoverableError)

    def test_unrecoverable_error(self):
        """Test UnrecoverableError is subclass of WorkflowError."""
        error = UnrecoverableError("Unrecoverable issue", workflow_id="wf-123")
        assert isinstance(error, WorkflowError)
        assert isinstance(error, UnrecoverableError)


class TestRetryLogic:
    """Tests for retry with backoff decorator."""

    def test_retry_succeeds_first_attempt(self):
        """Test that successful function doesn't retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_succeeds_after_failures(self):
        """Test that function retries and eventually succeeds."""
        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausts_attempts(self):
        """Test that retry raises error after max attempts."""

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def always_fails():
            raise ValueError("Persistent failure")

        with pytest.raises(ValueError, match="Persistent failure"):
            always_fails()

    def test_retry_with_specific_exceptions(self):
        """Test retry only catches specified exceptions."""

        @retry_with_backoff(max_retries=2, initial_delay=0.01, exceptions=(ValueError,))
        def raises_type_error():
            raise TypeError("Not caught")

        with pytest.raises(TypeError, match="Not caught"):
            raises_type_error()

    def test_retry_backoff_timing(self):
        """Test that backoff delays increase exponentially."""
        call_times = []

        @retry_with_backoff(max_retries=3, initial_delay=0.1, backoff_factor=2.0)
        def timed_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Not yet")
            return "done"

        timed_func()

        # Check delays are roughly: 0.1s, 0.2s
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert 0.08 < delay1 < 0.15  # ~0.1s with tolerance

        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            assert 0.18 < delay2 < 0.25  # ~0.2s with tolerance


class TestErrorContext:
    """Tests for ErrorContext manager."""

    def test_error_context_success(self):
        """Test ErrorContext with successful operation."""
        with ErrorContext("test_operation", workflow_id="wf-123") as ctx:
            ctx.add_info("key", "value")
            assert ctx.operation == "test_operation"
            assert ctx.workflow_id == "wf-123"
            assert ctx.info["key"] == "value"

    def test_error_context_with_error(self):
        """Test ErrorContext captures error information."""
        with pytest.raises(ValueError):
            with ErrorContext("failing_operation", workflow_id="wf-123") as ctx:
                ctx.add_info("attempt", 1)
                raise ValueError("Test error")

    def test_error_context_timing(self):
        """Test ErrorContext tracks operation duration."""
        with ErrorContext("timed_operation") as ctx:
            time.sleep(0.05)
            assert ctx.start_time is not None

        # Duration should be at least 0.05s
        duration = time.time() - ctx.start_time
        assert duration >= 0.05

    def test_error_context_multiple_info(self):
        """Test ErrorContext can store multiple info items."""
        with ErrorContext("multi_info_op") as ctx:
            ctx.add_info("step", "initialization")
            ctx.add_info("count", 42)
            ctx.add_info("flag", True)

        assert len(ctx.info) == 3
        assert ctx.info["step"] == "initialization"
        assert ctx.info["count"] == 42
        assert ctx.info["flag"] is True


class TestRecoveryStrategies:
    """Tests for error recovery strategies."""

    def test_fallback_recovery_can_recover(self):
        """Test FallbackRecovery can recover from any error."""
        strategy = FallbackRecovery(fallback_value="default")
        assert strategy.can_recover(ValueError("any error"))
        assert strategy.can_recover(RuntimeError("any error"))

    def test_fallback_recovery_returns_value(self):
        """Test FallbackRecovery returns configured value."""
        strategy = FallbackRecovery(fallback_value="fallback")
        result = strategy.recover(ValueError("error"), {})
        assert result == "fallback"

    def test_fallback_recovery_with_none(self):
        """Test FallbackRecovery with None value."""
        strategy = FallbackRecovery(fallback_value=None)
        result = strategy.recover(ValueError("error"), {})
        assert result is None

    def test_retry_recovery_can_recover_from_recoverable(self):
        """Test RetryRecovery can recover from RecoverableError."""
        strategy = RetryRecovery(max_attempts=3)
        assert strategy.can_recover(RecoverableError("recoverable"))
        assert strategy.can_recover(ValueError("standard error"))

    def test_retry_recovery_cannot_recover_from_unrecoverable(self):
        """Test RetryRecovery cannot recover from UnrecoverableError."""
        strategy = RetryRecovery(max_attempts=3)
        assert not strategy.can_recover(UnrecoverableError("fatal"))

    def test_retry_recovery_succeeds(self):
        """Test RetryRecovery successfully retries operation."""
        attempt = 0

        def operation():
            nonlocal attempt
            attempt += 1
            if attempt < 2:
                raise ValueError("Not yet")
            return "success"

        strategy = RetryRecovery(max_attempts=3, delay=0.01)
        result = strategy.recover(ValueError("initial"), {"operation": operation})
        assert result == "success"
        assert attempt == 2

    def test_retry_recovery_exhausts_attempts(self):
        """Test RetryRecovery raises after max attempts."""

        def always_fails():
            raise ValueError("Always fails")

        strategy = RetryRecovery(max_attempts=2, delay=0.01)
        with pytest.raises(ValueError, match="Always fails"):
            strategy.recover(ValueError("initial"), {"operation": always_fails})

    def test_retry_recovery_requires_operation(self):
        """Test RetryRecovery requires operation in context."""
        strategy = RetryRecovery(max_attempts=3)
        with pytest.raises(ValueError, match="operation"):
            strategy.recover(ValueError("error"), {})


class TestHandleNodeError:
    """Tests for handle_node_error decorator."""

    def test_handle_node_error_success(self):
        """Test decorator allows successful execution."""

        @handle_node_error("test_node")
        def successful_node(state):
            return {"result": "success"}

        result = successful_node({"workflow_id": "wf-123"})
        assert result["result"] == "success"

    def test_handle_node_error_wraps_exception(self):
        """Test decorator wraps exceptions as NodeExecutionError."""

        @handle_node_error("failing_node")
        def failing_node(state):
            raise ValueError("Node failed")

        with pytest.raises(NodeExecutionError) as exc_info:
            failing_node({"workflow_id": "wf-123"})

        error = exc_info.value
        assert error.node_name == "failing_node"
        assert "Node failed" in str(error)

    def test_handle_node_error_preserves_original(self):
        """Test decorator preserves original exception as cause."""

        @handle_node_error("error_node")
        def error_node(state):
            raise ValueError("Original error")

        with pytest.raises(NodeExecutionError) as exc_info:
            error_node({"workflow_id": "wf-123"})

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_handle_node_error_with_workflow_id(self):
        """Test decorator extracts workflow_id from state."""

        @handle_node_error("tracked_node")
        def tracked_node(state):
            raise ValueError("Tracked error")

        with pytest.raises(NodeExecutionError) as exc_info:
            tracked_node({"workflow_id": "wf-456"})

        assert exc_info.value.workflow_id == "wf-456"

    def test_handle_node_error_with_kwargs(self):
        """Test decorator works with kwargs."""

        @handle_node_error("kwarg_node")
        def kwarg_node(self, state):
            return {"status": "ok"}

        result = kwarg_node("self", state={"workflow_id": "wf-789"})
        assert result["status"] == "ok"


class TestStateValidation:
    """Tests for state validation helpers."""

    def test_validate_state_field_success(self):
        """Test validation passes for valid field."""
        state = {"user_query": "Python async", "workflow_id": "wf-123"}

        # Should not raise
        validate_state_field(state, "user_query", str, workflow_id="wf-123")

    def test_validate_state_field_missing(self):
        """Test validation fails for missing field."""
        state = {"workflow_id": "wf-123"}

        with pytest.raises(StateValidationError) as exc_info:
            validate_state_field(state, "user_query", str, workflow_id="wf-123")

        error = exc_info.value
        assert error.field == "user_query"
        assert "missing" in str(error).lower()

    def test_validate_state_field_wrong_type(self):
        """Test validation fails for wrong type."""
        state = {"revision_count": "not a number", "workflow_id": "wf-123"}

        with pytest.raises(StateValidationError) as exc_info:
            validate_state_field(state, "revision_count", int, workflow_id="wf-123")

        error = exc_info.value
        assert error.field == "revision_count"
        assert "type" in str(error).lower()

    def test_validate_state_field_various_types(self):
        """Test validation with different types."""
        state = {
            "string_field": "text",
            "int_field": 42,
            "bool_field": True,
            "list_field": [1, 2, 3],
            "dict_field": {"key": "value"},
        }

        # All should pass
        validate_state_field(state, "string_field", str)
        validate_state_field(state, "int_field", int)
        validate_state_field(state, "bool_field", bool)
        validate_state_field(state, "list_field", list)
        validate_state_field(state, "dict_field", dict)

    def test_validate_state_field_with_none(self):
        """Test validation handles None values."""
        state = {"optional_field": None}

        # This should fail because None is not str
        with pytest.raises(StateValidationError):
            validate_state_field(state, "optional_field", str)


class TestIntegration:
    """Integration tests combining multiple error handling features."""

    def test_retry_with_error_context(self):
        """Test retry decorator works with error context."""
        attempts = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def operation_with_context():
            nonlocal attempts
            with ErrorContext("attempt") as ctx:
                attempts += 1
                ctx.add_info("attempt_num", attempts)
                if attempts < 2:
                    raise ValueError("Not ready")
                return "done"

        result = operation_with_context()
        assert result == "done"
        assert attempts == 2

    def test_node_error_with_validation(self):
        """Test node error decorator with state validation."""

        @handle_node_error("validated_node")
        def validated_node(state):
            validate_state_field(state, "required_field", str, state.get("workflow_id"))
            return {"status": "processed"}

        # Should raise StateValidationError, wrapped in NodeExecutionError
        with pytest.raises(NodeExecutionError):
            validated_node({"workflow_id": "wf-123"})

    def test_recovery_with_multiple_strategies(self):
        """Test using multiple recovery strategies."""
        retry_strategy = RetryRecovery(max_attempts=2, delay=0.01)
        fallback_strategy = FallbackRecovery(fallback_value="fallback")

        # Try retry first
        error = RecoverableError("recoverable")
        assert retry_strategy.can_recover(error)

        # If retry exhausted, use fallback
        unrecoverable = UnrecoverableError("fatal")
        assert not retry_strategy.can_recover(unrecoverable)
        assert fallback_strategy.can_recover(unrecoverable)
        result = fallback_strategy.recover(unrecoverable, {})
        assert result == "fallback"
