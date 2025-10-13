#!/usr/bin/env python
"""Timed authentication script for Kindle with automatic session save.

This script:
1. Launches Chrome browser in headed mode
2. Navigates to your Kindle URL
3. Waits 2 minutes for you to log in manually
4. Automatically saves the session state
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from minerva.config import settings
from minerva.core.ingestion.kindle_automation import KindleAutomation


async def main():
    """Launch browser and authenticate with timed wait."""
    print("\n" + "=" * 70)
    print("KINDLE AUTHENTICATION (TIMED)")
    print("=" * 70)
    print("\nThis will:")
    print("1. Open Chrome browser")
    print("2. Navigate to your Kindle book")
    print("3. Wait 2 minutes for you to log in")
    print("4. Automatically save your session\n")

    kindle_url = sys.argv[1] if len(sys.argv) > 1 else input("Enter Kindle URL: ").strip()

    if not kindle_url:
        print("❌ Error: Kindle URL is required")
        return

    print("\n" + "-" * 70)
    print("Launching browser...")
    print("-" * 70 + "\n")

    async with KindleAutomation(headless=False) as kindle:
        # Navigate to the URL
        print(f"Navigating to: {kindle_url}\n")
        await kindle.page.goto(kindle_url)

        print("=" * 70)
        print("PLEASE LOG IN TO AMAZON IN THE BROWSER WINDOW")
        print("=" * 70)
        print("\nYou have 2 minutes to log in...")
        print("The browser will stay open for 120 seconds.\n")

        # Wait for 2 minutes (120 seconds) to give time to log in
        for remaining in range(120, 0, -10):
            print(f"⏱️  Time remaining: {remaining} seconds...")
            await asyncio.sleep(10)

        print("\n⏱️  Time's up! Saving session...\n")

        # Save the session
        await kindle.save_session_state()

        print("\n" + "=" * 70)
        print("✅ SESSION SAVED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nSession saved to: {settings.session_state_path.expanduser()}")
        print("\nYou can now run book capture without logging in again!")

        # Keep browser open for 5 more seconds so you can verify
        print("\nBrowser will close in 5 seconds...")
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
