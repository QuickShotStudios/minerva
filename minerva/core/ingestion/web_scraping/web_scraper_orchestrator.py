"""Web scraper orchestrator - coordinates all website scraping components."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse
from uuid import UUID, uuid4

from playwright.async_api import Browser, async_playwright
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.core.ingestion.embedding_generator import EmbeddingGenerator
from minerva.core.ingestion.semantic_chunking import ChunkMetadata, SemanticChunker
from minerva.core.ingestion.web_scraping.content_extractor import (
    ContentExtractor,
    ExtractedContent,
    ExtractionConfig,
)
from minerva.core.ingestion.web_scraping.content_processor import ContentProcessor
from minerva.core.ingestion.web_scraping.website_discovery import (
    DiscoveryConfig,
    WebsiteDiscovery,
)
from minerva.db.models import Book, Chunk, FailedScrape, SourceType
from minerva.db.models.embedding_config import EmbeddingConfig
from minerva.utils.token_counter import count_tokens

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic."""

    max_retries: int = 3
    base_delay_ms: int = 1000
    backoff_multiplier: float = 2.0


@dataclass
class ScrapeConfig:
    """Complete scraping configuration."""

    discovery: DiscoveryConfig
    extraction: ExtractionConfig
    retry: RetryConfig = None
    rate_limit_delay_ms: int = 200

    def __post_init__(self):
        """Set default retry config if not provided."""
        if self.retry is None:
            self.retry = RetryConfig()


@dataclass
class FailedPage:
    """Record of a failed page scrape."""

    url: str
    error: str
    retry_count: int = 0


@dataclass
class SuccessfulPage:
    """Record of a successful page scrape."""

    url: str
    title: Optional[str] = None
    word_count: int = 0
    extraction_method: str = "trafilatura"


@dataclass
class ScrapeResult:
    """Result of a scraping operation."""

    book_id: UUID
    success_count: int = 0
    failure_count: int = 0
    total_words: int = 0
    total_chunks: int = 0
    failures: List[FailedPage] = None
    successes: List[SuccessfulPage] = None

    def __post_init__(self):
        if self.failures is None:
            self.failures = []
        if self.successes is None:
            self.successes = []

    @property
    def error_rate(self) -> float:
        """Calculate error rate for adaptive rate limiting."""
        total = self.success_count + self.failure_count
        return self.failure_count / total if total > 0 else 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0.0


