"""Centralized OpenAI client initialization and utilities."""

from openai import AsyncOpenAI

from minerva.config import settings


def get_openai_client() -> AsyncOpenAI:
    """
    Get configured OpenAI async client instance.

    Returns:
        Configured AsyncOpenAI client with API key from settings

    Example:
        ```python
        client = get_openai_client()
        response = await client.chat.completions.create(...)
        ```
    """
    return AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
