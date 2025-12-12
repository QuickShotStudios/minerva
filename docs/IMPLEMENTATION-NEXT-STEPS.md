# Website Scraping - Implementation Next Steps

**Status:** ✅ Ready to Start
**Estimated Time to v1.0:** 5-7 days
**Last Updated:** 2025-11-13

---

## 🎯 Quick Start: What to Do Right Now

### Step 1: Review Complete Design (15 minutes)
Read these documents in order:
1. ✅ `docs/brainstorming-session-results.md` - All decisions and rationale
2. ✅ `docs/architecture/website-scraping-architecture.md` - Complete technical design
3. ✅ `docs/architecture/website-scraping-roadmap.md` - Implementation phases

### Step 2: Set Up Development Environment (30 minutes)
```bash
# 1. Install new dependencies
poetry add playwright trafilatura readability-lxml beautifulsoup4 lxml rich datasketch extruct

# 2. Install Playwright browsers
poetry run playwright install chromium

# 3. Verify installations
poetry run python -c "import trafilatura; import playwright; print('✅ Dependencies installed')"
```

### Step 3: Start with Database Migration (2-4 hours)
**This is your first task - everything else depends on it!**

See detailed instructions in [Day 1: Database Migration](#day-1-database-migration) below.

---

## 📅 Day-by-Day Implementation Plan

### Day 1: Database & Discovery (8 hours)

#### Morning: Database Migration (4 hours)

**File:** Create new Alembic migration

```bash
# Create migration
poetry run alembic revision -m "Add website scraping support"
```

**Edit the migration file** (`alembic/versions/XXXXX_add_website_scraping_support.py`):

```python
"""Add website scraping support

Revision ID: XXXXX
Revises: YYYYY
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'XXXXX'
down_revision = 'YYYYY'  # Previous migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Add source_type enum
    source_type_enum = postgresql.ENUM('kindle', 'website', 'pdf', name='source_type')
    source_type_enum.create(op.get_bind())

    # Add source_type column with default 'kindle' (for existing rows)
    op.add_column('books', sa.Column('source_type', source_type_enum, nullable=False, server_default='kindle'))

    # Add metadata columns
    op.add_column('books', sa.Column('source_domain', sa.String(255), nullable=True))
    op.add_column('books', sa.Column('published_date', sa.TIMESTAMP(), nullable=True))
    op.add_column('books', sa.Column('word_count', sa.Integer(), nullable=True))
    # Note: page_count already exists, just repurpose (# of Kindle pages OR # of web pages)

    # Add indexes
    op.create_index('idx_books_source_type', 'books', ['source_type'])
    op.create_index('idx_books_source_domain', 'books', ['source_domain'])

    # Create failed_scrapes table
    op.create_table(
        'failed_scrapes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE')
    )
    op.create_index('idx_failed_scrapes_book_id', 'failed_scrapes', ['book_id'])


def downgrade():
    # Drop failed_scrapes table
    op.drop_index('idx_failed_scrapes_book_id', table_name='failed_scrapes')
    op.drop_table('failed_scrapes')

    # Drop indexes
    op.drop_index('idx_books_source_domain', table_name='books')
    op.drop_index('idx_books_source_type', table_name='books')

    # Drop columns
    op.drop_column('books', 'word_count')
    op.drop_column('books', 'published_date')
    op.drop_column('books', 'source_domain')
    op.drop_column('books', 'source_type')

    # Drop enum
    source_type_enum = postgresql.ENUM('kindle', 'website', 'pdf', name='source_type')
    source_type_enum.drop(op.get_bind())
```

**Run migration:**
```bash
# Test on local database
poetry run alembic upgrade head

# Verify
poetry run python -c "from minerva.db import engine; import sqlalchemy as sa; inspector = sa.inspect(engine); print('✅ Columns:', inspector.get_columns('books'))"
```

**Checkpoint:** ✅ Migration runs successfully, new columns visible in database

---

#### Afternoon: Discovery Module (4 hours)

**File:** Create `minerva/core/ingestion/website_discovery.py`

**Starter Code:**
```python
"""Website discovery module - sitemap parsing and link crawling."""
from dataclasses import dataclass, field
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
from playwright.async_api import async_playwright, Page
import logging

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryConfig:
    """Configuration for website discovery."""
    domain_locked: bool = True
    include_subdomains: bool = False
    max_depth: Optional[int] = None
    max_pages: Optional[int] = None
    exclude_patterns: List[str] = field(default_factory=list)


class WebsiteDiscovery:
    """Discover pages on a website via sitemap or crawling."""

    def __init__(self, config: DiscoveryConfig):
        self.config = config
        self.visited: Set[str] = set()

    async def discover_pages(self, start_url: str) -> List[str]:
        """
        Main discovery method: try sitemap first, fall back to crawler.

        Returns:
            List of URLs to scrape
        """
        logger.info(f"Discovering pages from {start_url}")

        # Try sitemap first
        sitemap_urls = await self._try_sitemap(start_url)
        if sitemap_urls:
            logger.info(f"Found {len(sitemap_urls)} URLs in sitemap")
            return self._filter_by_scope(sitemap_urls, start_url)

        # Fall back to crawler
        logger.info("No sitemap found, falling back to crawler")
        crawled_urls = await self._crawl_site(start_url)
        return self._filter_by_scope(crawled_urls, start_url)

    async def _try_sitemap(self, base_url: str) -> Optional[List[str]]:
        """Try to fetch and parse sitemap.xml."""
        # TODO: Implement sitemap fetching
        # Check /sitemap.xml, /sitemap_index.xml
        # Parse XML, extract <loc> tags
        # Handle sitemap indexes (nested)
        pass

    async def _crawl_site(self, start_url: str) -> List[str]:
        """Crawl site by following links (BFS)."""
        # TODO: Implement BFS crawler
        # Use Playwright to load pages
        # Extract all <a href> links
        # Filter internal links
        # Respect max_depth and max_pages
        pass

    def _filter_by_scope(self, urls: List[str], base_url: str) -> List[str]:
        """Filter URLs based on scope configuration."""
        # TODO: Implement filtering
        # Domain-locked by default
        # Respect include_subdomains
        # Apply exclude_patterns
        # Limit to max_pages
        pass
```

**Implementation Tasks:**
- [ ] Implement `_try_sitemap()` - fetch and parse sitemap.xml
- [ ] Implement `_crawl_site()` - BFS link crawler using Playwright
- [ ] Implement `_filter_by_scope()` - apply scope rules
- [ ] Write unit tests with mock sitemaps and pages
- [ ] Test on real websites: peptidedosages.com, a documentation site

**Checkpoint:** ✅ Discovery finds 50+ pages on peptidedosages.com

---

### Day 2: Content Extraction (8 hours)

**File:** Create `minerva/core/ingestion/content_extractor.py`

**Starter Code:**
```python
"""Content extraction module - extract text and metadata from HTML."""
from dataclasses import dataclass
from typing import Optional
import trafilatura
from readability import Document
from bs4 import BeautifulSoup
import extruct
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Extracted content from a webpage."""
    url: str
    text: str
    title: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    word_count: int = 0


@dataclass
class ExtractionConfig:
    """Configuration for content extraction."""
    use_ai_extraction: bool = False
    min_word_count: int = 50
    min_text_to_html_ratio: float = 0.1


class ContentExtractor:
    """Extract clean text and metadata from HTML pages."""

    def __init__(self, config: ExtractionConfig):
        self.config = config

    def extract_content(self, url: str, html: str) -> Optional[ExtractedContent]:
        """
        Extract content using priority cascade: Trafilatura → Readability → AI.

        Returns:
            ExtractedContent or None if extraction failed
        """
        logger.info(f"Extracting content from {url}")

        # Try Trafilatura first
        text = trafilatura.extract(html, include_comments=False, include_tables=False)
        if text and self._quality_check(text, html):
            logger.debug("Trafilatura extraction successful")
            metadata = self._extract_metadata(html, url)
            return ExtractedContent(url=url, text=text, **metadata)

        # Fall back to Readability
        doc = Document(html)
        text = doc.summary(html_partial=True)
        # TODO: Strip HTML tags from Readability output
        if text and self._quality_check(text, html):
            logger.debug("Readability extraction successful")
            metadata = self._extract_metadata(html, url)
            return ExtractedContent(url=url, text=text, **metadata)

        # TODO: AI extraction (if enabled)
        if self.config.use_ai_extraction:
            pass

        logger.warning(f"Failed to extract quality content from {url}")
        return None

    def _extract_metadata(self, html: str, url: str) -> dict:
        """Extract metadata using priority cascade: meta tags → Schema.org → inference."""
        # TODO: Implement metadata extraction
        # OpenGraph tags (og:title, og:description, og:author)
        # Standard meta tags
        # Schema.org JSON-LD (use extruct library)
        # Content inference (dates in text, heuristics)
        pass

    def _quality_check(self, text: str, html: str) -> bool:
        """Check if extracted content meets quality thresholds."""
        word_count = len(text.split())
        if word_count < self.config.min_word_count:
            return False

        # TODO: Check text-to-HTML ratio
        return True
```

**Implementation Tasks:**
- [ ] Complete `extract_content()` with all three methods
- [ ] Implement `_extract_metadata()` with OpenGraph, meta tags, Schema.org
- [ ] Implement `_quality_check()` with word count and ratio checks
- [ ] Write unit tests with diverse HTML fixtures
- [ ] Test on peptidedosages.com, blog sites, documentation sites

**Checkpoint:** ✅ Extracts clean text and metadata from 90%+ of test pages

---

### Day 3: Deduplication & Orchestration (8 hours)

#### Morning: Deduplication (4 hours)

**File:** Create `minerva/core/ingestion/content_processor.py`

**Starter Code:**
```python
"""Content processing - deduplication and chunking."""
import hashlib
from typing import List
from datasketch import MinHash, MinHashLSH
from minerva.core.ingestion.content_extractor import ExtractedContent
import logging

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Process extracted content: deduplicate, chunk, prepare for embeddings."""

    def deduplicate_pages(self, pages: List[ExtractedContent]) -> List[ExtractedContent]:
        """Remove exact duplicate pages using SHA256 hash."""
        seen_hashes = set()
        unique_pages = []

        for page in pages:
            content_hash = hashlib.sha256(page.text.encode()).hexdigest()
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_pages.append(page)
            else:
                logger.debug(f"Skipping duplicate page: {page.url}")

        logger.info(f"Deduplication: {len(pages)} → {len(unique_pages)} pages")
        return unique_pages

    def deduplicate_chunks(self, chunks: List[dict]) -> List[dict]:
        """Remove near-duplicate chunks using MinHash LSH."""
        # TODO: Implement MinHash deduplication
        # Create MinHash for each chunk
        # Use LSH to find similar chunks
        # Keep only unique chunks (95% similarity threshold)
        pass
```

**Implementation Tasks:**
- [ ] Complete `deduplicate_chunks()` with MinHash LSH
- [ ] Write unit tests with synthetic duplicate/near-duplicate data
- [ ] Performance test with 1000+ chunks

**Checkpoint:** ✅ Deduplication removes duplicates in <5s for 1000 chunks

---

#### Afternoon: Orchestrator (4 hours)

**File:** Create `minerva/core/ingestion/web_scraper_orchestrator.py`

**Starter Code:**
```python
"""Web scraper orchestrator - coordinates all components."""
import asyncio
from dataclasses import dataclass
from typing import List
from playwright.async_api import async_playwright
from minerva.core.ingestion.website_discovery import WebsiteDiscovery, DiscoveryConfig
from minerva.core.ingestion.content_extractor import ContentExtractor, ExtractionConfig
from minerva.core.ingestion.content_processor import ContentProcessor
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScrapeConfig:
    """Complete scraping configuration."""
    discovery: DiscoveryConfig
    extraction: ExtractionConfig
    retry_max_attempts: int = 3
    retry_base_delay_ms: int = 1000


@dataclass
class ScrapeResult:
    """Result of a scraping operation."""
    book_id: int
    success_count: int = 0
    failure_count: int = 0
    failures: List[dict] = None

    def __post_init__(self):
        if self.failures is None:
            self.failures = []


class WebScraperOrchestrator:
    """Coordinate website scraping pipeline."""

    async def scrape_website(self, url: str, config: ScrapeConfig) -> ScrapeResult:
        """
        Main scraping pipeline.

        Steps:
        1. Create book record in database
        2. Discover pages (sitemap or crawl)
        3. For each page: fetch HTML, extract content, save
        4. Deduplicate and process
        5. Generate summary report
        """
        # TODO: Implement full pipeline
        # Initialize Playwright
        # Call discovery.discover_pages()
        # Loop through pages:
        #   - fetch_page_with_retry()
        #   - extractor.extract_content()
        #   - save_to_database()
        #   - adaptive_delay()
        # Call processor.deduplicate()
        # Generate embeddings (reuse existing pipeline)
        pass

    async def fetch_page_with_retry(self, url: str, config: ScrapeConfig) -> str:
        """Fetch page HTML with retry logic and exponential backoff."""
        # TODO: Implement retry with backoff
        pass

    async def adaptive_delay(self, error_rate: float):
        """Adjust delay based on recent error rate."""
        if error_rate > 0.2:
            delay_ms = 2000
        elif error_rate > 0.1:
            delay_ms = 1000
        else:
            delay_ms = 200

        await asyncio.sleep(delay_ms / 1000)
```

**Implementation Tasks:**
- [ ] Implement `scrape_website()` main pipeline
- [ ] Implement `fetch_page_with_retry()` with exponential backoff
- [ ] Implement dynamic content handling (pagination, infinite scroll)
- [ ] Implement incremental saves to database
- [ ] Write integration tests with local test server

**Checkpoint:** ✅ End-to-end scrape of 10-page test site works

---

### Day 4: CLI & Dynamic Content (8 hours)

#### Morning: CLI Interface (4 hours)

**File:** Modify `minerva/cli/app.py`

**Code Changes:**
```python
# Add new command
@app.command()
def ingest(
    url: str,
    source_type: Optional[str] = typer.Argument(None, help="Source type: website, kindle"),
    max_pages: Optional[int] = typer.Option(None, help="Maximum pages to scrape"),
    max_depth: Optional[int] = typer.Option(None, help="Maximum link depth"),
    include_subdomains: bool = typer.Option(False, help="Include subdomains"),
    use_ai_extraction: bool = typer.Option(False, help="Use AI for content extraction"),
    verbose: bool = typer.Option(False, help="Verbose logging"),
):
    """Ingest content from URL (auto-detects Kindle vs. website)."""

    # Auto-detect source type if not provided
    if source_type is None:
        if 'read.amazon.com' in url:
            source_type = 'kindle'
        else:
            source_type = 'website'

    # Route to appropriate handler
    if source_type == 'kindle':
        # Existing Kindle ingestion logic
        pass
    elif source_type == 'website':
        # New website scraping logic
        asyncio.run(_ingest_website(url, max_pages, max_depth, include_subdomains, use_ai_extraction, verbose))
    else:
        typer.echo(f"❌ Unknown source type: {source_type}", err=True)
        raise typer.Exit(1)


async def _ingest_website(url, max_pages, max_depth, include_subdomains, use_ai_extraction, verbose):
    """Handle website ingestion."""
    # TODO: Configure logging based on verbose flag
    # TODO: Build config from CLI options
    # TODO: Call WebScraperOrchestrator.scrape_website()
    # TODO: Display summary report
    pass


@app.command()
def retry(book_id: int):
    """Retry failed pages from a previous scrape."""
    # TODO: Fetch failed_scrapes for book_id
    # TODO: Re-attempt scraping
    # TODO: Update database
    pass
```

**Implementation Tasks:**
- [ ] Add `ingest` command with auto-detection
- [ ] Add all CLI options (max-pages, max-depth, etc.)
- [ ] Add `retry` command
- [ ] Write CLI tests (option parsing, auto-detection)

**Checkpoint:** ✅ `minerva ingest website <url>` command works end-to-end

---

#### Afternoon: Dynamic Content Handling (4 hours)

**File:** Enhance `web_scraper_orchestrator.py`

**Code Addition:**
```python
async def handle_dynamic_content(page) -> None:
    """
    Smart detection: network idle → pagination → infinite scroll.

    Already waited for networkidle in goto().
    Now check for pagination buttons and infinite scroll.
    """
    # Check for pagination buttons
    pagination_selectors = [
        'a[rel="next"]',
        '.next-page',
        '.load-more',
        'button:has-text("Load More")',
        '[aria-label="Next"]'
    ]

    for selector in pagination_selectors:
        button = await page.query_selector(selector)
        if button:
            logger.debug(f"Found pagination button: {selector}")
            await button.click()
            await page.wait_for_load_state('networkidle')
            # Recursively check for more pagination
            return await handle_dynamic_content(page)

    # Check for infinite scroll
    prev_height = await page.evaluate('document.body.scrollHeight')
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await page.wait_for_timeout(1000)  # Wait for content to load
    new_height = await page.evaluate('document.body.scrollHeight')

    if new_height > prev_height:
        logger.debug("Detected infinite scroll, continuing...")
        return await handle_dynamic_content(page)

    logger.debug("No more dynamic content detected")
```

**Implementation Tasks:**
- [ ] Integrate `handle_dynamic_content()` into page fetching
- [ ] Test on sites with pagination
- [ ] Test on sites with infinite scroll
- [ ] Test on static sites (should not break)

**Checkpoint:** ✅ Handles pagination and infinite scroll on test sites

---

### Day 5: Progress Dashboard & Polish (8 hours)

#### Morning: Progress Dashboard (5 hours)

**File:** Create `minerva/core/ingestion/progress_tracker.py`

**Starter Code:**
```python
"""Progress tracking with rich dashboard."""
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table
from rich.live import Live
from dataclasses import dataclass
import time

console = Console()


@dataclass
class ScrapingStats:
    """Real-time scraping statistics."""
    total_pages: int = 0
    scraped_pages: int = 0
    failed_pages: int = 0
    words_extracted: int = 0
    chunks_created: int = 0
    start_time: float = 0

    def __post_init__(self):
        self.start_time = time.time()

    @property
    def success_rate(self) -> float:
        if self.scraped_pages == 0:
            return 0.0
        return (self.scraped_pages / (self.scraped_pages + self.failed_pages)) * 100

    @property
    def pages_per_min(self) -> float:
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return (self.scraped_pages / elapsed) * 60


class ProgressTracker:
    """Track and display scraping progress with rich UI."""

    def __init__(self, total_pages: int):
        self.stats = ScrapingStats(total_pages=total_pages)
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        )
        self.task_id = self.progress.add_task("Scraping pages...", total=total_pages)

    def update(self, success: bool = True, words: int = 0, current_url: str = ""):
        """Update progress after scraping a page."""
        if success:
            self.stats.scraped_pages += 1
            self.stats.words_extracted += words
        else:
            self.stats.failed_pages += 1

        self.progress.update(
            self.task_id,
            advance=1,
            description=f"Scraping: {current_url[:50]}..."
        )

    def display_summary(self, failures: List[dict]):
        """Display final summary report."""
        # TODO: Create beautiful summary table with rich
        # Show: total pages, success rate, duration, cost estimate, failures
        pass
```

**Implementation Tasks:**
- [ ] Integrate `ProgressTracker` into orchestrator
- [ ] Implement live dashboard with stats table
- [ ] Implement beautiful summary report
- [ ] Test on scrapes of various sizes (10, 50, 100+ pages)

**Checkpoint:** ✅ Beautiful live dashboard shows real-time progress

---

#### Afternoon: Polish & Refinement (3 hours)

**Tasks:**
- [ ] Add error logging to files (`~/.minerva/logs/scrape-{book_id}.log`)
- [ ] Improve error messages (user-friendly)
- [ ] Add cost estimation to summary (embeddings cost)
- [ ] Code cleanup and refactoring
- [ ] Add docstrings to all public methods
- [ ] Run linter (black, flake8)

**Checkpoint:** ✅ Code is clean, well-documented, lint-free

---

### Day 6: Testing & Documentation (8 hours)

#### Morning: Comprehensive Testing (5 hours)

**Test Sites:**
- [ ] peptidedosages.com (WordPress, dynamic content)
- [ ] Python docs or similar (static HTML, sitemap)
- [ ] Medium article (paywall detection, metadata)
- [ ] Local test server with pagination
- [ ] Local test server with infinite scroll

**Test Scenarios:**
- [ ] Basic scrape (10-20 pages)
- [ ] Large scrape (100+ pages with --max-pages limit)
- [ ] Deep crawl (--max-depth 5)
- [ ] Subdomain scrape (--include-subdomains)
- [ ] Simulated network failures (test retry logic)
- [ ] Empty pages, 404s, timeouts (test error handling)

**Performance Testing:**
- [ ] Measure scraping time for 50 pages
- [ ] Monitor memory usage during large scrape
- [ ] Check database query performance

**Checkpoint:** ✅ All tests pass, no critical bugs

---

#### Afternoon: Documentation (3 hours)

**Files to Update:**
- [ ] `README.md` - Add website scraping section with examples
- [ ] `docs/user-guide/website-scraping.md` - Create comprehensive guide
- [ ] `~/.minerva/config.yaml` - Add scraping configuration section
- [ ] Code docstrings - Ensure all public APIs documented

**Documentation Structure:**
```markdown
# Website Scraping User Guide

## Getting Started
- Installation
- First scrape example

## Features
- Auto-detection
- Sitemap vs. crawler
- Dynamic content handling
- Error recovery

## CLI Reference
- All commands and options
- Examples for each option

## Troubleshooting
- Common errors and solutions
- Performance tuning
- Anti-bot measures

## Advanced Usage
- AI extraction
- Custom configurations
- Batch scraping
```

**Checkpoint:** ✅ Documentation is comprehensive and clear

---

### Day 7: Production Deployment (4 hours)

#### Database Migration on Production

```bash
# 1. Backup production database first!
pg_dump $PRODUCTION_DATABASE_URL > backup-pre-scraping-$(date +%Y%m%d).sql

# 2. Run migration on production
alembic upgrade head

# 3. Verify migration
psql $PRODUCTION_DATABASE_URL -c "SELECT source_type, COUNT(*) FROM books GROUP BY source_type;"
# Should show: kindle | 9
```

#### Deploy Code to Fly.io

```bash
# 1. Ensure all tests pass locally
poetry run pytest

# 2. Deploy to Fly.io
flyctl deploy

# 3. Monitor deployment
flyctl logs -a minerva-api

# 4. Smoke test
minerva ingest website https://example.com --max-pages 5
```

#### Post-Deployment Verification

```bash
# Check database
psql $PRODUCTION_DATABASE_URL -c "SELECT * FROM books WHERE source_type='website' LIMIT 5;"

# Check API
curl https://minerva-api.fly.dev/api/v1/books \
  -H "X-API-Key: YOUR_KEY"

# Search scraped content
minerva search "example query"
```

**Checkpoint:** ✅ v1.0 deployed to production, smoke tests pass

---

## 📦 Complete Deliverables Checklist

Before considering v1.0 complete, verify all deliverables:

### Code
- [ ] `minerva/core/ingestion/website_discovery.py`
- [ ] `minerva/core/ingestion/content_extractor.py`
- [ ] `minerva/core/ingestion/content_processor.py`
- [ ] `minerva/core/ingestion/web_scraper_orchestrator.py`
- [ ] `minerva/core/ingestion/progress_tracker.py`
- [ ] Updated `minerva/cli/app.py`
- [ ] Alembic migration for database schema

### Tests
- [ ] Unit tests for discovery module (>80% coverage)
- [ ] Unit tests for extraction module (>85% coverage)
- [ ] Unit tests for processing module (>80% coverage)
- [ ] Integration tests (end-to-end scraping)
- [ ] CLI tests (option parsing, commands)

### Documentation
- [ ] Updated `README.md`
- [ ] `docs/user-guide/website-scraping.md`
- [ ] `docs/architecture/website-scraping-architecture.md` ✅
- [ ] `docs/architecture/website-scraping-roadmap.md` ✅
- [ ] `docs/brainstorming-session-results.md` ✅
- [ ] Updated `~/.minerva/config.yaml`
- [ ] Code docstrings for all public APIs

### Deployment
- [ ] Database migration run on production
- [ ] Code deployed to Fly.io
- [ ] Smoke tests passed
- [ ] Monitoring configured

### Quality
- [ ] All tests pass locally and in CI
- [ ] Code passes linter (black, flake8)
- [ ] >80% test coverage overall
- [ ] No critical bugs
- [ ] Performance benchmarks met (<2 min for 50 pages)

---

## 🚨 Blockers & How to Unblock

### Blocker: "Playwright is too slow"
**Solution:** This is expected. Optimize in v1.1 with parallel fetching. For now, prioritize correctness over speed.

### Blocker: "Content extraction quality is poor on some sites"
**Solution:**
1. Test with different sites - quality varies by site structure
2. Try adjusting Trafilatura config
3. Fall back to `--use-ai-extraction` for problematic sites (implement in v1.1)
4. Document known problematic sites

### Blocker: "Getting blocked by anti-bot measures"
**Solution:**
1. Ensure adaptive rate limiting is working
2. Add respectful user agent
3. Test with slower `--delay` setting
4. Document sites with strict anti-bot measures

### Blocker: "Database performance issues with large scrapes"
**Solution:**
1. Verify indexes are created (`idx_books_source_type`, etc.)
2. Use batch inserts for chunks (not one-by-one)
3. Monitor query performance with `EXPLAIN ANALYZE`
4. Consider connection pooling if needed

### Blocker: "Confused about how to integrate with existing Kindle pipeline"
**Solution:**
- Website scraping reuses: `SemanticChunker`, `EmbeddingGenerator`, database schema
- Only difference: source of content (Playwright web scraper vs. Kindle screenshots)
- After extraction, everything is identical (chunks → embeddings → storage)

---

## 💡 Tips for Success

1. **Start Simple:** Get a basic end-to-end scrape working first (even if ugly), then refine
2. **Test Early, Test Often:** Run on real websites every day, catch issues early
3. **Incremental Commits:** Commit after each module (discovery, extraction, etc.)
4. **Use Type Hints:** Dataclasses and type hints prevent bugs and improve readability
5. **Log Everything:** Debug logging is your friend for long-running scrapes
6. **Ask for Help:** If stuck >2 hours, ask questions (GitHub, Discord, etc.)

---

## 📞 Support

**Questions?** Open a GitHub Discussion
**Bugs?** Open a GitHub Issue
**Need Help?** Tag @analyst in Discord

---

## 🎉 When You're Done

Celebrate! You've shipped a major feature. Then:

1. **Gather Feedback:** Ask early users to test and report issues
2. **Monitor Production:** Watch logs for errors, performance issues
3. **Plan v1.1:** Prioritize improvements based on real usage
4. **Update Roadmap:** Mark v1.0 complete, start v1.1 planning

**Next Phase:** v1.1 Enhancement (AI extraction, robots.txt, performance optimization)

---

*Good luck! You have a complete blueprint - now go build it! 🚀*
