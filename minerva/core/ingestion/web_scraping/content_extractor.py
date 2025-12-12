"""Content extraction module - extract text and metadata from HTML pages."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import trafilatura
from bs4 import BeautifulSoup
from readability import Document

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Extracted content from a webpage."""

    url: str
    text: str
    title: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    description: Optional[str] = None
    word_count: int = 0
    domain: Optional[str] = None

    def __post_init__(self):
        """Calculate word count and domain after initialization."""
        if not self.word_count and self.text:
            self.word_count = len(self.text.split())
        if not self.domain and self.url:
            self.domain = urlparse(self.url).netloc


@dataclass
class ExtractionConfig:
    """Configuration for content extraction."""

    use_ai_extraction: bool = False
    min_word_count: int = 50
    min_text_to_html_ratio: float = 0.1


class ContentExtractor:
    """Extract clean text and metadata from HTML pages.

    Uses a priority cascade approach:
    1. Trafilatura (fast, accurate for most sites)
    2. Readability (fallback for complex layouts)
    3. AI extraction (optional, for difficult cases)
    """

    def __init__(self, config: Optional[ExtractionConfig] = None):
        """Initialize content extractor with configuration."""
        self.config = config or ExtractionConfig()

    def extract_content(self, url: str, html: str) -> Optional[ExtractedContent]:
        """Extract content using priority cascade: Trafilatura → Readability → AI.

        Args:
            url: The URL of the page being extracted
            html: The HTML content of the page

        Returns:
            ExtractedContent object or None if extraction failed
        """
        logger.info(f"Extracting content from {url}")

        # Try Trafilatura first (best results for most sites)
        text = self._extract_with_trafilatura(html)
        if text and self._quality_check(text, html):
            logger.debug(f"Trafilatura extraction successful for {url}")
            metadata = self._extract_metadata(html, url)
            return ExtractedContent(url=url, text=text, **metadata)

        # Fall back to Readability
        text = self._extract_with_readability(html)
        if text and self._quality_check(text, html):
            logger.debug(f"Readability extraction successful for {url}")
            metadata = self._extract_metadata(html, url)
            return ExtractedContent(url=url, text=text, **metadata)

        # TODO: AI extraction (implement in v1.1)
        if self.config.use_ai_extraction:
            logger.warning(f"AI extraction not yet implemented for {url}")

        # Last resort: basic HTML stripping
        text = self._extract_basic(html)
        if text and self._quality_check(text, html):
            logger.warning(f"Using basic extraction for {url} (lower quality)")
            metadata = self._extract_metadata(html, url)
            return ExtractedContent(url=url, text=text, **metadata)

        logger.error(f"Failed to extract quality content from {url}")
        return None

    def _extract_with_trafilatura(self, html: str) -> Optional[str]:
        """Extract main content using Trafilatura library.

        Args:
            html: HTML content to extract from

        Returns:
            Extracted text or None if extraction failed
        """
        try:
            text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,  # Keep tables for data-rich content
                no_fallback=False,  # Use fallback extraction if needed
                favor_precision=True,  # Prefer precision over recall
            )
            return text
        except Exception as e:
            logger.debug(f"Trafilatura extraction failed: {e}")
            return None

    def _extract_with_readability(self, html: str) -> Optional[str]:
        """Extract main content using Mozilla Readability algorithm.

        Args:
            html: HTML content to extract from

        Returns:
            Extracted text or None if extraction failed
        """
        try:
            doc = Document(html)
            # Readability returns HTML, so we need to strip tags
            summary_html = doc.summary()
            soup = BeautifulSoup(summary_html, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            return text
        except Exception as e:
            logger.debug(f"Readability extraction failed: {e}")
            return None

    def _extract_basic(self, html: str) -> Optional[str]:
        """Basic HTML tag stripping as last resort.

        Args:
            html: HTML content to extract from

        Returns:
            Extracted text or None if extraction failed
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Remove script, style, and other non-content tags
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # Get text
            text = soup.get_text(separator="\n", strip=True)

            # Clean up excessive whitespace
            text = re.sub(r"\n\s*\n+", "\n\n", text)

            return text
        except Exception as e:
            logger.debug(f"Basic extraction failed: {e}")
            return None

    def _extract_metadata(self, html: str, url: str) -> dict:
        """Extract metadata using priority cascade: meta tags → Schema.org → inference.

        Args:
            html: HTML content to parse
            url: URL of the page (for context)

        Returns:
            Dictionary with metadata fields
        """
        soup = BeautifulSoup(html, "html.parser")
        metadata = {}

        # 1. Try OpenGraph tags first (most reliable)
        og_title = soup.find("meta", property="og:title")
        og_description = soup.find("meta", property="og:description")
        og_author = soup.find("meta", property="og:author")

        if og_title:
            metadata["title"] = og_title.get("content")
        if og_description:
            metadata["description"] = og_description.get("content")
        if og_author:
            metadata["author"] = og_author.get("content")

        # 2. Try standard meta tags
        if not metadata.get("title"):
            title_tag = soup.find("title")
            if title_tag:
                metadata["title"] = title_tag.get_text(strip=True)

        if not metadata.get("description"):
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                metadata["description"] = meta_desc.get("content")

        if not metadata.get("author"):
            meta_author = soup.find("meta", attrs={"name": "author"})
            if meta_author:
                metadata["author"] = meta_author.get("content")

        # 3. Try to extract published date
        published_date = self._extract_published_date(soup)
        if published_date:
            metadata["published_date"] = published_date

        # 4. Set defaults for missing fields
        if not metadata.get("title"):
            metadata["title"] = "Untitled"
        if not metadata.get("author"):
            metadata["author"] = urlparse(url).netloc  # Use domain as author
        if not metadata.get("description"):
            metadata["description"] = ""

        return metadata

    def _extract_published_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract published date from various HTML patterns.

        Args:
            soup: BeautifulSoup object of the HTML

        Returns:
            datetime object or None if no date found
        """
        # Try meta tags first
        date_patterns = [
            ("meta", {"property": "article:published_time"}),
            ("meta", {"name": "publishdate"}),
            ("meta", {"name": "date"}),
            ("meta", {"property": "og:published_time"}),
            ("time", {"class": "published"}),
            ("time", {"class": "entry-date"}),
        ]

        for tag_name, attrs in date_patterns:
            tag = soup.find(tag_name, attrs=attrs)
            if tag:
                date_str = tag.get("content") or tag.get("datetime") or tag.get_text()
                if date_str:
                    parsed_date = self._parse_date_string(date_str)
                    if parsed_date:
                        return parsed_date

        return None

    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date string using multiple formats.

        Args:
            date_str: String representation of a date

        Returns:
            datetime object or None if parsing failed
        """
        # Common date formats
        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
            "%Y-%m-%dT%H:%M:%S",  # ISO 8601 without timezone
            "%Y-%m-%d %H:%M:%S",  # SQL datetime
            "%Y-%m-%d",  # Simple date
            "%B %d, %Y",  # January 1, 2025
            "%b %d, %Y",  # Jan 1, 2025
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except (ValueError, AttributeError):
                continue

        return None

    def _quality_check(self, text: str, html: str) -> bool:
        """Check if extracted content meets quality thresholds.

        Args:
            text: Extracted text content
            html: Original HTML

        Returns:
            True if content meets quality standards
        """
        if not text:
            return False

        # Check minimum word count
        word_count = len(text.split())
        if word_count < self.config.min_word_count:
            logger.debug(f"Content failed quality check: only {word_count} words")
            return False

        # Check text-to-HTML ratio (avoid pages with mostly navigation)
        html_length = len(html)
        text_length = len(text)

        if html_length > 0:
            ratio = text_length / html_length
            if ratio < self.config.min_text_to_html_ratio:
                logger.debug(
                    f"Content failed quality check: text/HTML ratio {ratio:.2f} too low"
                )
                return False

        return True
