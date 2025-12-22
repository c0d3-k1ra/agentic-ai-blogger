"""Tests for logging configuration."""

import json
import logging

import pytest

from src.utils.config import reset_settings
from src.utils.logging_config import (
    JsonFormatter,
    StandardFormatter,
    get_logger,
    reset_logging,
    setup_logging,
)


class TestLoggingSetup:
    """Test logging setup and configuration."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        reset_logging()
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_logging()
        reset_settings()

    def test_setup_logging_configures_root_logger(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that setup_logging configures the root logger."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

        # Check our StreamHandler was added (pytest may have its own handlers)
        stream_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and h.stream == logging.sys.stdout
        ]
        assert len(stream_handlers) == 1

    def test_setup_logging_prevents_duplicate_handlers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that calling setup_logging multiple times doesn't create duplicate handlers."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")

        # Call setup multiple times
        setup_logging()
        setup_logging()
        setup_logging()

        root_logger = logging.getLogger()
        # Should only have 1 StreamHandler to stdout, not 3
        stream_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and h.stream == logging.sys.stdout
        ]
        assert len(stream_handlers) == 1

    def test_setup_logging_with_force_reconfigure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that force_reconfigure allows reconfiguration."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        setup_logging()

        # Change log level
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        reset_settings()

        # Force reconfigure
        setup_logging(force_reconfigure=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        # Check we still have only 1 StreamHandler to stdout
        stream_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and h.stream == logging.sys.stdout
        ]
        assert len(stream_handlers) == 1


class TestLogLevels:
    """Test that LOG_LEVEL is respected."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        reset_logging()
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_logging()
        reset_settings()

    def test_info_level_filters_debug_messages(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that DEBUG messages are filtered when LOG_LEVEL is INFO."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        # Set caplog level before setup_logging
        caplog.set_level(logging.DEBUG)
        setup_logging()
        logger = get_logger("test")

        logger.debug("This should not appear")
        logger.info("This should appear")
        logger.warning("This should also appear")

        # Debug message should not be in logs
        messages = [record.message for record in caplog.records]
        assert "This should not appear" not in messages
        assert "This should appear" in messages
        assert "This should also appear" in messages

    def test_debug_level_shows_all_messages(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that all messages appear when LOG_LEVEL is DEBUG."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        caplog.set_level(logging.DEBUG)
        setup_logging()
        logger = get_logger("test")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

        messages = [record.message for record in caplog.records]
        assert "Debug message" in messages
        assert "Info message" in messages
        assert "Warning message" in messages

    def test_warning_level_filters_info_and_debug(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that INFO and DEBUG messages are filtered when LOG_LEVEL is WARNING."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        caplog.set_level(logging.DEBUG)
        setup_logging()
        logger = get_logger("test")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        messages = [record.message for record in caplog.records]
        assert "Debug message" not in messages
        assert "Info message" not in messages
        assert "Warning message" in messages
        assert "Error message" in messages


class TestLogFormatters:
    """Test different log formatters."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        reset_logging()
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_logging()
        reset_settings()

    def test_standard_formatter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test standard text formatter produces expected format."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")

        formatter = StandardFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Check format components are present
        assert "INFO" in formatted
        assert "test.module" in formatted
        assert "Test message" in formatted
        assert "[" in formatted  # Timestamp brackets

    def test_json_formatter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test JSON formatter produces valid JSON with expected fields."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")

        formatter = JsonFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Should be valid JSON
        log_data = json.loads(formatted)

        # Check required fields
        assert log_data["level"] == "INFO"
        assert log_data["name"] == "test.module"
        assert log_data["message"] == "Test message"
        assert log_data["app_name"] == "test-app"
        assert log_data["environment"] == "development"
        assert "timestamp" in log_data

    def test_json_formatter_with_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test JSON formatter includes exception info when present."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")

        formatter = JsonFormatter()

        # Create exception info
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        # Create a log record with exception
        record = logging.LogRecord(
            name="test.module",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert "exception" in log_data
        assert "ValueError: Test error" in log_data["exception"]


class TestGetLogger:
    """Test get_logger function."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        reset_logging()
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_logging()
        reset_settings()

    def test_get_logger_returns_logger_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that get_logger returns a logger instance."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")

        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_configures_logging_if_needed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that get_logger sets up logging if not already configured."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")

        # Don't call setup_logging explicitly
        get_logger("test.module")

        # Logging should be configured
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

    def test_get_logger_same_name_returns_same_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that getting logger with same name returns same instance."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")

        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")

        assert logger1 is logger2


class TestNoDuplicateLogs:
    """Test that logs are not duplicated."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        reset_logging()
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_logging()
        reset_settings()

    def test_single_log_message_not_duplicated(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that a single log message appears only once."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        caplog.set_level(logging.INFO)
        setup_logging()
        logger = get_logger("test")

        logger.info("Unique message")

        # Count how many times the message appears
        count = sum(1 for record in caplog.records if record.message == "Unique message")
        assert count == 1

    def test_multiple_setup_calls_no_duplicate_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that multiple setup_logging calls don't cause duplicate logs."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        caplog.set_level(logging.INFO)

        # Call setup multiple times (should not add duplicate handlers)
        setup_logging()
        setup_logging()
        setup_logging()

        logger = get_logger("test")
        logger.info("Test message")

        # Should only appear once
        count = sum(1 for record in caplog.records if record.message == "Test message")
        assert count == 1
