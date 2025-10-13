"""Token counting utilities using tiktoken for accurate OpenAI token estimation."""

import tiktoken


def count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    """
    Count tokens in text using tiktoken for accurate OpenAI token estimation.

    Args:
        text: Text to count tokens for
        model: OpenAI model name (default: "text-embedding-3-small")

    Returns:
        Number of tokens in the text

    Example:
        ```python
        token_count = count_tokens("Hello, world!")
        print(f"Token count: {token_count}")
        ```
    """
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def count_tokens_for_vision(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    Count tokens for vision model inputs using specific encoding.

    Args:
        text: Text to count tokens for
        encoding_name: Tiktoken encoding name (default: "cl100k_base" for GPT-4 models)

    Returns:
        Number of tokens in the text

    Example:
        ```python
        token_count = count_tokens_for_vision("Extract all text from this image")
        ```
    """
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))
