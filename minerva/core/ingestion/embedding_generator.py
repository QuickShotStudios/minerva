"""Vector embedding generation using OpenAI Embeddings API."""

import asyncio
from uuid import UUID

import structlog
from openai import AsyncOpenAI, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.config import settings
from minerva.db.models.embedding_config import EmbeddingConfig
from minerva.utils.exceptions import EmbeddingGenerationError, OpenAIRateLimitError
from minerva.utils.openai_client import get_openai_client

logger = structlog.get_logger(__name__)


class EmbeddingGenerator:
    """
    Generate vector embeddings for text chunks using OpenAI Embeddings API.

    This class handles:
    - Batch embedding generation (up to 100 chunks per API call)
    - OpenAI embeddings API integration
    - Embedding config management (model tracking)
    - Error handling with retry logic for rate limits
    - Cost tracking and token usage logging
    - Database integration for storing embeddings
    """

    def __init__(
        self,
        session: AsyncSession,
        client: AsyncOpenAI | None = None,
        embedding_model: str | None = None,
        embedding_dimensions: int | None = None,
        batch_size: int = 100,
    ) -> None:
        """
        Initialize EmbeddingGenerator with database session and configuration.

        Args:
            session: Database session for storing embeddings and configs
            client: Optional AsyncOpenAI client (defaults to new client from settings)
            embedding_model: Optional model name (defaults to settings.embedding_model)
            embedding_dimensions: Optional dimensions (defaults to settings.embedding_dimensions)
            batch_size: Number of chunks per API call (default: 100, max: 2048)
        """
        self.session = session
        self.client = client or get_openai_client()
        self.embedding_model = embedding_model or settings.embedding_model
        self.embedding_dimensions = (
            embedding_dimensions or settings.embedding_dimensions
        )
        self.batch_size = min(batch_size, 2048)  # OpenAI max is 2048

    async def generate_embeddings(
        self,
        texts: list[str],
        book_id: str | None = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of text chunks.

        Args:
            texts: List of text strings to embed
            book_id: Optional book ID for logging context

        Returns:
            List of embedding vectors (1536-dimensional)

        Raises:
            EmbeddingGenerationError: If embedding generation fails

        Example:
            ```python
            generator = EmbeddingGenerator(session)
            texts = ["chunk 1 text", "chunk 2 text"]
            embeddings = await generator.generate_embeddings(texts)
            ```
        """
        if not texts:
            logger.warning("empty_texts_for_embedding", book_id=book_id)
            return []

        try:
            # Split into batches
            all_embeddings: list[list[float]] = []
            total_batches = (len(texts) + self.batch_size - 1) // self.batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * self.batch_size
                end_idx = min(start_idx + self.batch_size, len(texts))
                batch_texts = texts[start_idx:end_idx]

                # Generate embeddings for this batch
                batch_embeddings = await self._generate_batch_embeddings(
                    batch_texts, book_id=book_id
                )
                all_embeddings.extend(batch_embeddings)

                logger.info(
                    "embedding_batch_complete",
                    book_id=book_id,
                    batch_num=batch_num + 1,
                    total_batches=total_batches,
                    batch_size=len(batch_texts),
                )

            # Calculate total tokens and cost
            total_tokens = sum(len(text.split()) * 1.3 for text in texts)  # Approximate
            cost_estimate = total_tokens * 0.02 / 1_000_000  # $0.02 per 1M tokens

            logger.info(
                "embeddings_generation_complete",
                book_id=book_id,
                total_chunks=len(texts),
                total_embeddings=len(all_embeddings),
                total_tokens=int(total_tokens),
                cost_estimate=cost_estimate,
            )

            return all_embeddings

        except Exception as e:
            logger.error(
                "embeddings_generation_failed",
                book_id=book_id,
                total_texts=len(texts),
                error=str(e),
            )
            raise EmbeddingGenerationError(f"Failed to generate embeddings: {e}") from e

    async def _generate_batch_embeddings(
        self,
        texts: list[str],
        book_id: str | None = None,
        max_retries: int = 3,
    ) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts with retry logic.

        Args:
            texts: List of text strings to embed (max 100)
            book_id: Optional book ID for logging
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            List of embedding vectors

        Raises:
            OpenAIRateLimitError: If rate limit exceeded after retries
            EmbeddingGenerationError: If embedding generation fails
        """
        delay = 1.0  # Initial delay in seconds
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.embeddings.create(
                    model=self.embedding_model,
                    input=texts,
                    encoding_format="float",
                )

                # Extract embeddings from response
                embeddings = [item.embedding for item in response.data]

                # Log token usage
                total_tokens = response.usage.total_tokens
                cost_estimate = total_tokens * 0.02 / 1_000_000

                logger.debug(
                    "batch_embeddings_success",
                    book_id=book_id,
                    batch_size=len(texts),
                    tokens_used=total_tokens,
                    cost_estimate=cost_estimate,
                )

                return embeddings

            except RateLimitError as e:
                last_exception = e
                if attempt == max_retries:
                    logger.error(
                        "rate_limit_retries_exhausted",
                        book_id=book_id,
                        attempts=attempt + 1,
                        error=str(e),
                    )
                    raise OpenAIRateLimitError(
                        f"Rate limit exceeded after {max_retries + 1} attempts"
                    ) from e

                logger.warning(
                    "rate_limit_retry",
                    book_id=book_id,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

            except Exception as e:
                # Server errors (5xx): retry
                error_str = str(e)
                if "500" in error_str or "502" in error_str or "503" in error_str:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            "server_error_retries_exhausted",
                            book_id=book_id,
                            attempts=attempt + 1,
                            error=error_str,
                        )
                        raise EmbeddingGenerationError(
                            f"Server error after {max_retries + 1} attempts: {error_str}"
                        ) from e

                    logger.warning(
                        "server_error_retry",
                        book_id=book_id,
                        attempt=attempt + 1,
                        delay=2.0,
                        error=error_str,
                    )
                    await asyncio.sleep(2.0)
                    continue

                # Client errors or other errors: don't retry
                logger.error(
                    "embedding_error_no_retry",
                    book_id=book_id,
                    error=error_str,
                )
                raise EmbeddingGenerationError(
                    f"Embedding generation error: {error_str}"
                ) from e

        # This should never be reached
        if last_exception:
            raise EmbeddingGenerationError(
                f"Failed after {max_retries + 1} attempts"
            ) from last_exception
        raise RuntimeError("Unexpected retry loop exit")

    async def get_or_create_embedding_config(self) -> EmbeddingConfig:
        """
        Get existing embedding config or create new one.

        Returns:
            EmbeddingConfig instance with current model settings

        Example:
            ```python
            config = await generator.get_or_create_embedding_config()
            print(f"Using config: {config.model_name}, dims: {config.dimensions}")
            ```
        """
        from sqlalchemy import select, update

        # Check if active config exists with current model
        # fmt: off
        stmt = select(EmbeddingConfig).where(
            EmbeddingConfig.is_active == True,  # type: ignore  # noqa: E712
            EmbeddingConfig.model_name == self.embedding_model,  # type: ignore
        )
        # fmt: on
        result = await self.session.execute(stmt)
        existing_config = result.scalar_one_or_none()

        if existing_config:
            logger.debug(
                "embedding_config_found",
                config_id=str(existing_config.id),
                model_name=existing_config.model_name,
            )
            return existing_config

        # Archive old active configs
        # fmt: off
        update_stmt = (
            update(EmbeddingConfig)
            .where(EmbeddingConfig.is_active == True)  # type: ignore  # noqa: E712
            .values(is_active=False)
        )
        # fmt: on
        await self.session.execute(update_stmt)

        # Create new config
        new_config = EmbeddingConfig(
            model_name=self.embedding_model,
            model_version="v1",  # Default version
            dimensions=self.embedding_dimensions,
            is_active=True,
        )
        self.session.add(new_config)
        await self.session.flush()

        logger.info(
            "embedding_config_created",
            config_id=str(new_config.id),
            model_name=new_config.model_name,
            dimensions=new_config.dimensions,
        )

        return new_config

    async def re_embed_book(
        self,
        book_id: UUID,
        new_model: str | None = None,
    ) -> int:
        """
        Re-generate embeddings for all chunks in a book with a different model.

        Args:
            book_id: UUID of book to re-embed
            new_model: Optional new model name (defaults to current settings)

        Returns:
            Number of chunks re-embedded

        Raises:
            EmbeddingGenerationError: If re-embedding fails

        Example:
            ```python
            chunks_updated = await generator.re_embed_book(
                book_id=UUID("..."),
                new_model="text-embedding-3-large"
            )
            ```
        """
        from sqlalchemy import select

        from minerva.db.models.book import Book
        from minerva.db.models.chunk import Chunk

        # Validate book exists
        book_stmt = select(Book).where(Book.id == book_id)  # type: ignore
        book_result = await self.session.execute(book_stmt)
        book = book_result.scalar_one_or_none()

        if not book:
            raise EmbeddingGenerationError(f"Book {book_id} not found")

        # Get all chunks for this book
        chunks_stmt = select(Chunk).where(Chunk.book_id == book_id).order_by(Chunk.chunk_sequence)  # type: ignore
        chunks_result = await self.session.execute(chunks_stmt)
        chunks = chunks_result.scalars().all()

        if not chunks:
            raise EmbeddingGenerationError(f"No chunks found for book {book_id}")

        # Update model if provided
        if new_model:
            self.embedding_model = new_model

        # Get current embedding config
        current_config = await self.get_or_create_embedding_config()

        # Validate new model differs from current
        if chunks[0].embedding_config_id == current_config.id:
            logger.warning(
                "re_embed_same_model",
                book_id=str(book_id),
                model=self.embedding_model,
            )
            # Continue anyway - user may want to regenerate

        # Extract chunk texts
        chunk_texts = [chunk.chunk_text for chunk in chunks]

        # Generate new embeddings
        logger.info(
            "re_embedding_started",
            book_id=str(book_id),
            total_chunks=len(chunks),
            new_model=self.embedding_model,
        )

        new_embeddings = await self.generate_embeddings(
            chunk_texts, book_id=str(book_id)
        )

        # Update chunks with new embeddings (transactionally)
        for chunk, embedding in zip(chunks, new_embeddings, strict=False):
            chunk.embedding = embedding
            chunk.embedding_config_id = current_config.id

        await self.session.flush()

        logger.info(
            "re_embedding_complete",
            book_id=str(book_id),
            chunks_updated=len(chunks),
            new_model=self.embedding_model,
            config_id=str(current_config.id),
        )

        return len(chunks)
