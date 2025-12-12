"""Website scraping module for Minerva.

This module provides comprehensive website scraping functionality including:
- Content discovery via sitemap.xml or link crawling
- Clean text extraction using Trafilatura and Readability
- Metadata extraction (title, author, published date)
- Deduplication at page and chunk levels
- Integration with Minerva's semantic chunking and embedding pipeline
"""

from minerva.core.ingestion.web_scraping.content_extractor import (
    ContentExtractor,
    ExtractedContent,
    ExtractionConfig,
)
from minerva.core.ingestion.web_scraping.content_processor import ContentProcessor
from minerva.core.ingestion.web_scraping.web_scraper_orchestrator import (
    ScrapeConfig,
    ScrapeResult,
    SuccessfulPage,
    WebScraperOrchestrator,
)
from minerva.core.ingestion.web_scraping.website_discovery import (
    DiscoveryConfig,
    WebsiteDiscovery,
)

__all__ = [
    "ContentExtractor",
    "ExtractedContent",
    "ExtractionConfig",
    "ContentProcessor",
    "WebsiteDiscovery",
    "DiscoveryConfig",
    "WebScraperOrchestrator",
    "ScrapeConfig",
    "ScrapeResult",
    "SuccessfulPage",
]
