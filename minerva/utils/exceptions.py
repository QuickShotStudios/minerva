"""Custom exceptions for Minerva application."""


class MinervaError(Exception):
    """Base exception for all Minerva errors."""

    pass


class TextExtractionError(MinervaError):
    """Exception raised when text extraction from screenshot fails."""

    pass


class OpenAIAPIError(MinervaError):
    """Base exception for OpenAI API errors."""

    pass


class OpenAIRateLimitError(OpenAIAPIError):
    """Exception raised when OpenAI API rate limit is hit (429)."""

    pass


class ChunkingError(MinervaError):
    """Exception raised when text chunking fails."""

    pass


class EmbeddingGenerationError(MinervaError):
    """Exception raised when embedding generation fails."""

    pass
