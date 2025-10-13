"""Unit tests for configuration management."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from minerva.config import Settings


def test_settings_from_environment(test_settings: Settings):
    """Test that settings load from environment variables."""
    assert test_settings.openai_api_key.get_secret_value() == "sk-test-key"
    assert (
        test_settings.database_url
        == "postgresql+asyncpg://postgres@localhost/mpp_minerva_test"
    )
    assert test_settings.screenshots_dir == Path("test_screenshots")
    assert test_settings.log_level == "DEBUG"


def test_default_values():
    """Test that default values are set correctly."""
    os.environ["OPENAI_API_KEY"] = "sk-test"

    settings = Settings()

    assert settings.vision_model == "gpt-4o-mini"
    assert settings.vision_detail_level == "low"
    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.embedding_dimensions == 1536
    assert settings.log_level == "INFO"


def test_vision_model_validation_invalid():
    """Test validation error for invalid vision model."""
    os.environ["OPENAI_API_KEY"] = "sk-test"
    os.environ["VISION_MODEL"] = "invalid-model"

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "Invalid vision_model" in str(exc_info.value)


def test_vision_model_validation_valid():
    """Test that valid vision models are accepted."""
    os.environ["OPENAI_API_KEY"] = "sk-test"

    for model in ["gpt-4o-mini", "gpt-4o", "gpt-4-vision-preview"]:
        os.environ["VISION_MODEL"] = model
        settings = Settings()
        assert settings.vision_model == model


def test_embedding_model_validation_invalid():
    """Test validation error for invalid embedding model."""
    os.environ["OPENAI_API_KEY"] = "sk-test"
    os.environ["EMBEDDING_MODEL"] = "invalid-embedding"

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "Invalid embedding_model" in str(exc_info.value)


def test_embedding_dimensions_mismatch():
    """Test validation error for mismatched embedding dimensions."""
    os.environ["OPENAI_API_KEY"] = "sk-test"
    os.environ["EMBEDDING_MODEL"] = "text-embedding-3-small"
    os.environ["EMBEDDING_DIMENSIONS"] = "3072"  # Wrong dimensions for this model

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "embedding_dimensions" in str(exc_info.value)
    assert "does not match" in str(exc_info.value)


def test_embedding_dimensions_correct():
    """Test that correct embedding dimensions are accepted."""
    os.environ["OPENAI_API_KEY"] = "sk-test"

    # Test text-embedding-3-small with 1536 dimensions
    os.environ["EMBEDDING_MODEL"] = "text-embedding-3-small"
    os.environ["EMBEDDING_DIMENSIONS"] = "1536"
    settings = Settings()
    assert settings.embedding_dimensions == 1536

    # Test text-embedding-3-large with 3072 dimensions
    os.environ["EMBEDDING_MODEL"] = "text-embedding-3-large"
    os.environ["EMBEDDING_DIMENSIONS"] = "3072"
    settings = Settings()
    assert settings.embedding_dimensions == 3072


def test_missing_required_field():
    """Test validation error for missing required field."""
    # Remove required field and disable .env file loading
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,  # Disable .env file loading
            database_url="postgresql+asyncpg://test",  # Provide other required fields
        )

    assert "openai_api_key" in str(exc_info.value)


def test_screenshots_directory_auto_creation(test_settings: Settings):
    """Test that screenshots directory is created automatically."""
    assert test_settings.screenshots_dir.exists()
    assert test_settings.screenshots_dir.is_dir()


def test_settings_singleton():
    """Test settings singleton access."""
    from minerva.config import settings

    assert settings is not None
    assert hasattr(settings, "openai_api_key")
    assert hasattr(settings, "database_url")
