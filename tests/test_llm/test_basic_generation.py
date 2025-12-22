"""Tests for LLM client basic text generation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.llm_client import LLMRetryExhausted, generate_text
from src.utils.config import reset_settings


@pytest.fixture(autouse=True)
def reset_config():
    """Reset configuration before each test."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def mock_litellm_response():
    """Create a mock LiteLLM response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Generated text from LLM"
    return response


@pytest.fixture
def env_vars_gemini(monkeypatch):
    """Set up environment variables for Gemini provider."""
    monkeypatch.setenv("APP_NAME", "test-app")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "test-gemini-key")
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "gemini-1.5-flash")
    monkeypatch.setenv("LLM_MAX_RETRIES", "3")
    monkeypatch.setenv("LLM_RETRY_DELAY", "0.1")  # Fast retries for tests


@pytest.fixture
def env_vars_openai(monkeypatch):
    """Set up environment variables for OpenAI provider."""
    monkeypatch.setenv("APP_NAME", "test-app")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "test-openai-key")
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "gpt-4")
    monkeypatch.setenv("LLM_MAX_RETRIES", "3")
    monkeypatch.setenv("LLM_RETRY_DELAY", "0.1")


class TestBasicGeneration:
    """Test basic text generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_text_returns_string(
        self, env_vars_gemini, mock_litellm_response
    ):
        """Test that generate_text returns non-empty string."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            result = await generate_text("Test prompt")

            assert isinstance(result, str)
            assert len(result) > 0
            assert result == "Generated text from LLM"
            mock_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_provider_switching_via_env_gemini(
        self, env_vars_gemini, mock_litellm_response
    ):
        """Test Gemini provider selection from environment."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt")

            # Verify provider was passed correctly
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["custom_llm_provider"] == "gemini"
            assert call_kwargs["model"] == "gemini-1.5-flash"
            assert call_kwargs["api_key"] == "test-gemini-key"

    @pytest.mark.asyncio
    async def test_provider_switching_via_env_openai(
        self, env_vars_openai, mock_litellm_response
    ):
        """Test OpenAI provider selection from environment."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt")

            # Verify provider was passed correctly
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["custom_llm_provider"] == "openai"
            assert call_kwargs["model"] == "gpt-4"
            assert call_kwargs["api_key"] == "test-openai-key"

    @pytest.mark.asyncio
    async def test_retries_on_transient_failure(
        self, env_vars_gemini, mock_litellm_response
    ):
        """Test retry logic on temporary failures."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            # Fail twice, succeed on third attempt
            mock_completion.side_effect = [
                ConnectionError("Network error"),
                TimeoutError("Request timeout"),
                mock_litellm_response,
            ]

            result = await generate_text("Test prompt")

            assert result == "Generated text from LLM"
            # Should be called 3 times (2 failures + 1 success)
            assert mock_completion.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_exception_after_max_retries(self, env_vars_gemini):
        """Test that LLMRetryExhausted is raised after all retries fail."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            # Always fail with a retryable error
            mock_completion.side_effect = ConnectionError("Network error")

            with pytest.raises(LLMRetryExhausted) as exc_info:
                await generate_text("Test prompt")

            assert "All 3 retries failed" in str(exc_info.value)
            # Should be called 4 times (1 initial + 3 retries)
            assert mock_completion.call_count == 4

    @pytest.mark.asyncio
    async def test_uses_custom_model_when_provided(
        self, env_vars_gemini, mock_litellm_response
    ):
        """Test model override parameter."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt", model="gemini-1.5-pro")

            # Verify custom model was used
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["model"] == "gemini-1.5-pro"

    @pytest.mark.asyncio
    async def test_respects_temperature_parameter(
        self, env_vars_gemini, mock_litellm_response
    ):
        """Test temperature parameter is passed correctly."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt", temperature=0.8)

            # Verify temperature was passed
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["temperature"] == 0.8

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises_immediately(self, env_vars_gemini):
        """Test that non-retryable errors raise immediately without retries."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            # Authentication error (non-retryable)
            mock_completion.side_effect = Exception("Authentication failed: 401")

            with pytest.raises(LLMRetryExhausted) as exc_info:
                await generate_text("Test prompt")

            assert "Non-retryable error" in str(exc_info.value)
            # Should be called only once (no retries)
            assert mock_completion.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_prompt_raises_error(self, env_vars_gemini):
        """Test that empty prompt raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await generate_text("")

        assert "Prompt cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_temperature_raises_error(self, env_vars_gemini):
        """Test that invalid temperature raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await generate_text("Test prompt", temperature=3.0)

        assert "Temperature must be between" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, env_vars_gemini, mock_litellm_response):
        """Test that retry delays follow exponential backoff."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                # Fail twice, succeed on third
                mock_completion.side_effect = [
                    ConnectionError("Network error"),
                    ConnectionError("Network error"),
                    mock_litellm_response,
                ]

                await generate_text("Test prompt")

                # Verify exponential backoff: 0.1 * (2^0), 0.1 * (2^1)
                assert mock_sleep.call_count == 2
                delays = [call.args[0] for call in mock_sleep.call_args_list]
                assert delays[0] == 0.1  # 0.1 * (2^0)
                assert delays[1] == 0.2  # 0.1 * (2^1)

    @pytest.mark.asyncio
    async def test_rate_limit_error_is_retryable(
        self, env_vars_gemini, mock_litellm_response
    ):
        """Test that rate limit errors trigger retries."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            # Rate limit error, then success
            mock_completion.side_effect = [
                Exception("Rate limit exceeded"),
                mock_litellm_response,
            ]

            result = await generate_text("Test prompt")

            assert result == "Generated text from LLM"
            assert mock_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_server_error_is_retryable(
        self, env_vars_gemini, mock_litellm_response
    ):
        """Test that 5xx server errors trigger retries."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            # Server error, then success
            mock_completion.side_effect = [
                Exception("Server error: 503"),
                mock_litellm_response,
            ]

            result = await generate_text("Test prompt")

            assert result == "Generated text from LLM"
            assert mock_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_passes_correct_message_format(
        self, env_vars_gemini, mock_litellm_response
    ):
        """Test that prompt is formatted correctly in messages."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt")

            # Verify message format
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["messages"] == [
                {"role": "user", "content": "Test prompt"}
            ]

    @pytest.mark.asyncio
    async def test_timeout_configuration(
        self, env_vars_gemini, mock_litellm_response, monkeypatch
    ):
        """Test that timeout is configured correctly."""
        monkeypatch.setenv("LLM_TIMEOUT", "60")
        reset_settings()  # Reset to pick up new timeout

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt")

            # Verify timeout was passed
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["timeout"] == 60


