"""Pytest configuration and fixtures."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest

from minerva.config import Settings


@pytest.fixture
def test_settings() -> Generator[Settings, None, None]:
    """
    Provide test configuration with overrides.

    Yields:
        Settings instance for testing
    """
    # Save original environment
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://postgres@localhost/mpp_minerva_test"
    )
    os.environ["SCREENSHOTS_DIR"] = "test_screenshots"
    os.environ["LOG_LEVEL"] = "DEBUG"

    # Create test settings
    settings = Settings()

    yield settings

    # Cleanup test screenshots directory
    screenshots_dir = Path("test_screenshots")
    if screenshots_dir.exists():
        screenshots_dir.rmdir()

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
