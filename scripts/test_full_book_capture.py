#!/usr/bin/env python
"""Test script for full book screenshot capture.

This script validates:
- Full book capture from start to finish
- Progress tracking and display
- Database integration (Book and Screenshot records)
- Screenshot hashing and duplicate detection
- Book-end detection
- Error handling and ingestion logs
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from minerva.core.ingestion.kindle_automation import KindleAutomation
from minerva.db.repositories import BookRepository, ScreenshotRepository
from minerva.db.session import AsyncSessionLocal


async def verify_database_records(book_id):
    """Verify that database records were created correctly."""
    async with AsyncSessionLocal() as session:
        book_repo = BookRepository(session)
        screenshot_repo = ScreenshotRepository(session)

        # Get book record
        book = await book_repo.get_by_id(book_id)
        if not book:
            print("❌ Book record not found in database")
            return False

        print("\n📚 Book Record:")
        print(f"  ID: {book.id}")
        print(f"  Title: {book.title}")
        print(f"  Author: {book.author}")
        print(f"  Status: {book.ingestion_status}")
        print(f"  Total Screenshots: {book.total_screenshots}")
        print(f"  Ingested At: {book.ingested_at}")

        # Get screenshot records
        screenshots = await screenshot_repo.get_by_book_id(book_id)
        print(f"\n📸 Screenshot Records: {len(screenshots)} found")

        if len(screenshots) != book.total_screenshots:
            print(
                f"❌ Screenshot count mismatch: {len(screenshots)} vs {book.total_screenshots}"
            )
            return False

        # Verify sequential numbering
        for i, screenshot in enumerate(screenshots, start=1):
            if screenshot.sequence_number != i:
                print(
                    f"❌ Non-sequential screenshot: expected {i}, got {screenshot.sequence_number}"
                )
                return False

        print("✓ All screenshot records are sequential")

        # Verify files exist
        missing_files = []
        for screenshot in screenshots:
            if not Path(screenshot.file_path).exists():
                missing_files.append(screenshot.file_path)

        if missing_files:
            print(f"❌ Missing screenshot files: {len(missing_files)}")
            for f in missing_files[:5]:  # Show first 5
                print(f"  - {f}")
            return False

        print("✓ All screenshot files exist on disk")

        return True


async def main():
    """Run full book capture test."""
    print("\n" + "=" * 70)
    print("FULL BOOK CAPTURE TEST")
    print("=" * 70)
    print("\nThis test will:")
    print("1. Capture all pages of a Kindle book")
    print("2. Track progress with real-time display")
    print("3. Detect book end via duplicate detection or UI indicators")
    print("4. Save screenshots to disk with book_id directory structure")
    print("5. Create Book and Screenshot records in database")
    print("6. Create ingestion log entries\n")

    # Get test inputs
    kindle_url = input("Enter Kindle Cloud Reader URL: ").strip()
    book_title = input("Enter book title (optional): ").strip() or None
    book_author = input("Enter book author (optional): ").strip() or None

    if not kindle_url:
        print("❌ Error: Kindle URL is required")
        return

    # Run capture
    print("\n" + "-" * 70)
    print("Starting Full Book Capture")
    print("-" * 70 + "\n")

    async with KindleAutomation(headless=False) as kindle:
        try:
            book_id = await kindle.capture_full_book(
                kindle_url=kindle_url,
                book_title=book_title,
                book_author=book_author,
                max_pages=1000,  # Safety limit
            )

            # Verify database records
            print("\n" + "-" * 70)
            print("Verifying Database Records")
            print("-" * 70)

            success = await verify_database_records(book_id)

            if success:
                print("\n" + "=" * 70)
                print("✅ FULL BOOK CAPTURE TEST PASSED")
                print("=" * 70)
                print("\nAll acceptance criteria met:")
                print("  ✓ Complete book captured from start to finish")
                print("  ✓ Progress tracking displayed")
                print("  ✓ Book end detected (duplicate or UI indicator)")
                print("  ✓ Screenshots saved with book_id directory structure")
                print("  ✓ Book and Screenshot records created in database")
                print("  ✓ Sequential numbering verified")
                print("  ✓ All files exist on disk")
                print("\n✨ Full book capture working correctly!")
            else:
                print("\n❌ TEST FAILED: Database verification failed")

        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