class WebScraperOrchestrator:
    """Coordinate website scraping pipeline.

    Orchestrates all scraping components:
    - Discovery (sitemap/crawling)
    - Content extraction
    - Deduplication
    - Chunking
    - Embedding generation
    - Database storage
    """

    def __init__(self, session: AsyncSession, config: Optional[ScrapeConfig] = None):
        """Initialize orchestrator with database session and configuration."""
        self.session = session
        self.config = config or ScrapeConfig(
            discovery=DiscoveryConfig(),
            extraction=ExtractionConfig(),
            retry=RetryConfig(),
        )

        # Initialize components
        self.discovery = WebsiteDiscovery(self.config.discovery)
        self.extractor = ContentExtractor(self.config.extraction)
        self.processor = ContentProcessor()

    async def scrape_website(
        self,
        url: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        browser: Optional[Browser] = None,
    ) -> ScrapeResult:
        """Main scraping pipeline.

        Args:
            url: Starting URL to scrape
            title: Optional title (will be detected from first page if not provided)
            author: Optional author (will use domain if not provided)
            browser: Playwright browser instance (if None, will create one)

        Returns:
            ScrapeResult with statistics and failures
        """
        logger.info(f"Starting website scrape: {url}")

        # If browser not provided, create one
        if browser is None:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    return await self._do_scrape(url, title, author, browser)
                finally:
                    await browser.close()
        else:
            # Use provided browser
            return await self._do_scrape(url, title, author, browser)

    async def _do_scrape(
        self, url: str, title: Optional[str], author: Optional[str], browser: Browser
    ) -> ScrapeResult:
        """Internal scraping logic."""
        # Step 1: Create book record
        book = await self._create_book_record(url, title, author)
        result = ScrapeResult(book_id=book.id)

        # Step 2: Discover pages
        logger.info("Discovering pages...")
        pages_to_scrape = await self.discovery.discover_pages(url, browser)
        logger.info(f"Found {len(pages_to_scrape)} pages to scrape")

        if not pages_to_scrape:
            logger.warning("No pages found to scrape")
            await self._update_book_status(book.id, "failed", "No pages found")
            return result

        # Step 3: Scrape pages
        logger.info("Scraping pages...")
        extracted_pages = await self._scrape_pages(pages_to_scrape, book.id, result, browser)

        if not extracted_pages:
            logger.error("No pages successfully scraped")
            await self._update_book_status(book.id, "failed", "All pages failed to scrape")
            return result

        # Step 4: Deduplicate pages
        logger.info("Deduplicating pages...")
        unique_pages = self.processor.deduplicate_pages(extracted_pages)

        # Step 5: Update book metadata with info from first page
        if unique_pages:
            await self._update_book_metadata(book.id, unique_pages[0])

        # Step 6: Chunk content
        logger.info("Chunking content...")
        chunks = await self._chunk_content(unique_pages, book.id)
        result.total_chunks = len(chunks)

        # Step 7: Deduplicate chunks
        logger.info("Deduplicating chunks...")
        unique_chunks_data = self.processor.deduplicate_chunks(
            [{"id": str(i), "text": c.chunk_text} for i, c in enumerate(chunks)]
        )
        unique_chunk_ids = {int(c["id"]) for c in unique_chunks_data}
        unique_chunks = [c for i, c in enumerate(chunks) if i in unique_chunk_ids]

        # Step 8: Generate embeddings
        logger.info(f"Generating embeddings for {len(unique_chunks)} chunks...")
        await self._generate_embeddings(unique_chunks, book.id)

        # Step 9: Update final book status
        total_words = sum(p.word_count for p in unique_pages)
        result.total_words = total_words

        await self._update_book_final_status(
            book.id,
            page_count=len(pages_to_scrape),
            word_count=total_words,
        )

        logger.info(
            f"Scraping complete: {result.success_count} pages, "
            f"{result.failure_count} failures, {result.total_chunks} chunks"
        )

        return result

    async def _create_book_record(
        self, url: str, title: Optional[str], author: Optional[str]
    ) -> Book:
        """Create initial book record in database."""
        domain = urlparse(url).netloc

        book = Book(
            id=uuid4(),
            title=title or f"Website: {domain}",
            author=author or domain,
            source_type=SourceType.WEBSITE,
            source_url=url,
            source_domain=domain,
            ingestion_status="in_progress",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)

        logger.info(f"Created book record: {book.id}")
        return book

    async def _scrape_pages(
        self, urls: List[str], book_id: UUID, result: ScrapeResult, browser: Browser
    ) -> List[ExtractedContent]:
        """Scrape all pages with retry logic and error handling."""
        extracted_pages = []

        for url in urls:
            try:
                # Fetch page with retry
                html = await self._fetch_page_with_retry(browser, url)

                # Extract content
                content = self.extractor.extract_content(url, html)

                if content:
                    extracted_pages.append(content)
                    result.success_count += 1

                    # Track successful page details
                    result.successes.append(SuccessfulPage(
                        url=url,
                        title=content.title,
                        word_count=content.word_count,
                        extraction_method="trafilatura"  # Could be enhanced to track actual method used
                    ))
                else:
                    raise Exception("Content extraction failed (quality check)")

            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")
                result.failure_count += 1
                result.failures.append(FailedPage(url=url, error=str(e)))

                # Save failed scrape to database
                await self._save_failed_scrape(book_id, url, str(e))

            # Adaptive rate limiting
            await self._adaptive_delay(result.error_rate)

        return extracted_pages

    async def _fetch_page_with_retry(self, browser: Browser, url: str) -> str:
        """Fetch page HTML with retry logic and exponential backoff."""
        for attempt in range(self.config.retry.max_retries):
            try:
                page = await browser.new_page()

                # Navigate to page and wait for content
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # Handle dynamic content (pagination, infinite scroll, etc.)
                await self._handle_dynamic_content(page)

                # Get HTML content
                html = await page.content()
                await page.close()

                return html

            except Exception as e:
                if attempt == self.config.retry.max_retries - 1:
                    # Final attempt failed
                    raise

                # Calculate backoff delay
                backoff = self.config.retry.base_delay_ms * (
                    self.config.retry.backoff_multiplier ** attempt
                )
                logger.debug(f"Retry {attempt + 1} for {url}, waiting {backoff}ms")
                await asyncio.sleep(backoff / 1000)

    async def _handle_dynamic_content(self, page) -> None:
        """Handle dynamic content (pagination, infinite scroll)."""
        try:
            # Check for pagination buttons
            pagination_selectors = [
                'a[rel="next"]',
                ".next-page",
                ".load-more",
                'button:has-text("Load More")',
                '[aria-label="Next"]',
            ]

            for selector in pagination_selectors:
                button = await page.query_selector(selector)
                if button:
                    logger.debug(f"Found pagination button: {selector}")
                    await button.click()
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    # Recursively check for more pagination
                    return await self._handle_dynamic_content(page)

            # Check for infinite scroll
            prev_height = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            new_height = await page.evaluate("document.body.scrollHeight")

            if new_height > prev_height:
                logger.debug("Detected infinite scroll, continuing...")
                return await self._handle_dynamic_content(page)

        except Exception as e:
            logger.debug(f"Dynamic content handling error (non-fatal): {e}")

    async def _adaptive_delay(self, error_rate: float) -> None:
        """Adjust delay based on recent error rate."""
        if error_rate > 0.2:  # >20% errors
            delay = 2000
        elif error_rate > 0.1:  # >10% errors
            delay = 1000
        else:
            delay = self.config.rate_limit_delay_ms

        await asyncio.sleep(delay / 1000)

    async def _chunk_content(
        self, pages: List[ExtractedContent], book_id: UUID
    ) -> List[ChunkMetadata]:
        """Chunk content using semantic chunker."""
        # Combine all page text with separators
        full_text = "\n\n---PAGE_BREAK---\n\n".join(p.text for p in pages)

        # Preprocess text to ensure proper paragraph breaks
        # This helps the chunker work correctly with content that lacks structure
        full_text = self._ensure_paragraph_breaks(full_text)

        # Use existing semantic chunker with appropriate token limits for embedding model
        # Embedding model (text-embedding-3-small) has 8192 token limit
        # Use 800 tokens per chunk with 15% overlap to stay well under limit
        chunker = SemanticChunker(
            chunk_size_tokens=800,
            chunk_overlap_percentage=0.15,
        )

        # Create chunks (for websites, we don't have screenshot_mapping)
        chunks = await chunker.chunk_extracted_text(
            text=full_text,
            screenshot_mapping={},  # Empty dict for websites
            book_id=str(book_id),
        )

        return chunks

    def _ensure_paragraph_breaks(self, text: str) -> str:
        """Ensure text has proper paragraph breaks for chunking.

        Splits very long blocks of text at sentence boundaries to help
        the chunker create appropriately sized chunks.
        """
        import re

        # Split into existing paragraphs
        paragraphs = text.split("\n\n")
        processed_paragraphs = []

        for para in paragraphs:
            # If paragraph is longer than 3000 characters, split at sentence boundaries
            if len(para) > 3000:
                # Split into sentences (simple heuristic: ". ", "! ", "? " followed by capital letter or end)
                sentences = re.split(r'([.!?]\s+)', para)

                # Reconstruct with proper breaks every ~1500 characters
                current_block = []
                current_length = 0

                for i in range(0, len(sentences), 2):
                    sentence = sentences[i] if i < len(sentences) else ""
                    separator = sentences[i+1] if i+1 < len(sentences) else ""
                    full_sentence = sentence + separator

                    if current_length + len(full_sentence) > 1500 and current_block:
                        # Save current block and start new one
                        processed_paragraphs.append("".join(current_block).strip())
                        current_block = [full_sentence]
                        current_length = len(full_sentence)
                    else:
                        current_block.append(full_sentence)
                        current_length += len(full_sentence)

                # Add remaining block
                if current_block:
                    processed_paragraphs.append("".join(current_block).strip())
            else:
                # Paragraph is fine as-is
                processed_paragraphs.append(para)

        return "\n\n".join(processed_paragraphs)

    async def _generate_embeddings(self, chunks: List[ChunkMetadata], book_id: UUID) -> None:
        """Generate embeddings using existing embedding generator."""
        # Get active embedding config
        result = await self.session.execute(
            select(EmbeddingConfig).where(EmbeddingConfig.is_active == True).limit(1)
        )
        embedding_config = result.scalar_one_or_none()

        if not embedding_config:
            raise Exception("No active embedding configuration found")

        # Create embedding generator
        generator = EmbeddingGenerator(self.session)

        # Extract texts from chunks
        texts = [chunk.chunk_text for chunk in chunks]

        # Generate embeddings for all chunks
        embeddings = await generator.generate_embeddings(texts, book_id=str(book_id))

        # Create Chunk models with embeddings
        chunk_models = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_model = Chunk(
                id=uuid4(),
                book_id=book_id,
                screenshot_ids=[],  # Empty for websites
                chunk_sequence=chunk.chunk_sequence,
                chunk_text=chunk.chunk_text,
                chunk_token_count=chunk.token_count,
                embedding_config_id=embedding_config.id,
                embedding=embedding,  # Add the embedding vector
                vision_model="N/A",  # Not applicable for websites
                vision_prompt_tokens=0,
                vision_completion_tokens=0,
                extraction_timestamp=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            chunk_models.append(chunk_model)

        # Save chunks to database
        self.session.add_all(chunk_models)
        await self.session.commit()

    async def _update_book_metadata(self, book_id: UUID, first_page: ExtractedContent) -> None:
        """Update book with metadata from first page."""
        stmt = (
            update(Book)
            .where(Book.id == book_id)
            .values(
                title=first_page.title,
                author=first_page.author or first_page.domain,
                published_date=first_page.published_date,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def _update_book_status(
        self, book_id: UUID, status: str, error: Optional[str] = None
    ) -> None:
        """Update book ingestion status."""
        values = {
            "ingestion_status": status,
            "updated_at": datetime.utcnow(),
        }
        if error:
            values["ingestion_error"] = error

        stmt = update(Book).where(Book.id == book_id).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def _update_book_final_status(
        self, book_id: UUID, page_count: int, word_count: int
    ) -> None:
        """Update book with final statistics."""
        stmt = (
            update(Book)
            .where(Book.id == book_id)
            .values(
                ingestion_status="completed",
                page_count=page_count,
                word_count=word_count,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def _save_failed_scrape(self, book_id: UUID, url: str, error: str) -> None:
        """Save failed scrape for retry functionality."""
        failed_scrape = FailedScrape(
            id=uuid4(),
            book_id=book_id,
            url=url,
            error_message=error,
            retry_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.session.add(failed_scrape)
        await self.session.commit()
