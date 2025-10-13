"""Book repository for database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.db.models.book import Book
from minerva.db.repositories.base_repository import BaseRepository


class BookRepository(BaseRepository[Book]):
    """Repository for Book model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize book repository."""
        super().__init__(Book, session)

    async def create_book(
        self,
        title: str,
        author: str,
        kindle_url: str,
    ) -> Book:
        """
        Create a new book record.

        Args:
            title: Book title
            author: Book author
            kindle_url: Kindle Cloud Reader URL

        Returns:
            Created Book instance
        """
        book = Book(
            title=title,
            author=author,
            kindle_url=kindle_url,
        )
        return await self.create(book)

    async def get_book_by_id(self, book_id: UUID) -> Book | None:
        """
        Get book by ID.

        Args:
            book_id: Book UUID

        Returns:
            Book instance or None
        """
        return await self.get_by_id(book_id)

    async def get_book_by_url(self, kindle_url: str) -> Book | None:
        """
        Get book by Kindle URL.

        Args:
            kindle_url: Kindle Cloud Reader URL

        Returns:
            Book instance or None
        """
        result = await self.session.execute(
            select(Book).where(Book.kindle_url == kindle_url)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()
