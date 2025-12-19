"""Example demonstrating the logging configuration."""

import os

from src.utils.config import reset_settings
from src.utils.logging_config import get_logger, setup_logging

# Set up environment for example
os.environ["APP_NAME"] = "tech-article-generator"
os.environ["ENVIRONMENT"] = "development"
os.environ["LOG_LEVEL"] = "DEBUG"

# Example 1: Standard text format logging
print("=== Example 1: Standard Text Format ===")
setup_logging(use_json=False, force_reconfigure=True)
logger = get_logger(__name__)

logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")

print("\n=== Example 2: JSON Format ===")
setup_logging(use_json=True, force_reconfigure=True)
logger = get_logger(__name__)

logger.info("Starting application")
logger.warning("Configuration value not set, using default")
logger.error("Failed to connect to service")

print("\n=== Example 3: LOG_LEVEL Filtering (WARNING) ===")
os.environ["LOG_LEVEL"] = "WARNING"


reset_settings()
setup_logging(use_json=False, force_reconfigure=True)
logger = get_logger(__name__)

print("(Debug and Info messages below will be filtered out)")
logger.debug("This won't appear")
logger.info("This won't appear either")
logger.warning("This will appear")
logger.error("This will also appear")
