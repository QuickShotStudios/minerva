"""Pydantic schemas for search API endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SearchFilters(BaseModel):
    """Optional filters for search requests."""

    book_ids: list[UUID] | None = Field(
        None, description="Filter by specific book IDs"
    )
    date_range: tuple[datetime, datetime] | None = Field(
        None, description="Filter by book ingestion date range"
    )


class SearchRequest(BaseModel):
    """Request schema for semantic search endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text",
    )
    top_k: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )
    similarity_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0-1)",
    )
    filters: SearchFilters | None = Field(
        None,
        description="Optional filters for narrowing search results",
    )
    include_context: bool = Field(
        False,
        description="Include previous/next chunks for context",
    )
    context_size: int = Field(
        1,
        ge=1,
        le=3,
        description="Number of chunks before/after to include in context",
    )

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        """Validate query is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "BPC-157 for gut health and tissue repair",
                    "top_k": 10,
                    "similarity_threshold": 0.7,
                    "filters": None,
                    "include_context": False,
                    "context_size": 1,
                }
            ]
        }
    }


class BookSummary(BaseModel):
    """Book summary for search results."""

    id: UUID
    title: str
    author: str | None


class ContextChunk(BaseModel):
    """Context chunk (previous/next) for search results."""

    chunk_id: UUID
    chunk_text: str
    chunk_sequence: int


class SearchResultItem(BaseModel):
    """Individual search result item."""

    chunk_id: UUID
    chunk_text: str
    similarity_score: float
    book: BookSummary
    screenshot_ids: list[UUID]
    chunk_sequence: int
    context_window: dict[str, list[ContextChunk]] | None = None


class QueryMetadata(BaseModel):
    """Metadata about the search query execution."""

    embedding_model: str
    processing_time_ms: int
    total_results: int
    similarity_threshold: float
    top_k: int
    filters_applied: dict[str, bool]


class SearchResponse(BaseModel):
    """Response schema for semantic search endpoint."""

    results: list[SearchResultItem]
    query_metadata: QueryMetadata

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "results": [
                        {
                            "chunk_id": "123e4567-e89b-12d3-a456-426614174000",
                            "chunk_text": "BPC-157 has shown promising results for gut health...",
                            "similarity_score": 0.89,
                            "book": {
                                "id": "123e4567-e89b-12d3-a456-426614174001",
                                "title": "Peptide Therapy Guide",
                                "author": "Dr. John Smith",
                            },
                            "screenshot_ids": [
                                "123e4567-e89b-12d3-a456-426614174002"
                            ],
                            "chunk_sequence": 5,
                            "context_window": None,
                        }
                    ],
                    "query_metadata": {
                        "embedding_model": "text-embedding-3-small",
                        "processing_time_ms": 150,
                        "total_results": 1,
                        "similarity_threshold": 0.7,
                        "top_k": 10,
                        "filters_applied": {
                            "book_ids": False,
                            "date_range": False,
                        },
                    },
                }
            ]
        }
    }
