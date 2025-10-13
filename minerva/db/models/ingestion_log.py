"""IngestionLog model for audit trail of ingestion pipeline."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class IngestionLog(SQLModel, table=True):
    """IngestionLog model for tracking ingestion pipeline operations."""

    __tablename__ = "ingestion_logs"

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
    pipeline_stage: str = Field(nullable=False, index=True)
    status: str = Field(nullable=False, index=True)
    error_message: str | None = Field(default=None)
    execution_time_ms: int | None = Field(default=None)
    log_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        index=True,
    )
