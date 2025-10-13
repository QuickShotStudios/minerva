"""Text extraction from screenshots using Tesseract OCR."""

import subprocess
import time
from pathlib import Path
from typing import Any

import structlog

from minerva.config import settings
from minerva.core.ingestion.text_cleaner import TextCleaner
from minerva.utils.exceptions import TextExtractionError

logger = structlog.get_logger(__name__)

# AI formatting pricing constants (gpt-4o-mini as of 2025-01)
AI_FORMATTING_INPUT_PRICE_PER_1M = 0.15  # USD per 1M input tokens
AI_FORMATTING_OUTPUT_PRICE_PER_1M = 0.60  # USD per 1M output tokens

# Optional AI formatting prompt (if USE_AI_FORMATTING enabled)
AI_FORMATTING_PROMPT = """Clean this OCR-extracted text by:
1. Removing OCR artifacts (misread characters, formatting glitches)
2. Standardizing paragraph breaks and structure
3. Fixing obvious OCR errors (e.g., 'l' misread as '1', 'O' as '0')
4. Preserving ALL original content - do not summarize or omit
5. Return only the cleaned text, no explanations or commentary."""


class TextExtractor:
    """
    Extract text from screenshot images using Tesseract OCR.

    This class handles:
    - Tesseract OCR invocation via subprocess
    - Error handling for OCR failures
    - Optional AI-powered formatting cleanup
    - Processing time tracking
    - OCR method recording for traceability

    Optionally applies AI-powered formatting cleanup if enabled via settings.
    """

    def __init__(
        self,
        tesseract_cmd: str | None = None,
        use_ai_formatting: bool | None = None,
        filter_kindle_ui: bool | None = None,
    ) -> None:
        """
        Initialize TextExtractor with Tesseract configuration.

        Args:
            tesseract_cmd: Path to tesseract binary (defaults to settings.tesseract_cmd)
            use_ai_formatting: Whether to apply AI formatting (defaults to settings.use_ai_formatting)
            filter_kindle_ui: Whether to filter Kindle UI elements (defaults to settings.filter_kindle_ui)
        """
        self.tesseract_cmd = tesseract_cmd or settings.tesseract_cmd
        self.use_ai_formatting = (
            use_ai_formatting
            if use_ai_formatting is not None
            else settings.use_ai_formatting
        )
        self.filter_kindle_ui = (
            filter_kindle_ui
            if filter_kindle_ui is not None
            else settings.filter_kindle_ui
        )
        self.text_cleaner = TextCleaner() if self.filter_kindle_ui else None
        self._verify_tesseract_installed()

    def _verify_tesseract_installed(self) -> None:
        """
        Verify Tesseract is installed and accessible.

        Raises:
            TextExtractionError: If tesseract binary not found
        """
        try:
            result = subprocess.run(
                [self.tesseract_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise TextExtractionError(
                    "Tesseract not working properly. Install with: brew install tesseract"
                )
            version_line = result.stdout.split("\n")[0]
            logger.info("tesseract_verified", version=version_line)
        except FileNotFoundError as e:
            raise TextExtractionError(
                "Tesseract not found. Install with: brew install tesseract"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise TextExtractionError(
                "Tesseract version check timed out. Check installation."
            ) from e

    async def extract_text_from_screenshot(
        self,
        file_path: Path,
        book_id: str | None = None,
        screenshot_id: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Extract text from screenshot using Tesseract OCR.

        Args:
            file_path: Path to screenshot image file
            book_id: Optional book ID for logging context
            screenshot_id: Optional screenshot ID for logging context

        Returns:
            Tuple of (extracted_text, metadata) where metadata includes:
                - ocr_method: "tesseract"
                - tesseract_version: Version string
                - use_ai_formatting: Whether AI cleanup was applied
                - cost_estimate: AI formatting cost (if applied), otherwise 0
                - processing_time_ms: Time taken for OCR + formatting

        Raises:
            TextExtractionError: If extraction fails
            FileNotFoundError: If screenshot file doesn't exist

        Example:
            ```python
            extractor = TextExtractor()
            text, metadata = await extractor.extract_text_from_screenshot(
                Path("screenshot.png"),
                book_id="abc123"
            )
            print(f"Extracted: {text[:100]}...")
            print(f"Cost: ${metadata['cost_estimate']:.4f}")
            ```
        """
        start_time = time.time()

        try:
            # Run Tesseract OCR
            raw_text = self._run_tesseract(file_path)

            # Apply Kindle UI filtering if enabled (before AI formatting)
            if self.text_cleaner and raw_text.strip():
                filtered_text = self.text_cleaner.clean(raw_text)
                chars_removed = len(raw_text) - len(filtered_text)
            else:
                filtered_text = raw_text
                chars_removed = 0

            # Optional AI formatting pass
            if self.use_ai_formatting and filtered_text.strip():
                formatted_text, ai_cost = await self._apply_ai_formatting(filtered_text)
            else:
                formatted_text = filtered_text
                ai_cost = 0.0

            processing_time_ms = int((time.time() - start_time) * 1000)

            metadata = {
                "ocr_method": "tesseract",
                "tesseract_version": self._get_tesseract_version(),
                "use_ai_formatting": self.use_ai_formatting,
                "filter_kindle_ui": self.filter_kindle_ui,
                "kindle_ui_chars_removed": chars_removed,
                "cost_estimate": ai_cost,
                "processing_time_ms": processing_time_ms,
            }

            logger.info(
                "text_extraction_success",
                file_path=str(file_path),
                book_id=book_id,
                screenshot_id=screenshot_id,
                text_length=len(formatted_text),
                ai_formatting_applied=self.use_ai_formatting,
                kindle_ui_filtered=self.filter_kindle_ui,
                ui_chars_removed=chars_removed,
                processing_time_ms=processing_time_ms,
            )

            return formatted_text, metadata

        except Exception as e:
            logger.error(
                "text_extraction_failed",
                file_path=str(file_path),
                book_id=book_id,
                screenshot_id=screenshot_id,
                error=str(e),
            )
            raise

    def _run_tesseract(self, file_path: Path) -> str:
        """
        Run Tesseract OCR on image file.

        Args:
            file_path: Path to image file

        Returns:
            Extracted text from OCR

        Raises:
            FileNotFoundError: If image file doesn't exist
            TextExtractionError: If OCR fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Screenshot file not found: {file_path}")

        try:
            # Tesseract PSM 3 = automatic page segmentation with OSD
            # Language: eng (English) - explicit for clarity (AC 5)
            # Output to stdout instead of creating temp file
            result = subprocess.run(
                [
                    self.tesseract_cmd,
                    str(file_path),
                    "stdout",
                    "-l",
                    "eng",
                    "--psm",
                    "3",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise TextExtractionError(
                    f"Tesseract OCR failed: {result.stderr.strip()}"
                )

            return result.stdout

        except subprocess.TimeoutExpired as e:
            raise TextExtractionError(
                f"Tesseract OCR timeout on {file_path} (>30s)"
            ) from e
        except Exception as e:
            raise TextExtractionError(
                f"Tesseract OCR error on {file_path}: {str(e)}"
            ) from e

    async def _apply_ai_formatting(self, raw_text: str) -> tuple[str, float]:
        """
        Apply AI formatting cleanup to remove OCR artifacts.

        Args:
            raw_text: Raw OCR output text

        Returns:
            Tuple of (formatted_text, cost_estimate)

        Raises:
            TextExtractionError: If AI formatting fails (falls back to raw_text)
        """
        try:
            from minerva.utils.openai_client import get_openai_client

            client = get_openai_client()
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": AI_FORMATTING_PROMPT},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.3,
                timeout=30.0,
            )

            formatted_text = response.choices[0].message.content or raw_text

            # Calculate cost using pricing constants
            usage = response.usage
            if usage:
                cost = (
                    usage.prompt_tokens * AI_FORMATTING_INPUT_PRICE_PER_1M / 1_000_000
                ) + (
                    usage.completion_tokens
                    * AI_FORMATTING_OUTPUT_PRICE_PER_1M
                    / 1_000_000
                )
            else:
                cost = 0.0

            logger.info(
                "ai_formatting_applied",
                raw_text_length=len(raw_text),
                formatted_text_length=len(formatted_text),
                cost=cost,
            )

            return formatted_text, cost

        except Exception as e:
            logger.warning(
                "ai_formatting_failed_fallback_to_raw",
                error=str(e),
            )
            # Fall back to raw OCR text if AI formatting fails
            return raw_text, 0.0

    def _get_tesseract_version(self) -> str:
        """
        Get Tesseract version string.

        Returns:
            Version string like "tesseract 5.3.0"
        """
        try:
            result = subprocess.run(
                [self.tesseract_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.split("\n")[0]
        except Exception:
            return "tesseract (version unknown)"
