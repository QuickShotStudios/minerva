"""Book API endpoints for listing and retrieving book details."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.api.dependencies import get_db
from minerva.api.schemas.books import (
    BookDetail,
    BookListItem,
    BooksListResponse,
    IngestionLogItem,
)
from minerva.db.models.book import Book
from minerva.db.models.chunk import Chunk
from minerva.db.models.ingestion_log import IngestionLog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/books", tags=["books"])


@router.get(
    "",
    response_model=BooksListResponse,
    summary="List books",
    description="Retrieve paginated list of books in knowledge base",
    status_code=status.HTTP_200_OK,
)
async def list_books(
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by ingestion_status"
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BooksListResponse:
    """
    List books with pagination and optional status filtering.

    Args:
        limit: Maximum number of books to return (1-100)
        offset: Number of books to skip
        status_filter: Optional filter by ingestion_status
        db: Database session (injected)

    Returns:
        BooksListResponse with books list, total count, and has_more flag
    """
    logger.info("list_books_request", limit=limit, offset=offset, status=status_filter)

    # Build query to get books with chunk counts
    query = (
        select(
            Book.id,
            Book.title,
            Book.author,
            Book.total_screenshots,
            Book.capture_date,
            Book.ingestion_status,
            func.count(Chunk.id).label("total_chunks"),
        )
        .outerjoin(Chunk, Book.id == Chunk.book_id)
        .group_by(
            Book.id,
            Book.title,
            Book.author,
            Book.total_screenshots,
            Book.capture_date,
            Book.ingestion_status,
        )
    )

    # Apply status filter if provided
    if status_filter:
        query = query.where(Book.ingestion_status == status_filter)

    # Get total count (before pagination)
    count_query = select(func.count()).select_from(Book)
    if status_filter:
        count_query = count_query.where(Book.ingestion_status == status_filter)
    total_count = await db.scalar(count_query) or 0

    # Apply pagination and ordering
    query = query.order_by(Book.created_at.desc()).offset(offset).limit(limit)

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    # Build response
    books = [
        BookListItem(
            id=row.id,
            title=row.title,
            author=row.author,
            total_screenshots=row.total_screenshots,
            total_chunks=row.total_chunks or 0,
            capture_date=row.capture_date,
            ingestion_status=row.ingestion_status,
        )
        for row in rows
    ]

    logger.info("list_books_complete", books_count=len(books), total_count=total_count)

    return BooksListResponse(
        books=books,
        total_count=total_count,
        has_more=(offset + limit) < total_count,
    )


@router.get(
    "/{book_id}",
    response_model=BookDetail,
    summary="Get book details",
    description="Retrieve full book details including metadata and recent logs",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Book not found"},
    },
)
async def get_book(
    book_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BookDetail:
    """
    Get detailed information about a specific book.

    Args:
        book_id: UUID of the book to retrieve
        db: Database session (injected)

    Returns:
        BookDetail with full book information, chunk count, and recent logs

    Raises:
        HTTPException: 404 if book not found
    """
    logger.info("get_book_request", book_id=str(book_id))

    # Fetch book
    book_query = select(Book).where(Book.id == book_id)
    result = await db.execute(book_query)
    book = result.scalar_one_or_none()

    if not book:
        logger.warning("book_not_found", book_id=str(book_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found",
        )

    # Count chunks for this book
    chunk_count_query = (
        select(func.count()).select_from(Chunk).where(Chunk.book_id == book_id)
    )
    total_chunks = await db.scalar(chunk_count_query) or 0

    # Fetch recent error/warning logs (last 10)
    logs_query = (
        select(IngestionLog)
        .where(
            IngestionLog.book_id == book_id,
            IngestionLog.log_level.in_(["WARNING", "ERROR"]),
        )
        .order_by(IngestionLog.created_at.desc())
        .limit(10)
    )
    logs_result = await db.execute(logs_query)
    logs = logs_result.scalars().all()

    logger.info(
        "get_book_complete",
        book_id=str(book_id),
        total_chunks=total_chunks,
        recent_logs_count=len(logs),
    )

    # Build response
    return BookDetail(
        id=book.id,
        title=book.title,
        author=book.author,
        kindle_url=book.kindle_url,
        total_screenshots=book.total_screenshots,
        total_chunks=total_chunks,
        capture_date=book.capture_date,
        ingestion_status=book.ingestion_status,
        ingestion_error=book.ingestion_error,
        metadata=book.metadata,
        created_at=book.created_at,
        updated_at=book.updated_at,
        recent_logs=[
            IngestionLogItem(
                log_level=log.log_level,
                message=log.message,
                created_at=log.created_at,
            )
            for log in logs
        ],
    )
