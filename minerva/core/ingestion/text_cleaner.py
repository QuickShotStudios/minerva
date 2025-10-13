"""Text cleaning utilities to remove Kindle UI elements and OCR artifacts."""

import re

import structlog

logger = structlog.get_logger(__name__)


class TextCleaner:
    """
    Clean extracted text by removing Kindle UI elements and noise.

    This class handles:
    - Removal of Kindle Cloud Reader UI elements (page numbers, progress bars)
    - Filtering navigation text (Kindle Library, Learning reading speed)
    - Cleaning OCR artifacts while preserving book content
    - Configurable filtering patterns

    Common Kindle UI patterns removed:
    - "Page x of y » z%"
    - "Kindle Library"
    - "Learning reading speed"
    - Progress indicators and navigation elements
    """

    # Regex patterns for Kindle UI elements
    KINDLE_UI_PATTERNS = [
        # Page indicators: "Page x of y » z%" or "Page x of y"
        r"Page\s+[ivxlcdm\d]+\s+of\s+\d+\s*[»›]?\s*\d*%?",
        # Location indicators: "Location 2 of 2771 « 0%"
        r"Location\s+\d+\s+of\s+\d+\s*[«»›]?\s*\d*%?",
        # Kindle Library text
        r"Kindle\s+Library",
        # Learning/reading speed indicators
        r"Learning\s+reading\s+speed[,.\s]*[+\-]?",
        # Progress bar artifacts (percentage with arrow symbols)
        # Must have arrow/navigation symbol to distinguish from content percentages
        r"[»›«]\s*\d+%",  # "» 39%" or "› 5%" or "« 0%"
        r"\d+%\s*[►▶→»›«]",  # "39% »" or "5% ›"
        # Navigation symbols and artifacts
        r"[►▶→»›«]{2,}",
        # Common Kindle navigation text
        r"(?:Back\s+to\s+)?(?:Table\s+of\s+)?Contents",
        # Font/display controls (often appear as artifacts)
        r"[Aa]a\s+[Aa]\s+[Aa]",
        # Sync status messages
        r"Synced\s+to\s+page\s+\d+",
        # Bookmark/highlight UI
        r"(?:Add\s+)?(?:Bookmark|Highlight|Note)",
    ]

    # Compiled patterns for performance
    _compiled_patterns: list[re.Pattern] = []

    def __init__(self, custom_patterns: list[str] | None = None) -> None:
        """
        Initialize TextCleaner with filtering patterns.

        Args:
            custom_patterns: Optional additional regex patterns to filter
        """
        # Compile all patterns
        patterns = self.KINDLE_UI_PATTERNS.copy()
        if custom_patterns:
            patterns.extend(custom_patterns)

        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in patterns
        ]

        logger.info("text_cleaner_initialized", pattern_count=len(self._compiled_patterns))

    def clean(self, text: str, aggressive: bool = False) -> str:
        """
        Clean text by removing Kindle UI elements.

        Args:
            text: Raw text to clean
            aggressive: If True, apply more aggressive cleaning (may remove edge cases)

        Returns:
            Cleaned text with UI elements removed

        Example:
            ```python
            cleaner = TextCleaner()
            raw_text = "Page 10 of 200 » 5%\\n\\nActual book content here..."
            cleaned = cleaner.clean(raw_text)
            # Returns: "Actual book content here..."
            ```
        """
        if not text or not text.strip():
            return ""

        original_length = len(text)
        cleaned_text = text

        # Apply each pattern
        for pattern in self._compiled_patterns:
            cleaned_text = pattern.sub("", cleaned_text)

        # Additional aggressive cleaning if requested
        if aggressive:
            cleaned_text = self._aggressive_clean(cleaned_text)

        # Normalize whitespace
        cleaned_text = self._normalize_whitespace(cleaned_text)

        # Return empty string if only whitespace remains
        if not cleaned_text or not cleaned_text.strip():
            return ""

        removed_chars = original_length - len(cleaned_text)
        if removed_chars > 0:
            logger.debug(
                "text_cleaned",
                original_length=original_length,
                cleaned_length=len(cleaned_text),
                removed_chars=removed_chars,
                removal_percentage=round(removed_chars / original_length * 100, 2),
            )

        return cleaned_text

    def _aggressive_clean(self, text: str) -> str:
        """
        Apply aggressive cleaning patterns (use cautiously).

        Args:
            text: Text to clean

        Returns:
            More aggressively cleaned text
        """
        # Remove standalone numbers that might be page numbers
        text = re.sub(r"^\d+$", "", text, flags=re.MULTILINE)

        # Remove very short lines (< 3 chars) that are likely UI artifacts
        lines = text.split("\n")
        lines = [line for line in lines if len(line.strip()) >= 3 or line.strip() == ""]
        text = "\n".join(lines)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace after cleaning.

        Args:
            text: Text with potential whitespace issues

        Returns:
            Text with normalized whitespace
        """
        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in text.split("\n")]

        # Remove excessive blank lines (more than 2 consecutive)
        normalized_lines = []
        blank_count = 0

        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:
                    normalized_lines.append(line)
            else:
                blank_count = 0
                normalized_lines.append(line)

        text = "\n".join(normalized_lines)

        # Remove leading/trailing whitespace from entire text
        text = text.strip()

        return text

    def get_statistics(self, original: str, cleaned: str) -> dict[str, int | float]:
        """
        Get statistics about the cleaning operation.

        Args:
            original: Original text before cleaning
            cleaned: Text after cleaning

        Returns:
            Dictionary with statistics (chars_removed, lines_removed, etc.)
        """
        original_lines = original.split("\n")
        cleaned_lines = cleaned.split("\n")

        return {
            "original_chars": len(original),
            "cleaned_chars": len(cleaned),
            "chars_removed": len(original) - len(cleaned),
            "removal_percentage": round(
                (len(original) - len(cleaned)) / len(original) * 100, 2
            )
            if original
            else 0,
            "original_lines": len(original_lines),
            "cleaned_lines": len(cleaned_lines),
            "lines_removed": len(original_lines) - len(cleaned_lines),
        }
