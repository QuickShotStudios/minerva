"""Chunk API endpoints for retrieving chunk details with context."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.api.dependencies import get_db
from minerva.api.security import verify_api_key
from minerva.api.schemas.books import BookListItem, ChunkContext, ChunkDetail
from minerva.db.models.book import Book
from minerva.db.models.chunk import Chunk

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chunks", tags=["chunks"])


@router.get(
    "/{chunk_id}",
    response_model=ChunkDetail,
    summary="Get chunk details",
    description="Retrieve chunk with surrounding context (previous/next chunks)",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Chunk not found"},
    },
)
async def get_chunk(
    chunk_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _: None = Depends(verify_api_key),  # noqa: B008
) -> ChunkDetail:
    """
    Get detailed information about a specific chunk with context.

    Args:
        chunk_id: UUID of the chunk to retrieve
        db: Database session (injected)

    Returns:
        ChunkDetail with chunk text, book info, and surrounding context

    Raises:
        HTTPException: 404 if chunk not found
    """
    logger.info("get_chunk_request", chunk_id=str(chunk_id))

    # Fetch chunk with book details
    chunk_query = (
        select(Chunk, Book).join(Book, Chunk.book_id == Book.id).where(Chunk.id == chunk_id)
    )
    result = await db.execute(chunk_query)
    row = result.one_or_none()

    if not row:
        logger.warning("chunk_not_found", chunk_id=str(chunk_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk {chunk_id} not found",
        )

    chunk, book = row

    # Fetch previous chunk text (chunk_sequence - 1)
    prev_query = select(Chunk.chunk_text).where(
        Chunk.book_id == chunk.book_id,
        Chunk.chunk_sequence == chunk.chunk_sequence - 1,
    )
    prev_result = await db.execute(prev_query)
    prev_text = prev_result.scalar_one_or_none()

    # Fetch next chunk text (chunk_sequence + 1)
    next_query = select(Chunk.chunk_text).where(
        Chunk.book_id == chunk.book_id,
        Chunk.chunk_sequence == chunk.chunk_sequence + 1,
    )
    next_result = await db.execute(next_query)
    next_text = next_result.scalar_one_or_none()

    # Count total chunks for book
    chunk_count_query = (
        select(func.count()).select_from(Chunk).where(Chunk.book_id == book.id)
    )
    total_chunks = await db.scalar(chunk_count_query) or 0

    logger.info(
        "get_chunk_complete",
        chunk_id=str(chunk_id),
        has_previous=prev_text is not None,
        has_next=next_text is not None,
    )

    # Build response
    return ChunkDetail(
        chunk_id=chunk.id,
        chunk_text=chunk.chunk_text,
        chunk_sequence=chunk.chunk_sequence,
        chunk_token_count=chunk.chunk_token_count,
        book=BookListItem(
            id=book.id,
            title=book.title,
            author=book.author,
            total_screenshots=book.total_screenshots,
            total_chunks=total_chunks,
            capture_date=book.capture_date,
            ingestion_status=book.ingestion_status,
        ),
        screenshot_ids=chunk.screenshot_ids,
        vision_model=chunk.vision_model,
        context=ChunkContext(
            previous_chunk=prev_text,
            next_chunk=next_text,
        ),
    )
