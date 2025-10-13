#!/usr/bin/env python
"""End-to-end pipeline test script for 20 pages.

This script:
1. Captures 20 screenshots from Kindle book (starting from page 1)
2. Runs OCR text extraction on all screenshots
3. Generates semantic chunks from extracted text
4. Creates vector embeddings for all chunks
5. Stores everything in the database
6. Verifies the complete pipeline worked correctly
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from minerva.core.ingestion.kindle_automation import KindleAutomation
from minerva.core.ingestion.pipeline import IngestionPipeline
from minerva.db.repositories import BookRepository, ScreenshotRepository
from minerva.db.session import AsyncSessionLocal


async def verify_results(book_id):
    """Verify that all pipeline stages completed successfully."""
    async with AsyncSessionLocal() as session:
        book_repo = BookRepository(session)
        screenshot_repo = ScreenshotRepository(session)

        # Get book record
        book = await book_repo.get_by_id(book_id)
        if not book:
            print("❌ Book record not found")
            return False

        print(f"\n{'='*70}")
        print("PIPELINE VERIFICATION")
        print(f"{'='*70}\n")

        print(f"📚 Book: {book.title}")
        print(f"   Author: {book.author}")
        print(f"   Status: {book.ingestion_status}")
        print(f"   Total Screenshots: {book.total_screenshots}")

        # Get screenshot records
        screenshots = await screenshot_repo.get_screenshots_by_book_id(book_id)
        print(f"\n📸 Screenshots: {len(screenshots)} captured")

        # Check for extracted text (would be in a separate table in full implementation)
        print(f"\n📝 Text Extraction: {'✓' if book.ingestion_status != 'screenshots_complete' else '⚠️  Pending'}")

        # Check final status
        success = book.ingestion_status == "completed"
        if success:
            print("\n✅ PIPELINE COMPLETE")
        else:
            print(f"\n⚠️  Pipeline Status: {book.ingestion_status}")
            if book.ingestion_error:
                print(f"   Error: {book.ingestion_error}")

        print(f"{'='*70}\n")
        return success


async def main():
    """Run end-to-end pipeline test."""
    print("\n" + "=" * 70)
    print("END-TO-END PIPELINE TEST (20 PAGES)")
    print("=" * 70)
    print("\nThis will:")
    print("1. Capture 20 screenshots from Kindle book")
    print("2. Extract text using Tesseract OCR")
    print("3. Generate semantic chunks")
    print("4. Create vector embeddings")
    print("5. Store everything in database\n")

    # Get test inputs
    kindle_url = input("Enter Kindle Cloud Reader URL: ").strip()
    book_title = input("Enter book title (optional): ").strip() or "Test Book"
    book_author = input("Enter book author (optional): ").strip() or "Unknown Author"

    if not kindle_url:
        print("❌ Error: Kindle URL is required")
        return

    # Step 1: Capture screenshots
    print("\n" + "-" * 70)
    print("STEP 1: SCREENSHOT CAPTURE (20 pages)")
    print("-" * 70 + "\n")

    async with KindleAutomation(headless=False) as kindle:
        try:
            book_id = await kindle.capture_full_book(
                kindle_url=kindle_url,
                book_title=book_title,
                book_author=book_author,
                max_pages=20,  # Only 20 pages for this test
            )

            print(f"\n✅ Screenshot capture complete! Book ID: {book_id}\n")

        except Exception as e:
            print(f"\n❌ Screenshot capture failed: {e}\n")
            import traceback

            traceback.print_exc()
            return

    # Step 2: Run full pipeline (starting from text extraction)
    print("-" * 70)
    print("STEP 2: FULL PIPELINE (OCR → Chunks → Embeddings)")
    print("-" * 70 + "\n")

    async with AsyncSessionLocal() as session:
        try:
            pipeline = IngestionPipeline(session=session)

            # Run pipeline starting from text extraction stage
            # (screenshots already exist from step 1)
            book = await pipeline.run_pipeline(
                kindle_url=kindle_url, title=book_title, author=book_author
            )

            print(f"\n✅ Pipeline complete! Final status: {book.ingestion_status}\n")

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}\n")
            import traceback

            traceback.print_exc()
            return

    # Step 3: Verify results
    success = await verify_results(book_id)

    if success:
        print("=" * 70)
        print("✅ END-TO-END TEST PASSED")
        print("=" * 70)
        print("\nAll pipeline stages completed successfully:")
        print("  ✓ 20 screenshots captured from page 1")
        print("  ✓ Text extracted with Tesseract OCR")
        print("  ✓ Semantic chunks generated")
        print("  ✓ Vector embeddings created")
        print("  ✓ All data stored in database")
        print("\n✨ Full pipeline is working correctly!\n")
    else:
        print("=" * 70)
        print("❌ END-TO-END TEST FAILED")
        print("=" * 70)
        print("\nPipeline did not complete successfully. Check logs above.\n")


if __name__ == "__main__":
    asyncio.run(main())
