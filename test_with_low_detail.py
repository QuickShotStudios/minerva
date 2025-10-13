#!/usr/bin/env python3
"""Test with low detail level to see if it bypasses content filter."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from minerva.core.ingestion.text_extraction import TextExtractor


async def main():
    """Test with low detail level."""
    screenshot_path = Path("screenshots/Kindle-10-06-2025_11_29_PM.png")

    if not screenshot_path.exists():
        print("Screenshot not found")
        return

    print("Testing with detail='low' (uses fewer tokens, might bypass filter)...")

    # Try with low detail
    extractor = TextExtractor(detail_level="low")

    try:
        extracted_text, metadata = await extractor.extract_text_from_screenshot(
            screenshot_path,
            book_id="test",
            screenshot_id="test",
        )

        print("\n✓ Success with low detail!")
        print(f"Tokens: {metadata['tokens_used']}")
        print(f"Cost: ${metadata['cost_estimate']:.6f}")
        print(f"\nExtracted text:\n{extracted_text}")

    except Exception as e:
        print(f"\n✗ Still failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
