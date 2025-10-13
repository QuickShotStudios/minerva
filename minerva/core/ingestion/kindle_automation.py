"""Kindle Cloud Reader automation with Playwright."""

import asyncio
import hashlib
import logging
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from minerva.config import settings
from minerva.db.models import Book, IngestionLog, Screenshot
from minerva.db.repositories.book_repository import BookRepository
from minerva.db.repositories.screenshot_repository import ScreenshotRepository
from minerva.db.session import AsyncSessionLocal
from minerva.utils.session_manager import ServiceType, SessionManager

logger = logging.getLogger(__name__)


class KindleAutomation:
    """Playwright automation for Kindle Cloud Reader."""

    def __init__(
        self,
        headless: bool = False,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        session_manager: SessionManager | None = None,
    ):
        """
        Initialize Kindle automation.

        Args:
            headless: Run browser in headless mode (default: False for auth)
            viewport_width: Browser viewport width in pixels
            viewport_height: Browser viewport height in pixels
            session_manager: Optional SessionManager instance (creates new if not provided)
        """
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self._playwright: Playwright | None = None
        self.session_manager = session_manager or SessionManager()

    async def launch(self, use_saved_session: bool = True) -> None:
        """
        Launch browser and create context.

        Args:
            use_saved_session: Load saved session state if available (default: True)
        """
        # Check for legacy session and migrate if needed
        if self.session_manager.legacy_session_path.exists():
            logger.info("Migrating legacy session to new location...")
            if self.session_manager.migrate_legacy_session():
                logger.info("Legacy session migrated successfully")

        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(headless=self.headless)

        # Try to load saved session state
        storage_state = None
        if use_saved_session:
            session_path = self.session_manager.get_session_path(ServiceType.KINDLE)
            if session_path.exists():
                try:
                    logger.info("Using saved Kindle session")
                    storage_state = str(session_path)
                except Exception as e:
                    logger.warning(f"Failed to load session state: {e}")

        self.context = await self.browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            storage_state=storage_state,
        )
        self.page = await self.context.new_page()

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def __aenter__(self) -> "KindleAutomation":
        """Async context manager entry."""
        await self.launch()
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def navigate_to_book(self, kindle_url: str, max_retries: int = 3) -> None:
        """
        Navigate to Kindle book URL and handle authentication.

        Args:
            kindle_url: Kindle Cloud Reader book URL
            max_retries: Maximum navigation retry attempts

        Raises:
            RuntimeError: If browser not launched or navigation fails after retries
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Navigating to Kindle URL (attempt {attempt}/{max_retries})"
                )

                # Navigate to the URL with timeout
                await self.page.goto(
                    kindle_url, wait_until="domcontentloaded", timeout=30000
                )

                # Check if authentication is required
                needs_auth = await self._is_auth_required()
                if needs_auth:
                    print("\n" + "=" * 60)
                    print("AUTHENTICATION REQUIRED")
                    print("=" * 60)
                    print("Please log in to Amazon in the browser window.")
                    print("After logging in, press Enter to continue...")
                    print("=" * 60 + "\n")

                    # Wait for user to complete authentication
                    input()

                    # Wait a moment for any redirects
                    await asyncio.sleep(2)

                # Wait for book reader to load
                await self._wait_for_book_reader()
                logger.info("Successfully navigated to book")

                # Save session if we just authenticated
                if needs_auth:
                    await self.save_session_state()

                return

            except PlaywrightTimeoutError as e:
                logger.error(
                    f"Navigation timeout on attempt {attempt}/{max_retries}: {e}"
                )
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Failed to navigate to book after {max_retries} attempts"
                    ) from e
                await asyncio.sleep(2)  # Wait before retry

            except Exception as e:
                logger.error(
                    f"Navigation error on attempt {attempt}/{max_retries}: {e}"
                )
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Failed to navigate to book: {type(e).__name__}: {e}"
                    ) from e
                await asyncio.sleep(2)

    async def _is_auth_required(self) -> bool:
        """
        Detect if authentication page is shown.

        Returns:
            True if authentication is required, False otherwise
        """
        if not self.page:
            return False

        # Check for Amazon login indicators
        auth_indicators = [
            'input[name="email"]',
            'input[id="ap_email"]',
            'input[name="password"]',
            "#signInSubmit",
        ]

        for selector in auth_indicators:
            if await self.page.locator(selector).count() > 0:
                return True

        return False

    async def _wait_for_book_reader(self, timeout: int = 30000) -> None:
        """
        Wait for Kindle book reader to fully load.

        Args:
            timeout: Maximum wait time in milliseconds

        Raises:
            TimeoutError: If book reader doesn't load within timeout
        """
        if not self.page:
            raise RuntimeError("Browser not launched.")

        # Wait for book canvas or content to be visible
        reader_selectors = [
            "canvas#KindleReaderCanvas",
            'div[id^="kr-renderer"]',
            'iframe[id^="KindleReaderIFrame"]',
        ]

        for selector in reader_selectors:
            try:
                await self.page.wait_for_selector(
                    selector, state="visible", timeout=timeout
                )
                # Additional wait for content to settle
                await asyncio.sleep(1)
                return
            except Exception:
                continue

        raise TimeoutError(f"Book reader failed to load within {timeout}ms")

    async def capture_screenshot(
        self, file_path: str | Path, full_page: bool = True
    ) -> Path:
        """
        Capture screenshot of current page.

        Args:
            file_path: Path to save screenshot
            full_page: Capture full scrollable page (default: True)

        Returns:
            Path to saved screenshot

        Raises:
            RuntimeError: If browser not launched or screenshot fails
        """
        if not self.page:
            raise RuntimeError("Browser not launched.")

        try:
            screenshot_path = Path(file_path)
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            await self.page.screenshot(path=str(screenshot_path), full_page=full_page)
            logger.debug(f"Screenshot saved: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            raise RuntimeError(f"Failed to capture screenshot: {e}") from e

    async def navigate_to_beginning(self, max_presses: int = 100) -> None:
        """
        Navigate to the beginning of the book.

        This method repeatedly presses the Left arrow key to navigate backwards
        until we reach the first page. This is more reliable than Home key for
        Kindle Cloud Reader.

        Args:
            max_presses: Maximum number of left arrow presses (default: 500)

        Raises:
            RuntimeError: If browser not launched
        """
        if not self.page:
            raise RuntimeError("Browser not launched.")

        logger.info("Navigating to beginning of book...")
        print("  Going back to page 1...", end="", flush=True)

        # Press left arrow many times to go back to start
        # Add small delay between presses so Kindle can process them
        for i in range(max_presses):
            await self.page.keyboard.press("ArrowLeft")
            # Small delay so Kindle reader can process the key press
            await asyncio.sleep(0.05)  # 50ms delay between presses

            # Show progress every 50 presses
            if (i + 1) % 50 == 0:
                print(f"\r  Going back to page 1... ({i + 1} presses)", end="", flush=True)

        print()  # New line after progress

        # Wait for final navigation to complete and page to settle
        await asyncio.sleep(3)

        logger.info("Navigation to beginning complete")

    async def turn_page(
        self,
        direction: Literal["next", "previous"] = "next",
        delay_min: float = 5.0,
        delay_max: float = 10.0,
    ) -> bool:
        """
        Turn to next or previous page.

        Args:
            direction: Page turn direction (next or previous)
            delay_min: Minimum delay in seconds before page turn
            delay_max: Maximum delay in seconds before page turn

        Returns:
            True if page turn successful, False otherwise
        """
        if not self.page:
            raise RuntimeError("Browser not launched.")

        # Add random human-like delay
        delay = random.uniform(delay_min, delay_max)
        await asyncio.sleep(delay)

        # Try keyboard navigation first
        key = "ArrowRight" if direction == "next" else "ArrowLeft"
        await self.page.keyboard.press(key)

        # Wait for page content to update
        await asyncio.sleep(0.5)

        # Verify page turned (content changed)
        # This is a simple check - in production you might compare screenshots
        return True

    async def save_session_state(self) -> None:
        """
        Save browser session state to file.

        Raises:
            RuntimeError: If browser context not available
        """
        if not self.context:
            raise RuntimeError("Browser context not available")

        try:
            session_path = self.session_manager.get_session_path(ServiceType.KINDLE)

            # Ensure parent directory exists
            session_path.parent.mkdir(parents=True, exist_ok=True)

            # Save session state
            await self.context.storage_state(path=str(session_path))

            # Set secure file permissions (owner read/write only)
            os.chmod(session_path, 0o600)

            logger.info(f"Kindle session saved to {session_path}")

        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
            raise RuntimeError(f"Failed to save session: {e}") from e

    async def validate_session(self, kindle_url: str) -> bool:
        """
        Validate if saved session is still valid by checking for auth requirement.

        Args:
            kindle_url: Kindle book URL to test

        Returns:
            True if session valid, False if authentication required
        """
        if not self.page:
            raise RuntimeError("Browser not launched")

        try:
            # Navigate to book URL
            await self.page.goto(
                kindle_url, wait_until="domcontentloaded", timeout=30000
            )

            # Check if authentication is required
            if await self._is_auth_required():
                logger.info("Session expired, re-authentication required")
                return False

            # Try to load book reader
            try:
                await self._wait_for_book_reader(timeout=10000)
                logger.info("Session is valid")
                return True
            except TimeoutError:
                logger.info("Session expired, re-authentication required")
                return False

        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False

    def calculate_screenshot_hash(self, screenshot_bytes: bytes) -> str:
        """
        Calculate SHA256 hash of screenshot for duplicate detection.

        Args:
            screenshot_bytes: Raw bytes of screenshot image

        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(screenshot_bytes).hexdigest()

    async def capture_full_book(
        self,
        kindle_url: str,
        book_title: str | None = None,
        book_author: str | None = None,
        max_pages: int = 1000,
        rewind_presses: int = 100,
        page_delay_min: float = 5.0,
        page_delay_max: float = 10.0,
    ) -> UUID:
        """
        Capture all pages of a Kindle book with progress tracking and database integration.

        Args:
            kindle_url: Kindle Cloud Reader book URL
            book_title: Book title (optional, will use URL if not provided)
            book_author: Book author (optional)
            max_pages: Maximum pages to capture (safety limit)

        Returns:
            Book UUID

        Raises:
            RuntimeError: If browser not launched or capture fails
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")

        # Generate book ID
        book_id = uuid4()
        screenshots_dir = Path(settings.screenshots_dir) / str(book_id)
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Track screenshot hashes for duplicate detection
        seen_hashes: set[str] = set()
        screenshot_records: list[Screenshot] = []

        # Progress tracking
        start_time = time.time()
        page_num = 0

        async with AsyncSessionLocal() as session:
            book_repo = BookRepository(session)
            screenshot_repo = ScreenshotRepository(session)

            try:
                # Create Book record
                book = Book(
                    id=book_id,
                    title=book_title or kindle_url,
                    author=book_author or "Unknown",
                    kindle_url=kindle_url,
                    total_screenshots=0,
                    ingestion_status="in_progress",
                )
                await book_repo.create(book)
                await session.commit()

                logger.info(f"Started capture for book {book_id}: {book.title}")
                print(f"\n{'='*70}")
                print(f"CAPTURING BOOK: {book.title}")
                print(f"Book ID: {book_id}")
                print(f"{'='*70}\n")

                # Navigate to book (will handle auth if needed)
                await self.navigate_to_book(kindle_url)

                # Navigate to beginning of book
                print("Navigating to beginning of book...")
                await self.navigate_to_beginning(max_presses=rewind_presses)
                print("✓ At beginning of book\n")

                # Capture loop
                while page_num < max_pages:
                    page_num += 1

                    # Capture screenshot
                    screenshot_path = screenshots_dir / f"page_{page_num:04d}.png"
                    await self.capture_screenshot(screenshot_path, full_page=False)

                    # Calculate hash
                    screenshot_bytes = screenshot_path.read_bytes()
                    screenshot_hash = self.calculate_screenshot_hash(screenshot_bytes)

                    # Check for duplicate (book end detection)
                    if screenshot_hash in seen_hashes:
                        logger.info(
                            f"Duplicate screenshot detected at page {page_num}. Book end reached."
                        )
                        print("\n✓ Book end detected (duplicate page)")
                        # Remove the duplicate screenshot
                        screenshot_path.unlink()
                        page_num -= 1
                        break

                    seen_hashes.add(screenshot_hash)

                    # Create Screenshot record
                    screenshot = Screenshot(
                        book_id=book_id,
                        sequence_number=page_num,
                        file_path=str(screenshot_path),
                        screenshot_hash=screenshot_hash,
                        captured_at=datetime.utcnow(),
                    )
                    screenshot_records.append(screenshot)
                    await screenshot_repo.create(screenshot)

                    # Progress display
                    elapsed = time.time() - start_time
                    rate = page_num / elapsed if elapsed > 0 else 0
                    print(
                        f"  📸 Page {page_num:4d} | {rate:5.2f} pages/sec | {elapsed:6.1f}s elapsed",
                        end="\r",
                    )

                    # Log every 10 pages
                    if page_num % 10 == 0:
                        await session.commit()
                        logger.info(f"Captured {page_num} pages")

                    # Turn to next page
                    success = await self.turn_page(
                        direction="next",
                        delay_min=page_delay_min,
                        delay_max=page_delay_max,
                    )
                    if not success:
                        logger.warning("Page turn may have failed")

                    # Check for book end indicators
                    is_end, reason = await self._is_book_end()
                    if is_end:
                        logger.info(f"Book end indicator detected at page {page_num}: {reason}")
                        print(f"\n\n⚠️  Possible book end detected at page {page_num}")
                        print(f"   Reason: {reason}")
                        print("\n💡 You can check the browser window to verify")

                        # Interactive prompt
                        while True:
                            response = input("\n❓ Is this the end of the book? (y/n): ").strip().lower()
                            if response in ['y', 'yes']:
                                print("✓ Stopping capture as confirmed by user")
                                logger.info("User confirmed book end")
                                break
                            elif response in ['n', 'no']:
                                print("✓ Continuing capture...")
                                logger.info("User rejected book end indicator, continuing")
                                break
                            else:
                                print("   Please enter 'y' for yes or 'n' for no")

                        # If user confirmed end, break the capture loop
                        if response in ['y', 'yes']:
                            break

                # Update Book record on success
                book.total_screenshots = page_num
                book.ingestion_status = "screenshots_complete"
                book.capture_date = datetime.utcnow()
                await book_repo.update(book)

                # Create ingestion log
                log_entry = IngestionLog(
                    book_id=book_id,
                    pipeline_stage="screenshot_capture",
                    status="completed",
                    log_metadata={"pages": page_num, "duration_seconds": elapsed},
                )
                session.add(log_entry)
                await session.commit()

                # Summary
                elapsed_total = time.time() - start_time
                avg_rate = page_num / elapsed_total if elapsed_total > 0 else 0
                print(f"\n\n{'='*70}")
                print("✅ CAPTURE COMPLETE")
                print(f"{'='*70}")
                print(f"  Total Pages: {page_num}")
                print(f"  Duration: {elapsed_total:.1f}s")
                print(f"  Average Rate: {avg_rate:.2f} pages/sec")
                print(f"  Screenshots: {screenshots_dir}")
                print(f"{'='*70}\n")

                logger.info(
                    f"Book capture complete: {page_num} pages in {elapsed_total:.1f}s"
                )

                return book_id

            except Exception as e:
                # Error handling
                logger.error(f"Book capture failed: {e}")

                # Update Book record with error
                if "book" in locals():
                    book.ingestion_status = "failed"
                    book.ingestion_error = str(e)
                    await book_repo.update(book)

                    # Create error log entry
                    error_log = IngestionLog(
                        book_id=book_id,
                        pipeline_stage="screenshot_capture",
                        status="failed",
                        error_message=f"Capture failed at page {page_num}: {str(e)}",
                        log_metadata={
                            "pages_captured": page_num,
                            "error_type": type(e).__name__,
                        },
                    )
                    session.add(error_log)
                    await session.commit()

                print(f"\n❌ CAPTURE FAILED: {e}\n")
                raise RuntimeError(f"Book capture failed: {e}") from e

    async def _is_book_end(self) -> tuple[bool, str | None]:
        """
        Check if we've reached the end of the book based on UI indicators.

        Returns:
            Tuple of (is_end, reason):
            - is_end: True if book end detected, False otherwise
            - reason: Description of why book end was detected (or None)
        """
        if not self.page:
            return False, None

        try:
            # Check if next page button is disabled or missing
            next_button_selectors = [
                'button[aria-label="Next Page"]',
                'button[title="Next Page"]',
                "#kr-page-button-next",
            ]

            for selector in next_button_selectors:
                button = await self.page.query_selector(selector)
                if button:
                    is_disabled = await button.is_disabled()
                    if is_disabled:
                        return True, '"Next Page" button is disabled'

            # Check for "end of book" text indicators
            end_indicators = ["End of Book", "The End", "Fin"]
            for indicator in end_indicators:
                if await self.page.locator(f"text={indicator}").count() > 0:
                    return True, f'Found text indicator: "{indicator}"'

        except Exception as e:
            logger.debug(f"Error checking book end: {e}")

        return False, None
