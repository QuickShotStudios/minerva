#!/usr/bin/env python
"""POC script to test Playwright Kindle automation.

This script validates:
- Navigation to Kindle URL
- Authentication handling
- Book reader loading
- Screenshot capture
- Page turning
- Capturing 10 consecutive pages
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from minerva.core.ingestion.kindle_automation import KindleAutomation


async def main():
    """Run Playwright POC test."""
    # Test Kindle URL (replace with your own book URL)
    kindle_url = input("Enter Kindle Cloud Reader URL: ").strip()

    if not kindle_url:
        print("Error: No URL provided")
        return

    # Create screenshots directory
    screenshots_dir = Path("screenshots/poc_test")
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    print("\n📚 Starting Playwright POC")
    print(f"URL: {kindle_url}")
    print(f"Screenshots will be saved to: {screenshots_dir}\n")

    # Initialize automation
    async with KindleAutomation(headless=False) as kindle:
        print("✓ Browser launched")

        # Navigate and authenticate
        print("→ Navigating to book...")
        await kindle.navigate_to_book(kindle_url)
        print("✓ Book reader loaded")

        # Capture 10 consecutive pages
        print("\n📸 Capturing 10 pages...")
        for i in range(1, 11):
            # Capture screenshot
            screenshot_path = screenshots_dir / f"page_{i:03d}.png"
            await kindle.capture_screenshot(screenshot_path)
            print(f"  ✓ Page {i:2d} captured: {screenshot_path.name}")

            # Turn to next page (except on last iteration)
            if i < 10:
                success = await kindle.turn_page(direction="next")
                if not success:
                    print("  ⚠ Warning: Page turn may have failed")

        print("\n✅ POC Complete!")
        print(f"   Captured 10 screenshots in {screenshots_dir}")
        print("\n   Review screenshots to verify quality and content.")


if __name__ == "__main__":
    asyncio.run(main())
