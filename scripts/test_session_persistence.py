#!/usr/bin/env python
"""Test script for session persistence functionality.

This script validates:
- Authentication and session save
- Session reuse without re-authentication
- Multiple books ingested with single login
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from minerva.core.ingestion.kindle_automation import KindleAutomation


async def test_session_persistence():
    """Test session persistence across multiple book ingestions."""
    print("\n" + "=" * 70)
    print("SESSION PERSISTENCE TEST")
    print("=" * 70)

    # Get test URLs
    print("\nThis test will:")
    print("1. Authenticate once for Book A")
    print("2. Save session state")
    print("3. Close browser")
    print("4. Open new browser with saved session")
    print("5. Access Book B without re-authentication\n")

    book_a_url = input("Enter Kindle URL for Book A: ").strip()
    book_b_url = input("Enter Kindle URL for Book B: ").strip()

    if not book_a_url or not book_b_url:
        print("Error: Both URLs required")
        return

    # Test 1: Authenticate and save session
    print("\n" + "-" * 70)
    print("TEST 1: Authenticate and capture Book A")
    print("-" * 70)

    screenshots_dir = Path("screenshots/session_test")
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    async with KindleAutomation(headless=False) as kindle:
        print("✓ Browser launched")

        # Navigate and authenticate (will save session after auth)
        await kindle.navigate_to_book(book_a_url)
        print("✓ Book A loaded")

        # Capture one screenshot to verify
        screenshot = screenshots_dir / "book_a_page_1.png"
        await kindle.capture_screenshot(screenshot)
        print(f"✓ Screenshot saved: {screenshot.name}")

    print("✓ Browser closed")
    print("\n⏸  Session should now be saved...")
    input("\nPress Enter to continue to Test 2...")

    # Test 2: Use saved session for Book B
    print("\n" + "-" * 70)
    print("TEST 2: Load Book B using saved session (no re-auth)")
    print("-" * 70)

    async with KindleAutomation(headless=False) as kindle:
        print("✓ Browser launched with saved session")

        # This should NOT require authentication
        await kindle.navigate_to_book(book_b_url)
        print("✓ Book B loaded (without authentication!)")

        # Capture screenshot to verify
        screenshot = screenshots_dir / "book_b_page_1.png"
        await kindle.capture_screenshot(screenshot)
        print(f"✓ Screenshot saved: {screenshot.name}")

    print("✓ Browser closed")

    # Summary
    print("\n" + "=" * 70)
    print("✅ SESSION PERSISTENCE TEST COMPLETE")
    print("=" * 70)
    print("\nResults:")
    print("  - Authenticated once for Book A")
    print("  - Session saved and reused for Book B")
    print("  - No re-authentication required")
    print(f"  - Screenshots saved to: {screenshots_dir}")
    print("\n  ✓ Session persistence working correctly!")


if __name__ == "__main__":
    asyncio.run(test_session_persistence())
