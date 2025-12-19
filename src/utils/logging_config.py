"""Structured logging configuration."""

import json
import logging
import sys
from typing import Any

from src.utils.config import get_settings


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON string with log data
        """
        settings = get_settings()
        
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class StandardFormatter(logging.Formatter):
    """Standard text formatter with consistent format."""
    
    def __init__(self) -> None:
        """Initialize with standard format."""
        fmt = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt=fmt, datefmt=datefmt)


# Track if logging has been configured
_logging_configured = False


def setup_logging(use_json: bool = False, force_reconfigure: bool = False) -> None:
    """
    Configure application logging.
    
    Sets up console logging with the LOG_LEVEL from settings.
    Prevents duplicate handlers by checking if already configured.
    
    Args:
        use_json: If True, use JSON format. If False, use standard text format.
        force_reconfigure: If True, force reconfiguration even if already set up.
    """
    global _logging_configured
    
    # Skip if already configured (unless forced)
    if _logging_configured and not force_reconfigure:
        return
    
    settings = get_settings()
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Remove only our own StreamHandler to prevent duplicates
    # Preserve other handlers (like pytest's caplog handler)
    handlers_to_remove = [
        h for h in root_logger.handlers 
        if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout
    ]
    for handler in handlers_to_remove:
        root_logger.removeHandler(handler)
    
    # Set log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL)
    root_logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Set formatter based on preference
    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = StandardFormatter()
    
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Mark as configured
    _logging_configured = True
    
    # Log that logging is configured
    logger = logging.getLogger(__name__)
    logger.debug(
        f"Logging configured: level={settings.LOG_LEVEL}, "
        f"format={'json' if use_json else 'standard'}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Ensures logging is set up before returning the logger.
    
    Args:
        name: Name for the logger (typically __name__ from calling module)
        
    Returns:
        Logger instance
    """
    # Ensure logging is configured
    if not _logging_configured:
        setup_logging()
    
    return logging.getLogger(name)


def reset_logging() -> None:
    """
    Reset logging configuration.
    
    Useful for testing to clear state between tests.
    """
    global _logging_configured
    
    # Clear all handlers from root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)  # Reset to default
    
    # Mark as not configured
    _logging_configured = False
