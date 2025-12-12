# Website Scraping Architecture - Minerva

**Version:** 1.0
**Status:** Design Complete - Ready for Implementation
**Date:** 2025-11-13
**Author:** Brainstorming Session with Business Analyst Mary

---

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [Database Schema](#database-schema)
6. [CLI Interface](#cli-interface)
7. [Configuration](#configuration)
8. [Error Handling](#error-handling)
9. [Performance Considerations](#performance-considerations)
10. [Security & Ethics](#security--ethics)
11. [Testing Strategy](#testing-strategy)
12. [Deployment](#deployment)

---

## Overview

### Purpose
Add website scraping capability to Minerva to ingest knowledge from public websites (blogs, documentation, research sites) into the semantic search knowledge base.

### Goals
- **Consistency:** Reuse existing Minerva patterns (Playwright, semantic chunking, embeddings)
- **Reliability:** Production-ready error handling, retries, incremental saves
- **User-Friendly:** Smart defaults, auto-detection, beautiful progress feedback
- **Future-Proof:** Extensible architecture for PDF, PubMed, auto-citations (v2+)
- **AI-Optimized:** Clean text extraction for quality embeddings and RAG

### Non-Goals (Out of Scope for v1)
- ❌ Authenticated/paywalled content scraping
- ❌ Scheduled/automated re-scraping
- ❌ Multi-modal content (images, videos)
- ❌ Real-time change detection
- ❌ API endpoint for programmatic scraping

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│  minerva ingest website <url> [--max-pages] [--max-depth]   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  WebScraperOrchestrator                      │
│  • Input validation & auto-detection                         │
│  • Progress tracking (rich dashboard)                        │
│  • Error handling & retry coordination                       │
│  • Summary report generation                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Discovery  │  │  Extraction │  │  Processing │
│   Module    │  │   Module    │  │   Module    │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         │               │               │
┌────────▼───────────────▼───────────────▼────────────────────┐
│              Existing Minerva Pipeline                       │
│  • Semantic Chunking (500-800 tokens)                        │
│  • Embedding Generation (OpenAI text-embedding-3-small)      │
│  • PostgreSQL Storage (pgvector)                             │
└──────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **Modular Design:** Discovery, extraction, and processing are independent, swappable components
2. **Reuse Over Rebuild:** Leverage existing Kindle pipeline infrastructure
3. **Fail Gracefully:** Errors in one page don't block entire scrape
4. **Progressive Enhancement:** Core features in v1, advanced features in v2+
5. **Configuration Over Code:** CLI flags control behavior without code changes

---

## Component Design

### 1. WebsiteDiscovery Component

**Responsibility:** Find all pages to scrape on a given website

**Algorithm:**
```python
def discover_pages(url: str, config: DiscoveryConfig) -> List[str]:
    """
    Hybrid discovery: sitemap.xml → crawler fallback
    """
    pages = []

    # Step 1: Try sitemap.xml
    sitemap_urls = check_sitemap(url)
    if sitemap_urls:
        pages.extend(sitemap_urls)
        return filter_by_scope(pages, config)

    # Step 2: Fall back to crawler
    pages = crawl_site(url, config)
    return filter_by_scope(pages, config)
```

**Implementation Details:**

**Sitemap Detection:**
- Check standard locations: `/sitemap.xml`, `/sitemap_index.xml`, `/sitemap.xml.gz`
- Parse XML using `xml.etree.ElementTree`
- Handle sitemap indexes (nested sitemaps)
- Extract URLs with priority/lastmod metadata

**Crawler Strategy:**
- Start at provided URL (root)
- Use Playwright to load page and extract all `<a href>` links
- Filter to internal links only (same domain/subdomain based on config)
- Breadth-first traversal to respect `--max-depth`
- Track visited URLs (set) to avoid cycles
- Stop when `--max-pages` limit reached

**Scope Filtering:**
```python
@dataclass
class DiscoveryConfig:
    domain_locked: bool = True
    include_subdomains: bool = False
    max_depth: Optional[int] = None
    max_pages: Optional[int] = None
    exclude_patterns: List[str] = field(default_factory=list)  # ["/admin/*", "/cart/*"]
```

**Output:** List of URLs to scrape, ordered by priority (sitemap priority or BFS order)

---

### 2. ContentExtractor Component

**Responsibility:** Extract clean text and metadata from HTML pages

**Algorithm:**
```python
def extract_content(url: str, html: str, config: ExtractionConfig) -> ExtractedContent:
    """
    Priority cascade: Trafilatura → Readability → Fallback
    Optional AI cleanup for complex pages
    """
    # Step 1: Try Trafilatura (fast, accurate)
    content = trafilatura.extract(html, include_comments=False)
    if content and quality_check(content):
        return enhance_with_metadata(content, html, url)

    # Step 2: Fall back to Readability
    content = readability.extract(html)
    if content and quality_check(content):
        return enhance_with_metadata(content, html, url)

    # Step 3: AI extraction (if enabled)
    if config.use_ai_extraction:
        content = ai_extract_content(html, url)
        return enhance_with_metadata(content, html, url)

    # Step 4: Fallback (strip HTML, basic cleaning)
    content = strip_html_basic(html)
    return enhance_with_metadata(content, html, url)
```

**Metadata Extraction:**
```python
def extract_metadata(html: str, url: str) -> Metadata:
    """
    Priority: Meta tags → Schema.org → Inference
    """
    soup = BeautifulSoup(html, 'lxml')
    metadata = {}

    # OpenGraph tags
    metadata['title'] = soup.find('meta', property='og:title')['content']
    metadata['description'] = soup.find('meta', property='og:description')['content']

    # Schema.org JSON-LD
    schema_data = extract_json_ld(soup)
    if schema_data:
        metadata.update(parse_schema_org(schema_data))

    # Standard meta tags
    metadata['author'] = soup.find('meta', attrs={'name': 'author'})['content']
    metadata['published_date'] = soup.find('meta', attrs={'name': 'published_date'})['content']

    # Inference from content
    if not metadata.get('published_date'):
        metadata['published_date'] = infer_date_from_content(soup)

    return Metadata(**metadata)
```

**Quality Check:**
- Minimum word count (e.g., 50 words)
- Text-to-HTML ratio (avoid pages with mostly navigation)
- Language detection (optional: filter non-English)

**AI Extraction (Optional):**
```python
async def ai_extract_content(html: str, url: str) -> str:
    """
    Use GPT-4o-mini to extract main content from complex layouts
    """
    prompt = f"""
    Extract the main article content from this HTML page.
    Remove navigation, ads, sidebars, footers.
    Preserve structure with markdown headings.

    URL: {url}
    HTML: {html[:10000]}  # Truncate for token limits
    """
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

---

### 3. ContentProcessor Component

**Responsibility:** Deduplicate, chunk, and prepare content for embedding

**Deduplication Algorithm:**
```python
def deduplicate_pages(pages: List[ExtractedContent]) -> List[ExtractedContent]:
    """
    Page-level exact hash deduplication
    """
    seen_hashes = set()
    unique_pages = []

    for page in pages:
        content_hash = hashlib.sha256(page.text.encode()).hexdigest()
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_pages.append(page)

    return unique_pages

def deduplicate_chunks(chunks: List[Chunk]) -> List[Chunk]:
    """
    Chunk-level fuzzy similarity deduplication using MinHash
    """
    from datasketch import MinHash, MinHashLSH

    lsh = MinHashLSH(threshold=0.95, num_perm=128)
    unique_chunks = []

    for chunk in chunks:
        minhash = MinHash(num_perm=128)
        for word in chunk.text.split():
            minhash.update(word.encode())

        # Check if similar chunk exists
        similar = lsh.query(minhash)
        if not similar:
            lsh.insert(chunk.id, minhash)
            unique_chunks.append(chunk)

    return unique_chunks
```

**Chunking:**
- Reuse existing `SemanticChunker` from Kindle pipeline
- 500-800 tokens per chunk
- 15% overlap between chunks
- Preserve paragraph boundaries

---

### 4. WebScraperOrchestrator Component

**Responsibility:** Coordinate all components, handle errors, track progress

**Main Pipeline:**
```python
async def scrape_website(url: str, config: ScrapeConfig) -> ScrapeResult:
    """
    Main orchestration logic
    """
    # Step 1: Initialize
    session = init_playwright_session()
    progress = init_progress_dashboard()
    results = ScrapeResult()

    # Step 2: Discover pages
    progress.start_phase("Discovering pages...")
    pages_to_scrape = await discovery.discover_pages(url, config.discovery)
    progress.update(total=len(pages_to_scrape))

    # Step 3: Scrape pages with error handling
    for page_url in pages_to_scrape:
        try:
            html = await fetch_page_with_retry(session, page_url, config.retry)
            content = extractor.extract_content(page_url, html, config.extraction)

            # Save immediately (incremental)
            await save_content_to_db(content)

            results.success_count += 1
            progress.advance()

            # Adaptive rate limiting
            await adaptive_delay(results.get_error_rate())

        except Exception as e:
            results.failures.append(FailedPage(url=page_url, error=str(e)))
            await log_failure(page_url, e)
            progress.update_errors(results.failure_count)

    # Step 4: Deduplication & processing
    progress.start_phase("Processing content...")
    await deduplicate_and_chunk(results.book_id)

    # Step 5: Generate summary
    return results
```

**Adaptive Rate Limiting:**
```python
async def adaptive_delay(error_rate: float) -> None:
    """
    Adjust delay based on recent error rate
    """
    if error_rate > 0.2:  # >20% errors
        delay = 2000  # Slow down to 2 seconds
    elif error_rate > 0.1:  # >10% errors
        delay = 1000  # 1 second
    else:
        delay = 200  # Fast: 200ms

    await asyncio.sleep(delay / 1000)
```

**Retry Logic:**
```python
async def fetch_page_with_retry(
    session: PlaywrightSession,
    url: str,
    config: RetryConfig
) -> str:
    """
    Exponential backoff retry
    """
    for attempt in range(config.max_retries):
        try:
            page = await session.goto(url, wait_until='networkidle')

            # Smart dynamic content handling
            await handle_dynamic_content(page)

            return await page.content()

        except Exception as e:
            if attempt == config.max_retries - 1:
                raise  # Final attempt failed

            backoff = config.base_delay * (2 ** attempt)
            await asyncio.sleep(backoff)
```

**Dynamic Content Handling:**
```python
async def handle_dynamic_content(page: PlaywrightPage) -> None:
    """
    Smart detection: network idle → pagination → infinite scroll
    """
    # Already waited for networkidle in goto()

    # Check for pagination
    pagination_selectors = [
        'a[rel="next"]', '.next-page', '.load-more',
        'button:has-text("Load More")', '[aria-label="Next"]'
    ]
    for selector in pagination_selectors:
        button = await page.query_selector(selector)
        if button:
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
        # More content loaded, keep scrolling
        return await handle_dynamic_content(page)
```

---

## Data Flow

### End-to-End Flow

```
User Input
    │
    ├─> minerva ingest website https://example.com --max-pages 100
    │
    ▼
CLI Parser
    │
    ├─> Validate URL
    ├─> Parse flags (--max-pages, --max-depth, --use-ai-extraction)
    ├─> Auto-detect source type (if not explicit)
    │
    ▼
WebScraperOrchestrator.scrape_website()
    │
    ├─> Initialize Playwright session
    ├─> Create "book" record in database (source_type='website')
    │
    ▼
WebsiteDiscovery.discover_pages()
    │
    ├─> Check /sitemap.xml
    │   ├─> Parse URLs
    │   └─> Return list
    │
    ├─> Fallback: Crawl site (BFS)
    │   ├─> Load root page
    │   ├─> Extract all <a> links
    │   ├─> Filter internal links
    │   ├─> Recursively crawl (respect max-depth)
    │   └─> Return list (capped at max-pages)
    │
    ▼
For each URL:
    │
    ├─> Fetch with retry (Playwright)
    │   ├─> goto(url, wait_until='networkidle')
    │   ├─> handle_dynamic_content() (pagination/scroll)
    │   └─> Return HTML
    │
    ├─> ContentExtractor.extract_content()
    │   ├─> Try Trafilatura
    │   ├─> Fallback Readability
    │   ├─> Optional AI extraction
    │   ├─> Extract metadata (meta tags, Schema.org)
    │   └─> Return ExtractedContent
    │
    ├─> Immediate Save to Database
    │   ├─> Create ingestion_log entry
    │   ├─> Store raw content (temporary)
    │   └─> Commit transaction
    │
    ├─> Adaptive delay (based on error rate)
    │
    └─> Update progress dashboard

    ▼
After all pages scraped:
    │
    ├─> ContentProcessor.deduplicate_pages()
    │   └─> Remove exact duplicates (SHA256 hash)
    │
    ├─> SemanticChunker.chunk_content()
    │   ├─> Split into 500-800 token chunks
    │   ├─> 15% overlap
    │   └─> Preserve boundaries
    │
    ├─> ContentProcessor.deduplicate_chunks()
    │   └─> MinHash LSH (95% similarity threshold)
    │
    ├─> EmbeddingGenerator.generate_embeddings()
    │   ├─> Batch chunks (100 at a time)
    │   ├─> Call OpenAI API
    │   └─> Store vectors in pgvector
    │
    ├─> Update book status (completed/failed)
    │
    └─> Display summary report
        ├─> Pages scraped: 95/100
        ├─> Failures: 5 (see logs)
        ├─> Chunks created: 487
        ├─> Duration: 8m 32s
        └─> Cost: $0.03 (embeddings)
```

---

## Database Schema

### Modified Schema (v1)

```sql
-- Add source_type to books table
ALTER TABLE books
ADD COLUMN source_type VARCHAR(20) NOT NULL DEFAULT 'kindle'
    CHECK (source_type IN ('kindle', 'website', 'pdf'));

-- Add index for filtering by source type
CREATE INDEX idx_books_source_type ON books(source_type);

-- Add metadata columns for website sources
ALTER TABLE books
ADD COLUMN source_domain VARCHAR(255),
ADD COLUMN published_date TIMESTAMP,
ADD COLUMN word_count INTEGER,
ADD COLUMN page_count INTEGER;  -- For websites, this is # of pages scraped

-- Update chunks table (no changes needed, already generic)
-- chunks.book_id foreign key still works

-- Add failed_scrapes table for retry functionality
CREATE TABLE failed_scrapes (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_failed_scrapes_book_id ON failed_scrapes(book_id);
```

### Example Data

```sql
-- Website scraping result
INSERT INTO books (
    title,
    source_url,
    source_type,
    source_domain,
    status,
    page_count,
    word_count,
    published_date
) VALUES (
    'Peptide Dosages - Complete Guide',
    'https://peptidedosages.com',
    'website',
    'peptidedosages.com',
    'completed',
    47,  -- 47 pages scraped
    125000,  -- Total words
    '2024-01-15 00:00:00'
);

-- Failed scrape entries
INSERT INTO failed_scrapes (book_id, url, error_message, retry_count)
VALUES
    (123, 'https://example.com/page-404', 'HTTP 404 Not Found', 3),
    (123, 'https://example.com/timeout', 'Request timeout after 30s', 3);
```

---

## CLI Interface

### Command Structure

```bash
# Explicit source type (recommended)
minerva ingest website <url> [OPTIONS]
minerva ingest kindle <url>

# Auto-detect fallback
minerva ingest <url> [OPTIONS]

# Retry failed pages
minerva retry <book_id>
```

### Options

```bash
# Scope control
--max-pages INTEGER          # Maximum pages to scrape (safety limit)
--max-depth INTEGER          # Maximum link depth from starting URL
--include-subdomains         # Allow scraping across subdomains

# Content extraction
--use-ai-extraction          # Use GPT-4o-mini for complex pages (extra cost)

# Rate limiting
--delay INTEGER              # Override adaptive delay (milliseconds)

# Progress & logging
--verbose                    # Detailed logging (default: progress bar only)
--quiet                      # Suppress all output except errors

# Output
--output-log PATH            # Save detailed log to file
```

### Examples

```bash
# Basic scrape (auto-detect, smart defaults)
minerva ingest https://peptidedosages.com

# Explicit website scrape with limits
minerva ingest website https://blog.example.com --max-pages 50 --max-depth 3

# Use AI extraction for complex layouts
minerva ingest website https://complex-site.com --use-ai-extraction

# Include subdomains
minerva ingest website https://example.com --include-subdomains

# Verbose logging to file
minerva ingest website https://example.com --verbose --output-log scrape.log

# Retry failed pages from previous scrape
minerva retry 123
```

### CLI Output (Rich Dashboard)

```
🌐 Scraping Website: peptidedosages.com
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Progress
  Pages scraped: ████████████████░░░░ 42/47 (89%)
  Speed: 3.2 pages/min
  Elapsed: 13m 12s
  Estimated remaining: 1m 45s

✅ Success: 42 pages
❌ Errors: 3 pages (retrying...)
⏩ Queue: 2 pages remaining

📈 Stats
  Total words: 105,432
  Avg words/page: 2,510
  Chunks created: 387
  Duplicates removed: 12

Current: Scraping /articles/peptide-protocols...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Summary Report

```
✅ Scraping Complete!

📊 Summary
  URL: https://peptidedosages.com
  Duration: 15m 47s
  Pages scraped: 45/47 (95.7%)
  Failed: 2 (see logs)

📝 Content
  Total words: 112,849
  Chunks created: 421
  Duplicates removed: 18
  Embeddings generated: 403

💰 Cost
  OpenAI API: $0.032 (embeddings)

❌ Failed Pages
  1. https://peptidedosages.com/admin-login (403 Forbidden)
  2. https://peptidedosages.com/old-page (404 Not Found)

💡 Next Steps
  • View ingested content: minerva list
  • Search: minerva search "peptide dosing"
  • Retry failures: minerva retry 123
  • View full logs: cat ~/.minerva/logs/scrape-123.log
```

---

## Configuration

### Config File (~/.minerva/config.yaml)

```yaml
scraping:
  # Default limits (can be overridden via CLI)
  max_pages: 500
  max_depth: null  # Unlimited depth by default

  # Rate limiting
  adaptive_rate_limiting: true
  min_delay_ms: 200
  max_delay_ms: 5000
  respect_robots_txt: true

  # Content extraction
  extraction_method: "trafilatura"  # trafilatura | readability | ai
  use_ai_extraction: false
  ai_extraction_model: "gpt-4o-mini"

  # Quality filters
  min_word_count: 50
  min_text_to_html_ratio: 0.1

  # Retry settings
  max_retries: 3
  base_retry_delay_ms: 1000
  retry_backoff_multiplier: 2

  # Deduplication
  page_deduplication: true  # Exact hash
  chunk_deduplication: true  # Fuzzy similarity
  chunk_similarity_threshold: 0.95

  # User agent
  user_agent: "Mozilla/5.0 (compatible; Minerva/1.0; +https://github.com/yourusername/minerva)"
```

---

## Error Handling

### Error Categories

1. **Network Errors**
   - Timeout, DNS failure, connection refused
   - **Handling:** Retry with exponential backoff (3 attempts)

2. **HTTP Errors**
   - 404 Not Found, 403 Forbidden, 500 Internal Server Error
   - **Handling:** Log and skip (no retry for 4xx), retry 5xx

3. **Content Extraction Errors**
   - Empty page, no main content detected
   - **Handling:** Log warning, save empty record (mark as failed extraction)

4. **Rate Limiting (429)**
   - Too many requests
   - **Handling:** Exponential backoff (start at 10s, double each time)

5. **JavaScript Errors**
   - Page failed to load dynamic content
   - **Handling:** Retry with longer wait, fallback to static HTML

6. **Database Errors**
   - Connection lost, constraint violation
   - **Handling:** Critical error, stop scraping, rollback transaction

### Error Logging

```python
# Error log entry
{
    "timestamp": "2025-11-13T10:23:45Z",
    "book_id": 123,
    "url": "https://example.com/page",
    "error_type": "HTTPError",
    "error_code": 404,
    "error_message": "Page not found",
    "retry_count": 3,
    "stack_trace": "...",
    "context": {
        "user_agent": "...",
        "referrer": "...",
        "scrape_config": {...}
    }
}
```

### Failure Recovery

```bash
# Retry failed pages from previous scrape
minerva retry <book_id>

# View failed pages
minerva show-failures <book_id>

# Export failures for manual review
minerva export-failures <book_id> --format csv
```

---

## Performance Considerations

### Optimization Strategies

1. **Parallel Page Fetching**
   - Use asyncio to fetch multiple pages concurrently (limit: 5 concurrent)
   - Respects rate limiting (global semaphore)

2. **Batch Embedding Generation**
   - Process chunks in batches of 100 (OpenAI limit: 8191 tokens/request)
   - Reduces API calls, improves throughput

3. **Incremental Saves**
   - Save each page immediately after extraction (don't wait for entire scrape)
   - Prevents data loss on interruption

4. **Lazy Playwright Initialization**
   - Only launch browser when needed (not during discovery phase if sitemap exists)

5. **Content Caching**
   - Cache robots.txt per domain (avoid redundant fetches)
   - Cache sitemap.xml (valid for duration of scrape)

### Resource Usage

**CPU:**
- Playwright browser: 1-2 cores per session
- Trafilatura parsing: Low (<10% CPU)
- MinHash deduplication: Moderate (50-70% CPU burst)

**Memory:**
- Playwright browser: ~200-300 MB
- Content buffering: ~10 MB per page (released after save)
- MinHash LSH: ~50 MB for 10,000 chunks

**Disk:**
- Playwright browser cache: ~100 MB
- Logs: ~1 MB per 100 pages scraped
- Database: ~5 KB per page (metadata), ~500 bytes per chunk

**Network:**
- Page fetch: 50 KB - 2 MB per page (avg: 300 KB)
- Embedding API: 1 KB per chunk (upload), 4 KB per embedding (download)

### Estimated Scraping Times

| Pages | Duration | Cost (Embeddings) |
|-------|----------|-------------------|
| 10    | 1-2 min  | $0.005            |
| 50    | 5-10 min | $0.025            |
| 100   | 10-20 min| $0.050            |
| 500   | 1-2 hours| $0.250            |
| 1000  | 2-4 hours| $0.500            |

*Assumes: 500 words/page, 1 chunk/page avg, adaptive rate limiting*

---

## Security & Ethics

### Ethical Scraping Practices

1. **Respect robots.txt**
   - Parse and honor crawl-delay directives
   - Skip disallowed paths
   - Option to override with `--ignore-robots` (warn user)

2. **Identify Scraper**
   - Custom user agent: `Minerva/1.0 (+https://github.com/yourusername/minerva)`
   - Include contact info in user agent

3. **Rate Limiting**
   - Default: adaptive delays (200ms - 2s)
   - Never exceed 5 requests/second per domain

4. **Respect Copyright**
   - Don't scrape paywalled content
   - Store for personal use only (knowledge base)
   - Preserve attribution (source URLs)

### Security Considerations

1. **Input Validation**
   - Validate URL format (http/https only)
   - Block local/private IP ranges (SSRF protection)
   - Sanitize URLs (prevent injection)

2. **Resource Limits**
   - Max page size: 10 MB (prevent memory exhaustion)
   - Timeout: 30s per page
   - Max concurrent requests: 5

3. **Data Privacy**
   - Don't log sensitive data (credentials in URLs)
   - Sanitize error messages (hide internal paths)

4. **Dependency Security**
   - Pin dependency versions
   - Regular security audits (dependabot)
   - Playwright auto-updates (browser binaries)

---

## Testing Strategy

### Unit Tests

```python
# Test content extraction
def test_trafilatura_extraction():
    html = load_fixture('sample_article.html')
    content = ContentExtractor.extract_with_trafilatura(html)
    assert content.word_count > 100
    assert 'peptide' in content.text.lower()

# Test deduplication
def test_page_deduplication():
    pages = [
        ExtractedContent(text="Same content", url="url1"),
        ExtractedContent(text="Same content", url="url2"),
        ExtractedContent(text="Different content", url="url3"),
    ]
    unique = ContentProcessor.deduplicate_pages(pages)
    assert len(unique) == 2

# Test retry logic
@pytest.mark.asyncio
async def test_retry_with_backoff():
    mock_page = MockPlaywrightPage(fail_count=2)
    html = await fetch_page_with_retry(mock_page, RetryConfig(max_retries=3))
    assert html is not None
    assert mock_page.call_count == 3
```

### Integration Tests

```python
# Test end-to-end scraping
@pytest.mark.integration
async def test_scrape_small_website():
    # Use local test server with known content
    url = "http://localhost:8888/test-site"
    result = await scrape_website(url, ScrapeConfig(max_pages=5))

    assert result.success_count == 5
    assert result.failure_count == 0

    # Verify database
    book = db.get_book_by_url(url)
    assert book.source_type == 'website'
    assert book.page_count == 5
    assert len(book.chunks) > 0

# Test sitemap discovery
@pytest.mark.integration
async def test_sitemap_discovery():
    url = "http://localhost:8888/site-with-sitemap"
    pages = await WebsiteDiscovery.discover_pages(url, DiscoveryConfig())
    assert len(pages) == 10  # Known sitemap size
    assert all(p.startswith(url) for p in pages)
```

### Test Fixtures

```
tests/
├── fixtures/
│   ├── sample_wordpress_page.html
│   ├── sample_static_page.html
│   ├── sample_javascript_page.html
│   ├── sample_sitemap.xml
│   └── sample_robots.txt
├── test_discovery.py
├── test_extraction.py
├── test_processing.py
└── test_orchestrator.py
```

### Manual Testing Checklist

- [ ] WordPress site (example: peptidedosages.com)
- [ ] Static HTML site (example: documentation site)
- [ ] JavaScript-heavy SPA (example: React site)
- [ ] Site with sitemap.xml
- [ ] Site without sitemap (requires crawling)
- [ ] Site with pagination
- [ ] Site with infinite scroll
- [ ] Site with 404 pages (test error handling)
- [ ] Site with rate limiting (test backoff)
- [ ] Large site (>100 pages, test --max-pages)

---

## Deployment

### Dependencies

```toml
# pyproject.toml additions
[tool.poetry.dependencies]
playwright = "^1.40.0"
trafilatura = "^1.6.2"
readability-lxml = "^0.8.1"
beautifulsoup4 = "^4.12.2"
lxml = "^4.9.3"
rich = "^13.7.0"
datasketch = "^1.6.4"  # MinHash for deduplication
extruct = "^0.16.0"  # Schema.org extraction
```

### Installation

```bash
# Install dependencies
poetry install

# Install Playwright browsers
poetry run playwright install chromium
```

### Database Migration

```bash
# Generate migration
alembic revision -m "Add website scraping support"

# Edit migration file (add source_type, metadata columns, failed_scrapes table)

# Apply migration
alembic upgrade head
```

### Configuration

```bash
# Update ~/.minerva/config.yaml with scraping defaults

# Set user agent (optional)
export MINERVA_USER_AGENT="Minerva/1.0 (+https://your-site.com)"
```

### Monitoring

```bash
# View logs
tail -f ~/.minerva/logs/scraping.log

# Check database
psql $DATABASE_URL -c "SELECT source_type, COUNT(*) FROM books GROUP BY source_type;"

# Monitor failed scrapes
psql $DATABASE_URL -c "SELECT url, error_message FROM failed_scrapes ORDER BY created_at DESC LIMIT 10;"
```

---

## Appendix

### Related Documentation
- [Brainstorming Session Results](../brainstorming-session-results.md)
- [Implementation Roadmap](./website-scraping-roadmap.md)
- [API Documentation](../api.md)

### References
- [Trafilatura Documentation](https://trafilatura.readthedocs.io/)
- [Playwright Python](https://playwright.dev/python/)
- [Readability Algorithm](https://github.com/mozilla/readability)
- [MinHash LSH](https://ekzhu.com/datasketch/)
- [robots.txt Spec](https://www.robotstxt.org/)

### Glossary
- **Sitemap:** XML file listing all pages on a website
- **Crawler:** Bot that recursively follows links to discover pages
- **Dynamic Content:** Content loaded via JavaScript after initial page load
- **Deduplication:** Removing duplicate or near-duplicate content
- **MinHash:** Probabilistic algorithm for estimating similarity
- **Trafilatura:** Python library for extracting main content from web pages
