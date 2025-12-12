"""Book model for storing content source metadata and ingestion status.

Supports multiple source types: Kindle books, websites, PDFs, etc.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Enum as SQLAlchemyEnum
from sqlmodel import Field, SQLModel


class SourceType(str, Enum):
    """Source type for content ingestion."""

    KINDLE = "kindle"
    WEBSITE = "website"
    PDF = "pdf"


class Book(SQLModel, table=True):
    """Book model representing a content source in the library.

    Supports multiple source types (Kindle, website, PDF).
    Field usage varies by source type:
    - Kindle: kindle_url, total_screenshots, capture_date are populated
    - Website: source_url, source_domain, page_count, word_count are populated
    - PDF: source_url, word_count are populated
    """

    __tablename__ = "books"

    # Primary fields
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
    )
    title: str = Field(nullable=False, index=True)
    author: str = Field(nullable=False, index=True)

    # Source type and URL
    source_type: SourceType = Field(
        default=SourceType.KINDLE,
        sa_column=Column(
            SQLAlchemyEnum(
                SourceType,
                name="source_type",
                create_constraint=True,
                values_callable=lambda x: [e.value for e in x],
            ),
            nullable=False,
            index=True,
        ),
    )
    source_url: str | None = Field(default=None)  # Generic source URL (for all types)

    # Kindle-specific fields (nullable for other source types)
    kindle_url: str | None = Field(default=None)
    total_screenshots: int | None = Field(default=0)
    capture_date: datetime | None = Field(default=None)

    # Website-specific fields
    source_domain: str | None = Field(default=None, index=True)  # e.g., "peptidedosages.com"
    published_date: datetime | None = Field(default=None, index=True)  # Website publish date
    word_count: int | None = Field(default=None)  # Total word count
    page_count: int | None = Field(default=None)  # # of pages (Kindle pages OR web pages scraped)

    # Ingestion status
    ingestion_status: str = Field(
        default="pending",
        nullable=False,
        index=True,
    )
    ingestion_error: str | None = Field(default=None)
    book_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
