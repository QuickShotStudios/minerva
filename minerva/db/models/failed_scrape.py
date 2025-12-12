"""Failed scrape model for tracking and retrying failed web scrapes."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class FailedScrape(SQLModel, table=True):
    """Failed scrape record for retry functionality.

    Tracks URLs that failed during website scraping to enable
    selective retry without re-scraping successful pages.
    """

    __tablename__ = "failed_scrapes"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
    )
    book_id: UUID = Field(
        foreign_key="books.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    url: str = Field(nullable=False, index=True)
    error_message: str | None = Field(default=None)
    retry_count: int = Field(default=0, nullable=False)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
