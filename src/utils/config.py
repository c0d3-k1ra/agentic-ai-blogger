"""Type-safe environment configuration using Pydantic Settings."""

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    Required fields will raise validation errors if missing.
    Optional fields have sensible defaults.
    Secrets are masked in string representations.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields in .env
        env_ignore_empty=True,
    )
    
    # Required fields - will raise error if missing
    APP_NAME: str = Field(
        ...,
        description="Application name"
    )
    
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        ...,
        description="Application environment"
    )
    
    # Optional fields with defaults
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    DEBUG: bool = Field(
        default=False,
        description="Debug mode flag"
    )
    
    API_TIMEOUT: int = Field(
        default=30,
        description="API timeout in seconds",
        gt=0  # Must be greater than 0
    )
    
    # Database configuration
    DATABASE_URL: SecretStr | None = Field(
        default=None,
        description="PostgreSQL database connection URL"
    )
    
    DB_POOL_SIZE: int = Field(
        default=5,
        description="Database connection pool size",
        gt=0
    )
    
    DB_MAX_OVERFLOW: int = Field(
        default=10,
        description="Maximum overflow connections in pool",
        ge=0
    )
    
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        description="Database pool timeout in seconds",
        gt=0
    )
    
    DB_MAX_RETRIES: int = Field(
        default=3,
        description="Maximum number of retry attempts for database operations",
        ge=0
    )
    
    DB_RETRY_DELAY: float = Field(
        default=1.0,
        description="Initial delay between retries in seconds",
        gt=0
    )
    
    # Secret fields - masked in repr
    API_KEY: SecretStr | None = Field(
        default=None,
        description="API key for external services"
    )
    
    SECRET_KEY: SecretStr | None = Field(
        default=None,
        description="Application secret key"
    )
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got '{v}'"
            )
        return v_upper
    
    def get_database_url(self) -> str | None:
        """Get the database URL value if set."""
        return self.DATABASE_URL.get_secret_value() if self.DATABASE_URL else None
    
    def get_api_key(self) -> str | None:
        """Get the API key value if set."""
        return self.API_KEY.get_secret_value() if self.API_KEY else None
    
    def get_secret_key(self) -> str | None:
        """Get the secret key value if set."""
        return self.SECRET_KEY.get_secret_value() if self.SECRET_KEY else None


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get the application settings singleton.
    
    Loads settings from environment variables and .env file on first call.
    Subsequent calls return the cached instance.
    
    Returns:
        Settings: The application settings instance
        
    Raises:
        ValidationError: If required environment variables are missing or invalid
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the settings singleton. Useful for testing."""
    global _settings
    _settings = None
