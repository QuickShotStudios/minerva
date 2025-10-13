"""Chunk model for storing semantic text chunks with vector embeddings."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import ARRAY, JSON, Column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class Chunk(SQLModel, table=True):
    """Chunk model representing a semantic text chunk with embedding."""

    __tablename__ = "chunks"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
    )
    book_id: UUID = Field(
        foreign_key="books.id",
        nullable=False,
        index=True,
    )
    screenshot_ids: list[UUID] = Field(
        sa_column=Column(ARRAY(PGUUID(as_uuid=True)), nullable=False),
    )
    chunk_sequence: int = Field(nullable=False)
    chunk_text: str = Field(nullable=False)
    chunk_token_count: int = Field(nullable=False)
    embedding_config_id: UUID = Field(
        foreign_key="embedding_configs.id",
        nullable=False,
    )
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1536)),
    )
    vision_model: str = Field(nullable=False)
    vision_prompt_tokens: int = Field(default=0, nullable=False)
    vision_completion_tokens: int = Field(default=0, nullable=False)
    extraction_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
    chunk_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
