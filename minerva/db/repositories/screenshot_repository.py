"""Screenshot repository for database operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.db.models.screenshot import Screenshot
from minerva.db.repositories.base_repository import BaseRepository


class ScreenshotRepository(BaseRepository[Screenshot]):
    """Repository for Screenshot model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize screenshot repository."""
        super().__init__(Screenshot, session)

    async def create_screenshot(
        self,
        book_id: UUID,
        sequence_number: int,
        file_path: str,
        screenshot_hash: str | None = None,
    ) -> Screenshot:
        """
        Create a new screenshot record.

        Args:
            book_id: Book UUID
            sequence_number: Screenshot sequence number
            file_path: Path to screenshot file
            screenshot_hash: Optional hash of screenshot

        Returns:
            Created Screenshot instance
        """
        screenshot = Screenshot(
            book_id=book_id,
            sequence_number=sequence_number,
            file_path=file_path,
            screenshot_hash=screenshot_hash,
            captured_at=datetime.utcnow(),
        )
        return await self.create(screenshot)

    async def get_screenshots_by_book_id(self, book_id: UUID) -> list[Screenshot]:
        """
        Get all screenshots for a book.

        Args:
            book_id: Book UUID

        Returns:
            List of Screenshot instances
        """
        result = await self.session.execute(
            select(Screenshot)
            .where(Screenshot.book_id == book_id)  # type: ignore[arg-type]
            .order_by(Screenshot.sequence_number)  # type: ignore[arg-type]
        )
        return list(result.scalars().all())

    async def get_screenshot_by_sequence(
        self, book_id: UUID, sequence_number: int
    ) -> Screenshot | None:
        """
        Get screenshot by book ID and sequence number.

        Args:
            book_id: Book UUID
            sequence_number: Screenshot sequence number

        Returns:
            Screenshot instance or None
        """
        result = await self.session.execute(
            select(Screenshot).where(
                Screenshot.book_id == book_id,  # type: ignore[arg-type]
                Screenshot.sequence_number == sequence_number,  # type: ignore[arg-type]
            )
        )
        return result.scalar_one_or_none()
