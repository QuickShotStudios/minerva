#!/usr/bin/env python
"""Cleanup script to clear test data from database and filesystem.

This script:
1. Truncates all main tables (books, screenshots, text_chunks, ingestion_logs)
2. Removes all screenshot directories
3. Resets the database to clean state for testing
"""

import asyncio
import shutil
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from minerva.config import settings
from minerva.db.session import AsyncSessionLocal


async def main():
    """Clear all test data."""
    print("\n" + "=" * 70)
    print("DATABASE AND FILESYSTEM CLEANUP")
    print("=" * 70)
    print("\n⚠️  WARNING: This will delete ALL data:")
    print("  - All book records")
    print("  - All screenshot records")
    print("  - All text chunk records")
    print("  - All ingestion logs")
    print("  - All screenshot files\n")

    confirm = input("Type 'yes' to continue: ").strip().lower()
    if confirm != "yes":
        print("\n❌ Cleanup cancelled")
        return

    print("\n" + "-" * 70)
    print("Cleaning up database...")
    print("-" * 70 + "\n")

    async with AsyncSessionLocal() as session:
        try:
            # Truncate tables in correct order (respecting foreign keys)
            tables = ["text_chunks", "screenshots", "ingestion_logs", "books"]

            for table in tables:
                # Check if table exists first
                result = await session.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        f"WHERE table_schema = 'public' AND table_name = '{table}')"
                    )
                )
                exists = result.scalar()

                if exists:
                    print(f"  Truncating {table}...")
                    await session.execute(
                        text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                    )
                else:
                    print(f"  Skipping {table} (doesn't exist)")

            await session.commit()
            print("\n✅ Database tables cleared\n")

        except Exception as e:
            print(f"\n❌ Database cleanup failed: {e}\n")
            await session.rollback()
            raise

    # Clear screenshots directory
    print("-" * 70)
    print("Cleaning up screenshots...")
    print("-" * 70 + "\n")

    screenshots_dir = Path(settings.screenshots_dir).expanduser()
    if screenshots_dir.exists():
        try:
            shutil.rmtree(screenshots_dir)
            print(f"  Removed: {screenshots_dir}")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Recreated: {screenshots_dir}")
            print("\n✅ Screenshots directory cleared\n")
        except Exception as e:
            print(f"\n❌ Screenshot cleanup failed: {e}\n")
            raise
    else:
        print(f"  No screenshots directory found at {screenshots_dir}")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {screenshots_dir}\n")

    print("=" * 70)
    print("✅ CLEANUP COMPLETE")
    print("=" * 70)
    print("\nDatabase and filesystem are now clean and ready for testing!\n")


if __name__ == "__main__":
    asyncio.run(main())
