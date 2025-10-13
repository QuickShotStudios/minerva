"""Vector similarity search using pgvector for semantic chunk retrieval."""

import time
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.core.ingestion.embedding_generator import EmbeddingGenerator
from minerva.db.models.book import Book
from minerva.db.models.chunk import Chunk

logger = structlog.get_logger(__name__)


@dataclass
class SearchResult:
    """Result from vector similarity search."""

    chunk_id: UUID
    chunk_text: str
    similarity_score: float
    book_id: UUID
    book_title: str
    book_author: str | None
    screenshot_ids: list[UUID]
    chunk_sequence: int
    previous_chunks: list["SearchResult"] | None = None
    next_chunks: list["SearchResult"] | None = None


@dataclass
class SearchMetadata:
    """Metadata about the search operation."""

    embedding_model: str
    processing_time_ms: int
    total_results: int
    similarity_threshold: float
    top_k: int
    filters_applied: dict[str, bool]


class VectorSearch:
    """Vector similarity search for semantic chunk retrieval."""

    def __init__(self, session: AsyncSession):
        """
        Initialize vector search with database session.

        Args:
            session: Async database session for queries
        """
        self.session = session
        self.embedding_generator = EmbeddingGenerator(session)

    async def search(
        self,
        query_text: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        book_ids: list[UUID] | None = None,
        date_range: tuple[datetime, datetime] | None = None,
        include_context: bool = False,
        context_size: int = 1,
    ) -> tuple[list[SearchResult], SearchMetadata]:
        """
        Search for semantically similar chunks using vector similarity.

        Args:
            query_text: Text query to search for
            top_k: Maximum number of results to return (default: 10)
            similarity_threshold: Minimum similarity score (0-1, default: 0.7)
            book_ids: Optional list of book IDs to filter by
            date_range: Optional tuple of (start_date, end_date) to filter books
            include_context: Whether to include previous/next chunks (default: False)
            context_size: Number of chunks before/after to include (default: 1)

        Returns:
            Tuple of (search_results, metadata)

        Raises:
            ValueError: If query_text is empty or parameters invalid
        """
        if not query_text.strip():
            raise ValueError("Query text cannot be empty")

        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")

        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        start_time = time.time()

        # Generate query embedding
        logger.debug("generating_query_embedding", query_length=len(query_text))
        query_embeddings = await self.embedding_generator.generate_embeddings(
            texts=[query_text], book_id=None
        )
        query_vector = query_embeddings[0]

        # Build vector similarity search query
        similarity = (1 - Chunk.embedding.cosine_distance(query_vector)).label(
            "similarity_score"
        )

        query = (
            select(
                Chunk.id.label("chunk_id"),
                Chunk.chunk_text,
                similarity,
                Chunk.book_id,
                Book.title.label("book_title"),
                Book.author.label("book_author"),
                Chunk.screenshot_ids,
                Chunk.chunk_sequence,
            )
            .join(Book, Chunk.book_id == Book.id)
            .where(similarity >= similarity_threshold)
            .order_by(similarity.desc())
            .limit(top_k)
        )

        # Apply optional filters
        if book_ids:
            query = query.where(Chunk.book_id.in_(book_ids))
            logger.debug("book_filter_applied", book_count=len(book_ids))

        if date_range:
            start_date, end_date = date_range
            query = query.where(
                Book.created_at >= start_date, Book.created_at <= end_date
            )
            logger.debug("date_filter_applied", start=start_date, end=end_date)

        # Execute query
        result = await self.session.execute(query)
        rows = result.all()

        # Process results
        search_results = [
            SearchResult(
                chunk_id=row.chunk_id,
                chunk_text=row.chunk_text,
                similarity_score=float(row.similarity_score),
                book_id=row.book_id,
                book_title=row.book_title,
                book_author=row.book_author,
                screenshot_ids=row.screenshot_ids,
                chunk_sequence=row.chunk_sequence,
            )
            for row in rows
        ]

        # Add context windows if requested
        if include_context:
            for search_result in search_results:
                context = await self._get_context_window(
                    book_id=search_result.book_id,
                    chunk_sequence=search_result.chunk_sequence,
                    context_size=context_size,
                )
                search_result.previous_chunks = context["previous"]
                search_result.next_chunks = context["next"]

        # Calculate metadata
        processing_time = time.time() - start_time
        metadata = SearchMetadata(
            embedding_model=self.embedding_generator.embedding_model,
            processing_time_ms=int(processing_time * 1000),
            total_results=len(search_results),
            similarity_threshold=similarity_threshold,
            top_k=top_k,
            filters_applied={
                "book_ids": book_ids is not None,
                "date_range": date_range is not None,
            },
        )

        logger.info(
            "vector_search_complete",
            query_text=query_text[:100],
            results_count=len(search_results),
            processing_time_ms=metadata.processing_time_ms,
        )

        return search_results, metadata

    async def _get_context_window(
        self, book_id: UUID, chunk_sequence: int, context_size: int = 1
    ) -> dict[str, list[SearchResult]]:
        """
        Fetch previous and next chunks for context.

        Args:
            book_id: Book ID containing the chunk
            chunk_sequence: Sequence number of the main chunk
            context_size: Number of chunks before/after (default: 1)

        Returns:
            Dictionary with "previous" and "next" chunk lists
        """
        # Fetch previous chunks
        prev_query = (
            select(
                Chunk.id.label("chunk_id"),
                Chunk.chunk_text,
                Chunk.book_id,
                Chunk.screenshot_ids,
                Chunk.chunk_sequence,
                Book.title.label("book_title"),
                Book.author.label("book_author"),
            )
            .join(Book, Chunk.book_id == Book.id)
            .where(Chunk.book_id == book_id, Chunk.chunk_sequence < chunk_sequence)
            .order_by(Chunk.chunk_sequence.desc())
            .limit(context_size)
        )

        # Fetch next chunks
        next_query = (
            select(
                Chunk.id.label("chunk_id"),
                Chunk.chunk_text,
                Chunk.book_id,
                Chunk.screenshot_ids,
                Chunk.chunk_sequence,
                Book.title.label("book_title"),
                Book.author.label("book_author"),
            )
            .join(Book, Chunk.book_id == Book.id)
            .where(Chunk.book_id == book_id, Chunk.chunk_sequence > chunk_sequence)
            .order_by(Chunk.chunk_sequence.asc())
            .limit(context_size)
        )

        prev_result = await self.session.execute(prev_query)
        next_result = await self.session.execute(next_query)

        previous_chunks = [
            SearchResult(
                chunk_id=row.chunk_id,
                chunk_text=row.chunk_text,
                similarity_score=0.0,  # Context chunks don't have similarity scores
                book_id=row.book_id,
                book_title=row.book_title,
                book_author=row.book_author,
                screenshot_ids=row.screenshot_ids,
                chunk_sequence=row.chunk_sequence,
            )
            for row in prev_result.all()
        ]

        next_chunks = [
            SearchResult(
                chunk_id=row.chunk_id,
                chunk_text=row.chunk_text,
                similarity_score=0.0,
                book_id=row.book_id,
                book_title=row.book_title,
                book_author=row.book_author,
                screenshot_ids=row.screenshot_ids,
                chunk_sequence=row.chunk_sequence,
            )
            for row in next_result.all()
        ]

        return {"previous": previous_chunks, "next": next_chunks}
