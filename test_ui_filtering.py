#!/usr/bin/env python3
"""Test script to validate UI filtering on actual screenshots."""

import asyncio
from pathlib import Path

from minerva.core.ingestion.text_extraction import TextExtractor


async def test_ui_filtering():
    """Test UI filtering with real screenshots."""
    # Get first screenshot
    screenshots_dir = Path("screenshots/225aad48-9fac-4013-973c-ebea9270b3f5")
    screenshot = screenshots_dir / "page_0001.png"

    if not screenshot.exists():
        print(f"Screenshot not found: {screenshot}")
        return

    print("=" * 80)
    print("TESTING UI FILTERING ON REAL SCREENSHOT")
    print("=" * 80)

    # Test WITHOUT filtering
    print("\n1. WITHOUT UI Filtering:")
    print("-" * 80)
    extractor_no_filter = TextExtractor(filter_kindle_ui=False)
    text_no_filter, metadata_no_filter = await extractor_no_filter.extract_text_from_screenshot(
        screenshot
    )
    print(f"Text length: {len(text_no_filter)} chars")
    print(f"\nFirst 500 chars:\n{text_no_filter[:500]}")

    # Test WITH filtering
    print("\n\n2. WITH UI Filtering:")
    print("-" * 80)
    extractor_with_filter = TextExtractor(filter_kindle_ui=True)
    text_with_filter, metadata_with_filter = await extractor_with_filter.extract_text_from_screenshot(
        screenshot
    )
    print(f"Text length: {len(text_with_filter)} chars")
    print(f"UI chars removed: {metadata_with_filter['kindle_ui_chars_removed']}")
    print(f"\nFirst 500 chars:\n{text_with_filter[:500]}")

    # Show differences
    print("\n\n3. COMPARISON:")
    print("-" * 80)
    chars_removed = len(text_no_filter) - len(text_with_filter)
    print(f"Original length: {len(text_no_filter)} chars")
    print(f"Filtered length: {len(text_with_filter)} chars")
    print(f"Difference: {chars_removed} chars ({chars_removed/len(text_no_filter)*100:.1f}%)")

    # Check for specific UI elements
    ui_elements = [
        "Page x of 209",
        "Page xi of 209",
        "Kindle Library",
        "Learning reading speed",
        "» 39%",
        "» 4%",
    ]

    print("\n4. UI ELEMENT DETECTION:")
    print("-" * 80)
    for element in ui_elements:
        in_original = element in text_no_filter
        in_filtered = element in text_with_filter
        status = "✓ REMOVED" if in_original and not in_filtered else ("✗ NOT FOUND" if not in_original else "✗ STILL PRESENT")
        print(f"{element:30s} -> {status}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_ui_filtering())
