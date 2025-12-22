"""Unified LLM client for text generation using LiteLLM.

This module provides a single, reliable async interface for generating text
using LiteLLM, with Gemini as the default provider and optional OpenAI support.

Public API:
    generate_text: Generate text from a prompt using configured LLM provider
    LLMRetryExhausted: Exception raised when retries are exhausted

Example:
    >>> text = await generate_text("Write a short poem about Python")
    >>> print(text)
"""

import asyncio

import litellm

from src.utils.config import get_settings
from src.utils.logging_config import get_logger


def _get_logger():
    """Get logger instance lazily to avoid module-level import issues."""
    return get_logger(__name__)


class LLMRetryExhausted(Exception):
    """Raised when all retry attempts are exhausted or error is non-retryable.

    This exception is raised when:
    1. All retry attempts fail (total attempts = 1 + LLM_MAX_RETRIES)
    2. A non-retryable error occurs (e.g., authentication error)

    The original exception is attached as the cause via exception chaining.
    """


def _is_retryable_error(error: Exception) -> bool:
    """Determine if an error should trigger a retry.

    Args:
        error: The exception that occurred

    Returns:
        True if the error is retryable, False otherwise
    """
    # Retryable errors: network, rate limit, server errors (5xx)
    retryable_types = (
        ConnectionError,
        TimeoutError,
        OSError,  # Network-related errors
    )

    # Check exception type
    if isinstance(error, retryable_types):
        return True

    # Check for LiteLLM-specific errors
    error_str = str(error).lower()
    if any(
        keyword in error_str
        for keyword in [
            "rate limit",
            "timeout",
            "connection",
            "server error",
            "500",
            "502",
            "503",
            "504",
        ]
    ):
        return True

    # Non-retryable: authentication, invalid request, etc.
    if any(
        keyword in error_str
        for keyword in [
            "authentication",
            "invalid api key",
            "unauthorized",
            "401",
            "403",
            "invalid request",
            "400",
        ]
    ):
        return False

    # Default: retry on unknown errors
    return True


def _get_llm_config(model_override: str | None) -> dict:
    """Get LLM configuration based on priority: custom endpoint > hosted provider.

    Args:
        model_override: Optional model override (plain ID or with provider prefix)

    Returns:
        dict: Configuration with keys:
            - model: Model ID (may include provider prefix like vertex_ai/model-name)
            - base_url: Custom endpoint URL or None
            - api_key: API key to use
            - provider: Provider name or None (None lets LiteLLM auto-detect from model prefix)
    """
    settings = get_settings()

    # Priority 1: Custom endpoint (if CUSTOM_LLM_BASE_URL is set)
    if settings.CUSTOM_LLM_BASE_URL:
        return {
            "model": model_override or settings.CUSTOM_LLM_MODEL or settings.LLM_DEFAULT_MODEL,
            "base_url": settings.CUSTOM_LLM_BASE_URL,
            "api_key": settings.get_custom_llm_api_key(),
            "provider": "openai",  # Treat all custom endpoints as OpenAI-compatible
        }

    # Priority 2: Hosted provider (gemini/openai)
    return {
        "model": model_override or settings.LLM_DEFAULT_MODEL,
        "base_url": None,
        "api_key": settings.get_llm_api_key(),
        "provider": settings.LLM_PROVIDER,
    }


