#!/usr/bin/env python
"""Simple script to authenticate with Kindle and save session state.

This script:
1. Launches Chrome browser in headed mode
2. Navigates to your Kindle URL
3. Waits for you to log in manually
4. Saves the session state for future use
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from minerva.config import settings
from minerva.core.ingestion.kindle_automation import KindleAutomation


async def main():
    """Launch browser and authenticate."""
    print("\n" + "=" * 70)
    print("KINDLE AUTHENTICATION")
    print("=" * 70)
    print("\nThis will:")
    print("1. Open Chrome browser")
    print("2. Navigate to your Kindle book")
    print("3. Wait for you to log in")
    print("4. Save your session for future use\n")

    kindle_url = input("Enter Kindle URL: ").strip()

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
        print("\nAfter you've logged in and see the book content,")
        input("press Enter here to save your session...\n")

        # Save the session
        await kindle.save_session_state()

        print("\n" + "=" * 70)
        print("✅ SESSION SAVED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nSession saved to: {settings.session_state_path.expanduser()}")
        print("\nYou can now run book capture without logging in again!")
        print("\nClosing browser...")


if __name__ == "__main__":
    asyncio.run(main())
