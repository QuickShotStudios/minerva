"""Pydantic schemas for book and chunk API endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BookListItem(BaseModel):
    """Book summary for list responses."""

    id: UUID
    title: str
    author: str | None
    total_screenshots: int | None
    total_chunks: int
    capture_date: datetime
    ingestion_status: str


class BooksListResponse(BaseModel):
    """Response schema for books list endpoint."""

    books: list[BookListItem]
    total_count: int
    has_more: bool

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "books": [
                        {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Peptide Therapy Guide",
                            "author": "Dr. John Smith",
                            "total_screenshots": 209,
                            "total_chunks": 185,
                            "capture_date": "2025-10-06T10:30:00Z",
                            "ingestion_status": "completed",
                        }
                    ],
                    "total_count": 5,
                    "has_more": False,
                }
            ]
        }
    }


class IngestionLogItem(BaseModel):
    """Ingestion log entry for book details."""

    log_level: str
    message: str
    created_at: datetime


class BookDetail(BaseModel):
    """Detailed book information with metadata and logs."""

    id: UUID
    title: str
    author: str | None
    kindle_url: str
    total_screenshots: int | None
    total_chunks: int
    capture_date: datetime
    ingestion_status: str
    ingestion_error: str | None
    metadata: dict | None  # type: ignore[type-arg]
    created_at: datetime
    updated_at: datetime
    recent_logs: list[IngestionLogItem]


class ChunkContext(BaseModel):
    """Context chunks (previous/next) for chunk details."""

    previous_chunk: str | None = Field(
        None, description="Text from previous chunk in sequence"
    )
    next_chunk: str | None = Field(None, description="Text from next chunk in sequence")


class ChunkDetail(BaseModel):
    """Detailed chunk information with context."""

    chunk_id: UUID
    chunk_text: str
    chunk_sequence: int
    chunk_token_count: int
    book: BookListItem
    screenshot_ids: list[UUID]
    vision_model: str
    context: ChunkContext