async def _call_llm_with_retry(  # pylint: disable=too-many-locals
    prompt: str,
    config: dict,
    temperature: float,
) -> str:
    """Call LLM with retry logic and exponential backoff.

    Args:
        prompt: Text prompt to send to LLM
        config: LLM configuration dict from _get_llm_config
        temperature: Sampling temperature

    Returns:
        Generated text

    Raises:
        LLMRetryExhausted: When retries are exhausted or error is non-retryable
    """
    settings = get_settings()
    logger = _get_logger()
    max_retries = settings.LLM_MAX_RETRIES

    # Extract config values
    model = config["model"]
    base_url = config["base_url"]
    api_key = config["api_key"]
    provider = config["provider"]

    # Determine provider for logging (custom endpoint or hosted)
    provider_name = "custom" if base_url else provider

    # Total attempts = 1 initial + max_retries
    for attempt in range(max_retries + 1):
        try:
            logger.debug(
                "LLM attempt %d/%d",
                attempt + 1,
                max_retries + 1,
                extra={
                    "extra_fields": {
                        "provider": provider_name,
                        "model": model,
                        "temperature": temperature,
                        "base_url": base_url if base_url else "default",
                    }
                },
            )

            # Call LiteLLM with configuration
            response = await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                api_key=api_key,
                base_url=base_url,
                timeout=settings.LLM_TIMEOUT,
                custom_llm_provider=provider,
            )

            # Extract generated text
            generated_text = response.choices[0].message.content

            # Log success at INFO level
            logger.info(
                "LLM request successful",
                extra={
                    "extra_fields": {
                        "provider": provider_name,
                        "model": model,
                        "attempts": attempt + 1,
                    }
                },
            )

            return generated_text

        except Exception as e:
            # Log error details at DEBUG level
            logger.debug("LLM error on attempt %d: %s: %s", attempt + 1, type(e).__name__, str(e))

            # Check if error is retryable
            if not _is_retryable_error(e):
                logger.error(
                    "LLM non-retryable error",
                    extra={
                        "extra_fields": {
                            "provider": provider_name,
                            "model": model,
                            "error_type": type(e).__name__,
                        }
                    },
                )
                raise LLMRetryExhausted(f"Non-retryable error: {type(e).__name__}") from e

            # Check if we've exhausted retries
            if attempt == max_retries:
                logger.error(
                    "LLM retries exhausted: %s: %s",
                    type(e).__name__,
                    str(e),
                    extra={
                        "extra_fields": {
                            "provider": provider_name,
                            "model": model,
                            "attempts": attempt + 1,
                            "error_type": type(e).__name__,
                        }
                    },
                )
                raise LLMRetryExhausted(
                    f"All {max_retries} retries failed: {type(e).__name__}: {str(e)}"
                ) from e

            # Calculate exponential backoff delay
            delay = settings.LLM_RETRY_DELAY * (2**attempt)
            logger.debug("Retrying in %ss (attempt %d/%d)", delay, attempt + 2, max_retries + 1)
            await asyncio.sleep(delay)

    # This should never be reached due to the loop logic
    raise LLMRetryExhausted("Unexpected retry loop exit")


async def generate_text(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    """Generate text using configured LLM provider.

    This is the public API for text generation. It provides a simple, reliable
    interface for generating text using LiteLLM with automatic retry logic.

    Args:
        prompt: Plain text prompt to send to the LLM
        model: Optional model override (plain ID like 'gpt-4', 'gemini-2.5-flash').
               If not provided, uses LLM_DEFAULT_MODEL or CUSTOM_LLM_MODEL from config.
        temperature: Sampling temperature for generation (default: 0.2).
                    Lower values are more deterministic, higher more creative.

    Returns:
        Generated text as a string

    Raises:
        LLMRetryExhausted: When all retry attempts fail or error is non-retryable

    Example:
        >>> text = await generate_text("Write a haiku about coding")
        >>> print(text)

    Notes:
        - Supports both hosted providers (Gemini/OpenAI) and custom endpoints (Ollama/LM Studio)
        - Priority: CUSTOM_LLM_BASE_URL > LLM_PROVIDER
        - Model IDs should be plain (no provider prefix)
        - Retry behavior: exponential backoff with max retries from config
        - Total attempts = 1 initial + LLM_MAX_RETRIES
        - Logs provider, model, and attempt count (never prompt or generated text)
    """
    # Validate inputs
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    if not 0.0 <= temperature <= 2.0:
        raise ValueError("Temperature must be between 0.0 and 2.0")

    # Get LLM configuration (handles provider priority and model selection)
    config = _get_llm_config(model)

    # Call LLM with retry logic
    return await _call_llm_with_retry(
        prompt=prompt,
        config=config,
        temperature=temperature,
    )
