"""Search API endpoints for semantic chunk retrieval."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.api.dependencies import get_db
from minerva.api.security import verify_api_key
from minerva.api.schemas.search import (
    BookSummary,
    ContextChunk,
    QueryMetadata,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from minerva.core.search.vector_search import VectorSearch

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "/semantic",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic search query",
    description="Search knowledge base using natural language query with vector similarity",
    responses={
        200: {"description": "Successful search with results"},
        401: {"description": "Unauthorized (invalid or missing API key)"},
        422: {"description": "Validation error (invalid parameters)"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable (database or embedding service down)"},
    },
)
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _: None = Depends(verify_api_key),  # noqa: B008
) -> SearchResponse:
    """
    Execute semantic search query against knowledge base.

    Returns up to top_k chunks ranked by similarity score, optionally filtered
    by book IDs or date range. Supports context windows for expanded results.

    **Authentication:** Requires valid API key in X-API-Key header.

    Args:
        request: Search request with query text and optional filters
        db: Database session (injected)

    Returns:
        SearchResponse with results and query metadata

    Raises:
        HTTPException: 401 for invalid/missing API key, 422 for validation errors,
                      503 for service unavailable, 500 for internal errors
    """
    logger.info(
        "semantic_search_request",
        query=request.query[:100],  # Truncate for logging
        top_k=request.top_k,
        threshold=request.similarity_threshold,
        include_context=request.include_context,
    )

    try:
        # Initialize vector search service
        search_service = VectorSearch(db)

        # Execute search
        results, metadata = await search_service.search(
            query_text=request.query,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            book_ids=request.filters.book_ids if request.filters else None,
            date_range=request.filters.date_range if request.filters else None,
            include_context=request.include_context,
            context_size=request.context_size,
        )

        # Convert to response schema
        response_items = []
        for r in results:
            # Build context window if present
            context_window = None
            if r.previous_chunks is not None or r.next_chunks is not None:
                context_window = {
                    "previous": [
                        ContextChunk(
                            chunk_id=c.chunk_id,
                            chunk_text=c.chunk_text,
                            chunk_sequence=c.chunk_sequence,
                        )
                        for c in (r.previous_chunks or [])
                    ],
                    "next": [
                        ContextChunk(
                            chunk_id=c.chunk_id,
                            chunk_text=c.chunk_text,
                            chunk_sequence=c.chunk_sequence,
                        )
                        for c in (r.next_chunks or [])
                    ],
                }

            response_items.append(
                SearchResultItem(
                    chunk_id=r.chunk_id,
                    chunk_text=r.chunk_text,
                    similarity_score=r.similarity_score,
                    book=BookSummary(
                        id=r.book_id,
                        title=r.book_title,
                        author=r.book_author,
                    ),
                    screenshot_ids=r.screenshot_ids,
                    chunk_sequence=r.chunk_sequence,
                    context_window=context_window,
                )
            )

        # Build query metadata from search service metadata
        query_metadata = QueryMetadata(
            embedding_model=metadata.embedding_model,
            processing_time_ms=metadata.processing_time_ms,
            total_results=metadata.total_results,
            similarity_threshold=metadata.similarity_threshold,
            top_k=metadata.top_k,
            filters_applied=metadata.filters_applied,
        )

        logger.info(
            "semantic_search_complete",
            results_count=len(response_items),
            processing_time_ms=metadata.processing_time_ms,
        )

        return SearchResponse(
            results=response_items,
            query_metadata=query_metadata,
        )

    except SQLAlchemyError as e:
        logger.error("database_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from e

    except Exception as e:
        logger.error("search_failed", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
