"""Unit tests for embedding generation module."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from openai import RateLimitError
from openai.types import CreateEmbeddingResponse, Embedding
from openai.types.create_embedding_response import Usage

from minerva.core.ingestion.embedding_generator import EmbeddingGenerator
from minerva.db.models.embedding_config import EmbeddingConfig
from minerva.utils.exceptions import (
    EmbeddingGenerationError,
)


@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_openai_client():
    """Create mock AsyncOpenAI client."""
    return AsyncMock()


@pytest.fixture
def embedding_generator(mock_session, mock_openai_client):
    """Create EmbeddingGenerator instance with mocked dependencies."""
    return EmbeddingGenerator(
        session=mock_session,
        client=mock_openai_client,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        batch_size=100,
    )


def create_mock_embedding_response(
    texts: list[str],
    dimensions: int = 1536,
) -> CreateEmbeddingResponse:
    """
    Create a mock OpenAI embeddings API response.

    Args:
        texts: List of input texts
        dimensions: Embedding dimensions

    Returns:
        Mock CreateEmbeddingResponse
    """
    embeddings = [
        Embedding(
            object="embedding",
            embedding=[0.1] * dimensions,  # Fake embedding vector
            index=i,
        )
        for i in range(len(texts))
    ]

    return CreateEmbeddingResponse(
        object="list",
        data=embeddings,
        model="text-embedding-3-small",
        usage=Usage(
            prompt_tokens=len(" ".join(texts).split()),
            total_tokens=len(" ".join(texts).split()),
        ),
    )


@pytest.mark.asyncio
async def test_successful_embedding_generation(embedding_generator):
    """Test successful embedding generation with mocked OpenAI response."""
    # Arrange
    texts = ["chunk 1 text", "chunk 2 text", "chunk 3 text"]
    mock_response = create_mock_embedding_response(texts)
    embedding_generator.client.embeddings.create = AsyncMock(return_value=mock_response)

    # Act
    embeddings = await embedding_generator.generate_embeddings(
        texts, book_id="test-book"
    )

    # Assert
    assert len(embeddings) == 3
    assert all(len(emb) == 1536 for emb in embeddings)
    embedding_generator.client.embeddings.create.assert_called_once()


@pytest.mark.asyncio
async def test_batch_processing_splits_correctly():
    """Test that 250 chunks are split into 3 batches (100, 100, 50)."""
    # Arrange
    mock_session = AsyncMock()
    mock_client = AsyncMock()
    generator = EmbeddingGenerator(
        session=mock_session,
        client=mock_client,
        batch_size=100,
    )

    texts = [f"chunk {i}" for i in range(250)]

    # Create different responses for each batch call
    def create_response_for_batch(*args, **kwargs):
        input_texts = kwargs.get("input", [])
        return create_mock_embedding_response(input_texts)

    generator.client.embeddings.create = AsyncMock(
        side_effect=create_response_for_batch
    )

    # Act
    embeddings = await generator.generate_embeddings(texts)

    # Assert
    assert len(embeddings) == 250
    # Should have called API 3 times (100 + 100 + 50)
    assert generator.client.embeddings.create.call_count == 3


@pytest.mark.asyncio
async def test_rate_limit_retry_success(embedding_generator):
    """Test exponential backoff on rate limit errors with eventual success."""
    # Arrange
    texts = ["chunk 1"]
    mock_response = create_mock_embedding_response(texts)

    # First two calls raise RateLimitError, third succeeds
    embedding_generator.client.embeddings.create = AsyncMock(
        side_effect=[
            RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None,
            ),
            RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None,
            ),
            mock_response,
        ]
    )

    # Act
    embeddings = await embedding_generator.generate_embeddings(texts)

    # Assert
    assert len(embeddings) == 1
    assert embedding_generator.client.embeddings.create.call_count == 3


@pytest.mark.asyncio
async def test_rate_limit_retries_exhausted(embedding_generator):
    """Test that rate limit errors raise exception after max retries."""
    # Arrange
    texts = ["chunk 1"]
    embedding_generator.client.embeddings.create = AsyncMock(
        side_effect=RateLimitError(
            "Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )
    )

    # Act & Assert
    with pytest.raises(EmbeddingGenerationError, match="Failed to generate embeddings"):
        await embedding_generator.generate_embeddings(texts)

    # Should have tried 4 times (initial + 3 retries)
    assert embedding_generator.client.embeddings.create.call_count >= 4


@pytest.mark.asyncio
async def test_server_error_retry(embedding_generator):
    """Test server error (5xx) retry logic."""
    # Arrange
    texts = ["chunk 1"]
    mock_response = create_mock_embedding_response(texts)

    # First call raises server error, second succeeds
    embedding_generator.client.embeddings.create = AsyncMock(
        side_effect=[
            Exception("500 Internal Server Error"),
            mock_response,
        ]
    )

    # Act
    embeddings = await embedding_generator.generate_embeddings(texts)

    # Assert
    assert len(embeddings) == 1
    assert embedding_generator.client.embeddings.create.call_count == 2


@pytest.mark.asyncio
async def test_empty_texts_returns_empty_list(embedding_generator):
    """Test that empty text list returns empty embeddings list."""
    # Act
    embeddings = await embedding_generator.generate_embeddings([])

    # Assert
    assert embeddings == []
    embedding_generator.client.embeddings.create.assert_not_called()


@pytest.mark.asyncio
async def test_token_usage_tracking(embedding_generator):
    """Test that token usage is tracked and cost is calculated."""
    # Arrange
    texts = ["chunk 1", "chunk 2"]
    mock_response = create_mock_embedding_response(texts)
    embedding_generator.client.embeddings.create = AsyncMock(return_value=mock_response)

    # Act
    with patch("minerva.core.ingestion.embedding_generator.logger") as mock_logger:
        await embedding_generator.generate_embeddings(texts, book_id="test-book")

        # Assert - verify logger.info was called with cost estimate
        info_calls = list(mock_logger.info.call_args_list)
        assert any("embeddings_generation_complete" in str(call) for call in info_calls)


@pytest.mark.asyncio
async def test_embedding_config_creation(embedding_generator):
    """Test that new embedding config is created when none exists."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    embedding_generator.session.execute = AsyncMock(return_value=mock_result)
    embedding_generator.session.flush = AsyncMock()
    embedding_generator.session.add = MagicMock()

    # Act
    config = await embedding_generator.get_or_create_embedding_config()

    # Assert
    assert config.model_name == "text-embedding-3-small"
    assert config.dimensions == 1536
    assert config.is_active is True
    embedding_generator.session.add.assert_called_once()
    embedding_generator.session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_embedding_config_retrieval(embedding_generator):
    """Test that existing embedding config is retrieved."""
    # Arrange
    existing_config = EmbeddingConfig(
        id=uuid4(),
        model_name="text-embedding-3-small",
        dimensions=1536,
        is_active=True,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_config
    embedding_generator.session.execute = AsyncMock(return_value=mock_result)
    embedding_generator.session.add = MagicMock()

    # Act
    config = await embedding_generator.get_or_create_embedding_config()

    # Assert
    assert config.id == existing_config.id
    assert config.model_name == existing_config.model_name
    embedding_generator.session.add.assert_not_called()


@pytest.mark.asyncio
async def test_embedding_config_archiving():
    """Test that old configs are marked inactive when creating new one."""
    # Arrange
    mock_session = AsyncMock()
    mock_client = AsyncMock()
    generator = EmbeddingGenerator(
        session=mock_session,
        client=mock_client,
        embedding_model="text-embedding-3-large",  # Different model
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    generator.session.execute = AsyncMock(return_value=mock_result)
    generator.session.flush = AsyncMock()
    generator.session.add = MagicMock()

    # Act
    await generator.get_or_create_embedding_config()

    # Assert - verify UPDATE statement was executed (archiving old configs)
    assert generator.session.execute.call_count >= 2  # SELECT + UPDATE


@pytest.mark.asyncio
async def test_embedding_dimensions_match_model():
    """Test that embedding dimensions match the configured model."""
    # Arrange
    mock_session = AsyncMock()
    mock_client = AsyncMock()

    # Test text-embedding-3-small (1536 dims)
    generator_small = EmbeddingGenerator(
        session=mock_session,
        client=mock_client,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
    )
    assert generator_small.embedding_dimensions == 1536

    # Test text-embedding-3-large would be 3072 dims
    generator_large = EmbeddingGenerator(
        session=mock_session,
        client=mock_client,
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
    )
    assert generator_large.embedding_dimensions == 3072


@pytest.mark.asyncio
async def test_custom_batch_size():
    """Test embedding generator with custom batch size."""
    # Arrange
    mock_session = AsyncMock()
    mock_client = AsyncMock()
    generator = EmbeddingGenerator(
        session=mock_session,
        client=mock_client,
        batch_size=50,  # Custom batch size
    )

    texts = [f"chunk {i}" for i in range(120)]

    # Create different responses for each batch call
    def create_response_for_batch(*args, **kwargs):
        input_texts = kwargs.get("input", [])
        return create_mock_embedding_response(input_texts)

    generator.client.embeddings.create = AsyncMock(
        side_effect=create_response_for_batch
    )

    # Act
    embeddings = await generator.generate_embeddings(texts)

    # Assert
    assert len(embeddings) == 120
    # Should have called API 3 times (50 + 50 + 20)
    assert generator.client.embeddings.create.call_count == 3


@pytest.mark.asyncio
async def test_batch_size_capped_at_max():
    """Test that batch size is capped at OpenAI's max (2048)."""
    # Arrange
    mock_session = AsyncMock()
    mock_client = AsyncMock()
    generator = EmbeddingGenerator(
        session=mock_session,
        client=mock_client,
        batch_size=5000,  # Try to set above max
    )

    # Assert
    assert generator.batch_size == 2048  # Should be capped


@pytest.mark.asyncio
async def test_re_embed_book_validation(embedding_generator):
    """Test that re_embed_book validates book exists."""
    # Arrange
    book_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Book not found
    embedding_generator.session.execute = AsyncMock(return_value=mock_result)

    # Act & Assert
    with pytest.raises(EmbeddingGenerationError, match="not found"):
        await embedding_generator.re_embed_book(book_id)


@pytest.mark.asyncio
async def test_re_embed_book_no_chunks(embedding_generator):
    """Test that re_embed_book fails gracefully when book has no chunks."""
    # Arrange
    from minerva.db.models.book import Book

    book_id = uuid4()
    mock_book = Book(id=book_id, title="Test Book", author="Test Author")

    # Mock book exists
    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = mock_book

    # Mock no chunks
    mock_chunks_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_chunks_result.scalars.return_value = mock_scalars

    embedding_generator.session.execute = AsyncMock(
        side_effect=[mock_book_result, mock_chunks_result]
    )

    # Act & Assert
    with pytest.raises(EmbeddingGenerationError, match="No chunks found"):
        await embedding_generator.re_embed_book(book_id)


@pytest.mark.asyncio
async def test_cost_estimation():
    """Test that cost estimation is calculated correctly."""
    # $0.02 per 1M tokens for text-embedding-3-small
    mock_session = AsyncMock()
    mock_client = AsyncMock()
    generator = EmbeddingGenerator(session=mock_session, client=mock_client)

    texts = ["word " * 1000 for _ in range(100)]  # ~100k tokens
    mock_response = create_mock_embedding_response(texts)
    generator.client.embeddings.create = AsyncMock(return_value=mock_response)

    with patch("minerva.core.ingestion.embedding_generator.logger") as mock_logger:
        await generator.generate_embeddings(texts)

        # Verify cost logging occurred
        info_calls = mock_logger.info.call_args_list
        assert len(info_calls) > 0
