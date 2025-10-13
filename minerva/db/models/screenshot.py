"""Screenshot model for storing Kindle page captures."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Screenshot(SQLModel, table=True):
    """Screenshot model representing a captured Kindle page."""

    __tablename__ = "screenshots"
    __table_args__ = (
        UniqueConstraint(
            "book_id", "sequence_number", name="uq_screenshot_book_sequence"
        ),
    )

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
    sequence_number: int = Field(nullable=False)
    file_path: str = Field(nullable=False)
    screenshot_hash: str | None = Field(default=None, index=True)
    captured_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