class TestCustomEndpoint:
    """Test custom LLM endpoint functionality."""

    @pytest.mark.asyncio
    async def test_custom_endpoint_takes_priority(
        self, monkeypatch, mock_litellm_response
    ):
        """Test that custom endpoint overrides provider config."""
        # Set up both provider and custom endpoint
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "test-gemini-key")
        monkeypatch.setenv("LLM_DEFAULT_MODEL", "gemini-1.5-flash")
        monkeypatch.setenv("CUSTOM_LLM_BASE_URL", "http://localhost:11434/v1")
        monkeypatch.setenv("CUSTOM_LLM_MODEL", "llama2")

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt")

            # Verify custom endpoint was used
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["base_url"] == "http://localhost:11434/v1"
            assert call_kwargs["model"] == "llama2"
            assert call_kwargs["custom_llm_provider"] is None  # Auto-detect

    @pytest.mark.asyncio
    async def test_custom_endpoint_with_api_key(
        self, monkeypatch, mock_litellm_response
    ):
        """Test custom endpoint with API key."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "test-gemini-key")
        monkeypatch.setenv("CUSTOM_LLM_BASE_URL", "http://remote-server:8000/v1")
        monkeypatch.setenv("CUSTOM_LLM_API_KEY", "custom-api-key")
        monkeypatch.setenv("CUSTOM_LLM_MODEL", "custom-model")

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt")

            # Verify custom API key was used
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["api_key"] == "custom-api-key"
            assert call_kwargs["base_url"] == "http://remote-server:8000/v1"

    @pytest.mark.asyncio
    async def test_custom_endpoint_model_override(
        self, monkeypatch, mock_litellm_response
    ):
        """Test that function parameter overrides CUSTOM_LLM_MODEL."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "test-gemini-key")
        monkeypatch.setenv("CUSTOM_LLM_BASE_URL", "http://localhost:11434/v1")
        monkeypatch.setenv("CUSTOM_LLM_MODEL", "llama2")

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            # Override with function parameter
            await generate_text("Test prompt", model="mistral")

            # Verify override was used
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["model"] == "mistral"
            assert call_kwargs["base_url"] == "http://localhost:11434/v1"

    @pytest.mark.asyncio
    async def test_fallback_to_provider_when_no_custom_url(
        self, env_vars_gemini, mock_litellm_response
    ):
        """Test fallback to provider when no custom URL set."""
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt")

            # Verify provider config was used
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["base_url"] is None
            assert call_kwargs["custom_llm_provider"] == "gemini"
            assert call_kwargs["api_key"] == "test-gemini-key"

    @pytest.mark.asyncio
    async def test_custom_endpoint_without_api_key(
        self, monkeypatch, mock_litellm_response
    ):
        """Test custom endpoint without API key (e.g., local Ollama)."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "test-gemini-key")
        monkeypatch.setenv("CUSTOM_LLM_BASE_URL", "http://localhost:11434/v1")
        monkeypatch.setenv("CUSTOM_LLM_MODEL", "llama2")
        # No CUSTOM_LLM_API_KEY set

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt")

            # Verify no API key was passed
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["api_key"] is None
            assert call_kwargs["base_url"] == "http://localhost:11434/v1"

    @pytest.mark.asyncio
    async def test_custom_endpoint_uses_default_model_if_no_custom_model(
        self, monkeypatch, mock_litellm_response
    ):
        """Test that LLM_DEFAULT_MODEL is used if CUSTOM_LLM_MODEL not set."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("LLM_API_KEY", "test-gemini-key")
        monkeypatch.setenv("LLM_DEFAULT_MODEL", "default-model")
        monkeypatch.setenv("CUSTOM_LLM_BASE_URL", "http://localhost:11434/v1")
        # No CUSTOM_LLM_MODEL set

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_litellm_response

            await generate_text("Test prompt")

            # Verify default model was used
            call_kwargs = mock_completion.call_args.kwargs
            assert call_kwargs["model"] == "default-model"
            assert call_kwargs["base_url"] == "http://localhost:11434/v1"
