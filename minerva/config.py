"""Configuration management for Minerva using Pydantic Settings."""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Tesseract OCR settings
    tesseract_cmd: str = Field(
        default="tesseract",
        description="Path to tesseract binary",
    )
    use_ai_formatting: bool = Field(
        default=False,
        description="Enable optional AI formatting cleanup of OCR output (adds ~$0.01/100 pages)",
    )
    filter_kindle_ui: bool = Field(
        default=True,
        description="Remove Kindle UI elements (page numbers, progress bars) from extracted text",
    )

    # OpenAI settings
    openai_api_key: SecretStr = Field(
        ...,
        description="OpenAI API key for embeddings and optional formatting",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model for vector generation",
    )
    embedding_dimensions: int = Field(
        default=1536,
        description="Embedding vector dimensions",
    )

    # Database settings
    database_url: str = Field(
        default="postgresql+asyncpg://postgres@localhost/mpp_minerva_local",
        description="PostgreSQL database URL with asyncpg driver",
    )
    production_database_url: str | None = Field(
        default=None,
        description="Production PostgreSQL database URL (optional)",
    )
    database_echo: bool = Field(
        default=False,
        description="Echo SQL queries to console",
    )

    # File system settings
    screenshots_dir: Path = Field(
        default=Path("screenshots"),
        description="Directory for storing screenshot files",
    )
    session_state_path: Path = Field(
        default=Path("~/.minerva/session_state.json"),
        description="Path to Playwright session state file",
    )

    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    environment: str = Field(
        default="development",
        description="Environment (development or production)",
    )

    # CORS settings
    cors_allowed_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins for API requests",
    )

    # API Security settings
    api_key: SecretStr | None = Field(
        default=None,
        description="Primary API key for authentication (required in production)",
    )
    require_api_key: bool = Field(
        default=True,
        description="Require API key authentication for protected endpoints",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model is in allowed list."""
        allowed_models = {"text-embedding-3-small", "text-embedding-3-large"}
        if v not in allowed_models:
            raise ValueError(
                f"Invalid embedding_model: {v}. Allowed values: {', '.join(allowed_models)}"
            )
        return v

    @model_validator(mode="after")
    def validate_embedding_dimensions(self) -> "Settings":
        """Validate embedding dimensions match the selected model."""
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        expected_dims = model_dimensions.get(self.embedding_model)
        if expected_dims and self.embedding_dimensions != expected_dims:
            raise ValueError(
                f"embedding_dimensions ({self.embedding_dimensions}) does not match "
                f"embedding_model ({self.embedding_model}). Expected: {expected_dims}"
            )
        return self

    @model_validator(mode="after")
    def create_screenshots_directory(self) -> "Settings":
        """Create screenshots directory if it doesn't exist."""
        try:
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise ValueError(
                f"Cannot create screenshots directory at {self.screenshots_dir}: {e}"
            ) from e
        return self

    @model_validator(mode="after")
    def validate_api_key(self) -> "Settings":
        """Validate API key is set when required in production."""
        if (
            self.require_api_key
            and self.environment == "production"
            and not self.api_key
        ):
            raise ValueError(
                "API_KEY must be set when REQUIRE_API_KEY=true in production environment. "
                "Set API_KEY environment variable or set REQUIRE_API_KEY=false."
            )
        return self


# Global settings instance
settings = Settings()  # type: ignore[call-arg]
