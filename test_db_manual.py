"""Manual test to verify database setup."""

import asyncio

from minerva.db.repositories.book_repository import BookRepository
from minerva.db.repositories.screenshot_repository import ScreenshotRepository
from minerva.db.session import AsyncSessionLocal


async def main():
    """Test database operations."""
    print("Testing database setup...")

    # Test 1: Create and read book
    async with AsyncSessionLocal() as session:
        repo = BookRepository(session)
        book = await repo.create_book(
            title="Manual Test Book",
            author="Test Author",
            kindle_url="https://read.amazon.com/manual",
        )
        print(f"✓ Created book: {book.id} - {book.title}")

        retrieved = await repo.get_book_by_id(book.id)
        assert retrieved.id == book.id
        print(f"✓ Retrieved book: {retrieved.title}")

        await session.commit()

    # Test 2: Create screenshot
    async with AsyncSessionLocal() as session:
        screenshot_repo = ScreenshotRepository(session)
        screenshot = await screenshot_repo.create_screenshot(
            book_id=book.id,
            sequence_number=1,
            file_path="/test/path.png",
        )
        print(f"✓ Created screenshot: {screenshot.id}")

        screenshots = await screenshot_repo.get_screenshots_by_book_id(book.id)
        assert len(screenshots) == 1
        print(f"✓ Retrieved {len(screenshots)} screenshot(s)")

        await session.commit()

    # Test 3: Check pgvector extension
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM pg_extension WHERE extname = 'vector';")
        )
        row = result.fetchone()
        assert row is not None
        print("✓ pgvector extension installed")

    print("\n✅ All manual tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
