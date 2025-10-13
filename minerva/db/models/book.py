"""Book model for storing Kindle book metadata and ingestion status."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Book(SQLModel, table=True):
    """Book model representing a Kindle book in the library."""

    __tablename__ = "books"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
    )
    title: str = Field(nullable=False, index=True)
    author: str = Field(nullable=False, index=True)
    kindle_url: str = Field(nullable=False)
    total_screenshots: int = Field(default=0, nullable=False)
    capture_date: datetime | None = Field(default=None)
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
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
