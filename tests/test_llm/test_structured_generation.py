"""Tests for structured output generation using Pydantic schemas.

This module tests the generate_structured function, which provides strict,
deterministic structured output generation with JSON validation and schema enforcement.
"""

import json
from unittest.mock import patch

import pytest
from pydantic import BaseModel, ConfigDict

from src.integrations.llm_client import LLMRetryExhausted, generate_structured
from src.utils.config import reset_settings


@pytest.fixture(autouse=True)
def reset_config():
    """Reset configuration before each test."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def env_vars_test(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("APP_NAME", "test-app")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "gemini-1.5-flash")
    monkeypatch.setenv("LLM_MAX_RETRIES", "3")
    monkeypatch.setenv("LLM_RETRY_DELAY", "0.1")
    monkeypatch.delenv("CUSTOM_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("CUSTOM_LLM_API_KEY", raising=False)
    monkeypatch.delenv("CUSTOM_LLM_MODEL", raising=False)
    reset_settings()


# Test schemas
class SimplePerson(BaseModel):
    """Simple schema for testing basic functionality."""

    name: str
    age: int


class ArticleSummary(BaseModel):
    """Schema with multiple field types."""

    title: str
    summary: str
    tags: list[str]
    word_count: int


class StrictSchema(BaseModel):
    """Schema that forbids extra fields."""

    model_config = ConfigDict(extra="forbid")

    required_field: str
    optional_field: str | None = None


class TestBasicStructuredGeneration:
    """Test basic structured generation functionality."""

    @pytest.mark.asyncio
    async def test_valid_json_returns_schema_instance(self, env_vars_test):
        """Valid JSON matching schema returns validated instance."""
        valid_json = '{"name": "Alice", "age": 30}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = valid_json

            result = await generate_structured(
                "Extract person info",
                schema=SimplePerson,
            )

            assert isinstance(result, SimplePerson)
            assert result.name == "Alice"
            assert result.age == 30
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_temperature_defaults_to_zero(self, env_vars_test):
        """Temperature defaults to 0.0 for deterministic output."""
        valid_json = '{"name": "Bob", "age": 25}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = valid_json

            await generate_structured(
                "Extract person info",
                schema=SimplePerson,
            )

            # Check that temperature=0.0 was passed
            call_kwargs = mock_llm.call_args
            assert call_kwargs.kwargs["temperature"] == 0.0

    @pytest.mark.asyncio
    async def test_custom_model_override_respected(self, env_vars_test):
        """Custom model parameter is passed through correctly."""
        valid_json = '{"name": "Charlie", "age": 35}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = valid_json

            await generate_structured(
                "Extract person info",
                schema=SimplePerson,
                model="gpt-4",
            )

            # Check that config was created with custom model
            call_kwargs = mock_llm.call_args
            config = call_kwargs.kwargs["config"]
            assert config["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_complex_schema_validation(self, env_vars_test):
        """Complex schema with multiple field types validates correctly."""
        valid_json = json.dumps(
            {
                "title": "Python Tips",
                "summary": "A collection of Python best practices",
                "tags": ["python", "programming", "tips"],
                "word_count": 500,
            }
        )

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = valid_json

            result = await generate_structured(
                "Write article summary",
                schema=ArticleSummary,
            )

            assert isinstance(result, ArticleSummary)
            assert result.title == "Python Tips"
            assert result.word_count == 500
            assert len(result.tags) == 3
            assert "python" in result.tags


class TestRetryBehavior:
    """Test retry logic for JSON parsing and schema validation errors."""

    @pytest.mark.asyncio
    async def test_invalid_json_triggers_retry_then_success(self, env_vars_test):
        """Invalid JSON on first attempt triggers retry, then succeeds."""
        invalid_json = "This is not JSON"
        valid_json = '{"name": "David", "age": 40}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            # First call returns invalid JSON, second returns valid
            mock_llm.side_effect = [invalid_json, valid_json]

            result = await generate_structured(
                "Extract person info",
                schema=SimplePerson,
            )

            assert isinstance(result, SimplePerson)
            assert result.name == "David"
            assert mock_llm.call_count == 2

    @pytest.mark.asyncio
    async def test_schema_validation_failure_triggers_retry(self, env_vars_test):
        """Schema validation failure triggers retry."""
        # Missing required 'age' field
        invalid_schema_json = '{"name": "Eve"}'
        valid_json = '{"name": "Eve", "age": 28}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.side_effect = [invalid_schema_json, valid_json]

            result = await generate_structured(
                "Extract person info",
                schema=SimplePerson,
            )

            assert isinstance(result, SimplePerson)
            assert result.name == "Eve"
            assert result.age == 28
            assert mock_llm.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_exhausted_on_json_error(self, env_vars_test):
        """Retries exhausted on persistent JSON parsing errors."""
        invalid_json = "Not JSON at all"

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            # Always return invalid JSON
            mock_llm.return_value = invalid_json

            with pytest.raises(LLMRetryExhausted) as exc_info:
                await generate_structured(
                    "Extract person info",
                    schema=SimplePerson,
                )

            assert "Invalid JSON" in str(exc_info.value)
            # Should retry max_retries times (default 3 in tests)
            assert mock_llm.call_count == 4  # 1 initial + 3 retries

    @pytest.mark.asyncio
    async def test_retries_exhausted_on_validation_error(self, env_vars_test):
        """Retries exhausted on persistent schema validation errors."""
        # Missing required 'age' field every time
        invalid_json = '{"name": "Frank"}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = invalid_json

            with pytest.raises(LLMRetryExhausted) as exc_info:
                await generate_structured(
                    "Extract person info",
                    schema=SimplePerson,
                )

            assert "Schema validation failed" in str(exc_info.value)
            assert mock_llm.call_count == 4  # 1 initial + 3 retries

    @pytest.mark.asyncio
    async def test_llm_retry_exhausted_propagates(self, env_vars_test):
        """LLM-level retry exhausted exception propagates correctly."""
        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            # Simulate LLM retry exhausted
            mock_llm.side_effect = LLMRetryExhausted("API error")

            with pytest.raises(LLMRetryExhausted) as exc_info:
                await generate_structured(
                    "Extract person info",
                    schema=SimplePerson,
                )

            assert "API error" in str(exc_info.value)
            mock_llm.assert_called_once()


class TestSchemaValidation:
    """Test strict schema validation behavior."""

    @pytest.mark.asyncio
    async def test_extra_fields_cause_validation_failure(self, env_vars_test):
        """Extra fields in JSON cause validation failure (Pydantic v2 default)."""
        # JSON with extra field 'email' not in schema
        json_with_extra = '{"required_field": "value", "extra_field": "not allowed"}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = json_with_extra

            with pytest.raises(LLMRetryExhausted) as exc_info:
                await generate_structured(
                    "Generate data",
                    schema=StrictSchema,
                )

            assert "Schema validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_required_fields_cause_failure(self, env_vars_test):
        """Missing required fields cause validation failure."""
        # Missing 'required_field'
        incomplete_json = '{"optional_field": "value"}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = incomplete_json

            with pytest.raises(LLMRetryExhausted) as exc_info:
                await generate_structured(
                    "Generate data",
                    schema=StrictSchema,
                )

            assert "Schema validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_type_mismatch_causes_failure(self, env_vars_test):
        """Type mismatch causes validation failure."""
        # 'age' should be int, not string
        wrong_type_json = '{"name": "Grace", "age": "thirty"}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = wrong_type_json

            with pytest.raises(LLMRetryExhausted) as exc_info:
                await generate_structured(
                    "Extract person info",
                    schema=SimplePerson,
                )

            assert "Schema validation failed" in str(exc_info.value)


class TestInputValidation:
    """Test input validation and error handling."""

    @pytest.mark.asyncio
    async def test_empty_prompt_raises_error(self, env_vars_test):
        """Empty prompt raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await generate_structured(
                "",
                schema=SimplePerson,
            )

        assert "Prompt cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_whitespace_only_prompt_raises_error(self, env_vars_test):
        """Whitespace-only prompt raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await generate_structured(
                "   \n\t  ",
                schema=SimplePerson,
            )

        assert "Prompt cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_schema_raises_error(self, env_vars_test):
        """Invalid schema argument raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await generate_structured(
                "Extract info",
                schema=dict,  # Not a BaseModel subclass
            )

        assert "must be a Pydantic BaseModel subclass" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_none_schema_raises_error(self, env_vars_test):
        """None schema raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await generate_structured(
                "Extract info",
                schema=None,  # type: ignore
            )

        assert "must be a Pydantic BaseModel subclass" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_temperature_out_of_range_raises_error(self, env_vars_test):
        """Temperature outside [0.0, 2.0] raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await generate_structured(
                "Extract info",
                schema=SimplePerson,
                temperature=3.0,
            )

        assert "Temperature must be between" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_negative_temperature_raises_error(self, env_vars_test):
        """Negative temperature raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await generate_structured(
                "Extract info",
                schema=SimplePerson,
                temperature=-0.1,
            )

        assert "Temperature must be between" in str(exc_info.value)


class TestPromptConstruction:
    """Test that prompts are constructed correctly."""

    @pytest.mark.asyncio
    async def test_prompt_includes_full_schema(self, env_vars_test):
        """Prompt includes full JSON schema."""
        valid_json = '{"name": "Henry", "age": 45}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = valid_json

            await generate_structured(
                "Extract person info",
                schema=SimplePerson,
            )

            # Check that prompt includes schema
            call_args = mock_llm.call_args
            prompt = call_args.kwargs["prompt"]

            assert "Schema:" in prompt
            assert "name" in prompt  # Field from schema
            assert "age" in prompt  # Field from schema
            assert "Extract person info" in prompt  # Original prompt

    @pytest.mark.asyncio
    async def test_prompt_instructs_json_only(self, env_vars_test):
        """Prompt explicitly instructs JSON-only output."""
        valid_json = '{"name": "Iris", "age": 50}'

        with patch("src.integrations.llm_client._call_llm_with_retry") as mock_llm:
            mock_llm.return_value = valid_json

            await generate_structured(
                "Extract person info",
                schema=SimplePerson,
            )

            # Check that prompt includes JSON-only instruction
            call_args = mock_llm.call_args
            prompt = call_args.kwargs["prompt"]

            assert "ONLY valid JSON" in prompt
            assert "No markdown" in prompt or "no markdown" in prompt
            assert "No explanations" in prompt or "no explanations" in prompt
