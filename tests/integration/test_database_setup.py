"""Integration tests for database setup validation."""


import pytest

from minerva.db.repositories.book_repository import BookRepository
from minerva.db.repositories.screenshot_repository import ScreenshotRepository
from minerva.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_create_and_read_book():
    """Test creating and reading a book record."""
    async with AsyncSessionLocal() as session:
        repo = BookRepository(session)

        # Create a book
        book = await repo.create_book(
            title="Test Book",
            author="Test Author",
            kindle_url="https://read.amazon.com/test",
        )

        assert book.id is not None
        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert book.kindle_url == "https://read.amazon.com/test"
        assert book.ingestion_status == "pending"

        # Read the book back
        retrieved_book = await repo.get_book_by_id(book.id)
        assert retrieved_book is not None
        assert retrieved_book.id == book.id
        assert retrieved_book.title == book.title

        await session.commit()


@pytest.mark.asyncio
async def test_create_and_read_screenshot():
    """Test creating and reading a screenshot record."""
    async with AsyncSessionLocal() as session:
        book_repo = BookRepository(session)
        screenshot_repo = ScreenshotRepository(session)

        # Create a book first
        book = await book_repo.create_book(
            title="Test Book for Screenshots",
            author="Test Author",
            kindle_url="https://read.amazon.com/test2",
        )

        # Create a screenshot
        screenshot = await screenshot_repo.create_screenshot(
            book_id=book.id,
            sequence_number=1,
            file_path="/path/to/screenshot.png",
            screenshot_hash="abc123",
        )

        assert screenshot.id is not None
        assert screenshot.book_id == book.id
        assert screenshot.sequence_number == 1
        assert screenshot.file_path == "/path/to/screenshot.png"

        # Read screenshots by book ID
        screenshots = await screenshot_repo.get_screenshots_by_book_id(book.id)
        assert len(screenshots) == 1
        assert screenshots[0].id == screenshot.id

        await session.commit()


@pytest.mark.asyncio
async def test_screenshot_unique_constraint():
    """Test that duplicate book_id + sequence_number raises error."""
    book_id = None

    async with AsyncSessionLocal() as session:
        book_repo = BookRepository(session)
        screenshot_repo = ScreenshotRepository(session)

        # Create a book
        book = await book_repo.create_book(
            title="Unique Test Book",
            author="Test Author",
            kindle_url="https://read.amazon.com/unique",
        )
        book_id = book.id

        # Create first screenshot
        await screenshot_repo.create_screenshot(
            book_id=book_id,
            sequence_number=1,
            file_path="/path/to/screenshot1.png",
        )
        await session.commit()

    # Try to create duplicate in new session
    async with AsyncSessionLocal() as session:
        screenshot_repo = ScreenshotRepository(session)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await screenshot_repo.create_screenshot(
                book_id=book_id,
                sequence_number=1,
                file_path="/path/to/screenshot2.png",
            )
            await session.commit()


@pytest.mark.asyncio
async def test_pgvector_extension():
    """Test that pgvector extension is installed."""
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM pg_extension WHERE extname = 'vector';")
        )
        row = result.fetchone()
        assert row is not None, "pgvector extension not installed"
