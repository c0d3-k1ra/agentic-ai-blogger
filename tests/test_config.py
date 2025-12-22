"""Tests for environment configuration."""

import os
from typing import Any

import pytest
from pydantic import ValidationError

from src.utils.config import Settings, get_settings, reset_settings


class TestSettings:
    """Test the Settings class."""
    
    def test_valid_config_with_required_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that config loads successfully with required fields."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        settings = Settings()
        
        assert settings.APP_NAME == "test-app"
        assert settings.ENVIRONMENT == "development"
        assert settings.LOG_LEVEL == "INFO"  # Default
        assert settings.DEBUG is False  # Default
        assert settings.API_TIMEOUT == 30  # Default
    
    def test_missing_required_field_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing required fields raise explicit ValidationError."""
        # Only set one required field
        monkeypatch.setenv("APP_NAME", "test-app")
        # Missing ENVIRONMENT - explicitly delete it in case it's in .env
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)  # Disable .env file loading
        
        # Check that the error mentions the missing field
        error_str = str(exc_info.value)
        assert "ENVIRONMENT" in error_str
    
    def test_missing_all_required_fields_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing all required fields raises ValidationError."""
        # Clear any environment variables including those from .env
        monkeypatch.delenv("APP_NAME", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)  # Disable .env file loading
        
        error_str = str(exc_info.value)
        assert "APP_NAME" in error_str or "ENVIRONMENT" in error_str
    
    def test_optional_fields_have_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that optional fields use their default values."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        settings = Settings()
        
        # Check defaults
        assert settings.LOG_LEVEL == "INFO"
        assert settings.DEBUG is False
        assert settings.API_TIMEOUT == 30
        assert settings.API_KEY is None
        assert settings.SECRET_KEY is None
    
    def test_optional_fields_can_be_overridden(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that optional fields can be set via environment variables."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("API_TIMEOUT", "60")
        
        settings = Settings()
        
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.DEBUG is True
        assert settings.API_TIMEOUT == 60
    
    def test_secrets_are_masked_in_repr(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that secret values are masked in string representation."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("API_KEY", "super-secret-key")
        monkeypatch.setenv("SECRET_KEY", "another-secret")
        
        settings = Settings()
        settings_str = str(settings)
        settings_repr = repr(settings)
        
        # Secrets should not appear in plain text
        assert "super-secret-key" not in settings_str
        assert "another-secret" not in settings_str
        assert "super-secret-key" not in settings_repr
        assert "another-secret" not in settings_repr
        
        # But should contain masked indicators
        assert "**********" in settings_str or "SecretStr" in settings_str
    
    def test_secrets_can_be_retrieved_with_getters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that secret values can be retrieved using getter methods."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("API_KEY", "my-api-key")
        monkeypatch.setenv("SECRET_KEY", "my-secret")
        
        settings = Settings()
        
        assert settings.get_api_key() == "my-api-key"
        assert settings.get_secret_key() == "my-secret"
    
    def test_environment_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that ENVIRONMENT field only accepts valid values."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "invalid-env")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_str = str(exc_info.value)
        assert "ENVIRONMENT" in error_str
    
    def test_valid_environment_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that all valid environment values are accepted."""
        monkeypatch.setenv("APP_NAME", "test-app")
        
        valid_envs = ["development", "staging", "production"]
        
        for env in valid_envs:
            monkeypatch.setenv("ENVIRONMENT", env)
            settings = Settings()
            assert settings.ENVIRONMENT == env
    
    def test_log_level_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that LOG_LEVEL is validated and normalized to uppercase."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "debug")  # lowercase
        
        settings = Settings()
        
        assert settings.LOG_LEVEL == "DEBUG"  # Should be uppercase
    
    def test_invalid_log_level_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid log level raises ValidationError."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_str = str(exc_info.value)
        assert "LOG_LEVEL" in error_str
    
    def test_api_timeout_must_be_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that API_TIMEOUT must be greater than 0."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("API_TIMEOUT", "0")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_str = str(exc_info.value)
        assert "API_TIMEOUT" in error_str or "greater than 0" in error_str
    
    def test_extra_env_vars_are_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that extra environment variables are ignored."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("UNKNOWN_VAR", "should-be-ignored")
        
        settings = Settings()
        
        # Should not raise error
        assert settings.APP_NAME == "test-app"
        assert not hasattr(settings, "UNKNOWN_VAR")


class TestGetSettings:
    """Test the get_settings singleton function."""
    
    def setup_method(self) -> None:
        """Reset settings before each test."""
        reset_settings()
    
    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()
    
    def test_get_settings_returns_singleton(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that get_settings returns the same instance."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_reset_settings_clears_singleton(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that reset_settings clears the singleton."""
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        settings1 = get_settings()
        reset_settings()
        
        monkeypatch.setenv("APP_NAME", "different-app")
        settings2 = get_settings()
        
        assert settings1 is not settings2
        assert settings1.APP_NAME == "test-app"
        assert settings2.APP_NAME == "different-app"
    
    def test_get_settings_raises_error_on_missing_required_fields(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
        """Test that get_settings raises ValidationError when required fields are missing."""
        # Clear required fields including those from .env
        monkeypatch.delenv("APP_NAME", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        
        # Point to a non-existent .env file to prevent loading from actual .env
        fake_env = tmp_path / "fake.env"
        monkeypatch.chdir(tmp_path)
        
        with pytest.raises(ValidationError):
            get_settings()
