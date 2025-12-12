# Website Scraping Implementation Roadmap

**Version:** 1.0
**Status:** Ready for Implementation
**Date:** 2025-11-13
**Owner:** Development Team

---

## Table of Contents
1. [Overview](#overview)
2. [Phase 1: Foundation (v1.0)](#phase-1-foundation-v10)
3. [Phase 2: Enhancement (v1.1)](#phase-2-enhancement-v11)
4. [Phase 3: Advanced Features (v2.0)](#phase-3-advanced-features-v20)
5. [Phase 4: Ecosystem (v2.5+)](#phase-4-ecosystem-v25)
6. [Timeline & Resources](#timeline--resources)
7. [Success Metrics](#success-metrics)
8. [Risk Mitigation](#risk-mitigation)

---

## Overview

### Vision
Transform Minerva from a Kindle-only knowledge extraction tool into a comprehensive multi-source knowledge base platform, starting with public website scraping.

### Principles
- **Ship Fast:** v1.0 in 1 week, iterate based on real usage
- **User Feedback:** Each phase informed by previous phase learnings
- **Quality Over Features:** Robust v1 > feature-rich v1
- **Future-Proof:** Architecture supports PDF, PubMed, auto-citations (v2+)

---

## Phase 1: Foundation (v1.0)

**Goal:** Ship production-ready website scraping with smart defaults and robust error handling

**Duration:** 5-7 days

**Status:** 🟡 Not Started

### Tasks

#### 1.1 Database Schema & Migration (Day 1 - 4 hours)
- [ ] Create Alembic migration for schema changes
- [ ] Add `source_type` enum field to `books` table
- [ ] Add metadata columns: `source_domain`, `published_date`, `word_count`
- [ ] Create `failed_scrapes` table for retry functionality
- [ ] Add indexes for performance
- [ ] Test migration on local database
- [ ] Update database documentation

**Owner:** Backend Dev
**Dependencies:** None
**Acceptance Criteria:**
- Migration runs successfully on fresh database
- Migration runs successfully on existing database with Kindle data
- All indexes created and optimized

---

#### 1.2 Core Discovery Module (Day 1-2 - 6 hours)
- [ ] Create `minerva/core/ingestion/website_discovery.py`
- [ ] Implement sitemap.xml detection and parsing
  - Check standard locations: `/sitemap.xml`, `/sitemap_index.xml`
  - Handle sitemap indexes (recursive parsing)
  - Extract URLs with priority/lastmod metadata
- [ ] Implement link crawler with BFS traversal
  - Extract all `<a href>` links using Playwright
  - Filter to internal links (domain-locked)
  - Track visited URLs (avoid cycles)
- [ ] Implement scope filtering
  - `--max-depth` limiting
  - `--max-pages` limiting
  - `--include-subdomains` flag
  - Domain-locked by default
- [ ] Write unit tests with mock sitemaps/pages
- [ ] Write integration tests with local test server

**Owner:** Backend Dev
**Dependencies:** None
**Acceptance Criteria:**
- Sitemap detection works on WordPress sites, documentation sites
- Crawler handles 100+ page sites without errors
- Respects domain boundaries and depth limits
- Test coverage >80%

---

#### 1.3 Content Extraction Module (Day 2-3 - 8 hours)
- [ ] Create `minerva/core/ingestion/content_extractor.py`
- [ ] Install and integrate Trafilatura
  - Primary extraction method
  - Quality check (word count, text-to-HTML ratio)
- [ ] Install and integrate Readability (fallback)
- [ ] Implement metadata extraction
  - OpenGraph tags
  - Standard meta tags (author, description)
  - Schema.org JSON-LD parsing (use `extruct` library)
  - Content inference for missing metadata
- [ ] Implement basic HTML fallback (strip tags)
- [ ] Write unit tests with diverse HTML fixtures
  - WordPress article
  - Static HTML page
  - JavaScript-heavy page
  - Page with rich metadata
  - Page with minimal metadata

**Owner:** Backend Dev
**Dependencies:** None
**Acceptance Criteria:**
- Extracts clean text from WordPress sites (peptidedosages.com)
- Extracts metadata with >90% accuracy on standard sites
- Handles edge cases (empty pages, malformed HTML)
- Test coverage >85%

---

#### 1.4 Deduplication & Processing (Day 3 - 4 hours)
- [ ] Create `minerva/core/ingestion/content_processor.py`
- [ ] Implement page-level deduplication
  - SHA256 hash of content
  - Skip exact duplicates
- [ ] Implement chunk-level deduplication
  - Install `datasketch` library (MinHash)
  - Configure LSH with 95% similarity threshold
  - Remove near-duplicate chunks
- [ ] Integrate with existing `SemanticChunker`
  - Reuse 500-800 token chunking logic
  - Preserve paragraph boundaries
- [ ] Write unit tests for deduplication
  - Exact duplicates
  - Near-duplicates (95% similar)
  - Unique content preservation

**Owner:** Backend Dev
**Dependencies:** 1.3 (Content Extraction)
**Acceptance Criteria:**
- Removes 100% of exact duplicate pages
- Removes >90% of near-duplicate chunks (tested with synthetic data)
- Preserves all unique content
- Performance: <5s for 1000 chunks

---

#### 1.5 Orchestration & Error Handling (Day 3-4 - 8 hours)
- [ ] Create `minerva/core/ingestion/web_scraper_orchestrator.py`
- [ ] Implement main pipeline
  - Initialize Playwright session
  - Call discovery module
  - Iterate through pages
  - Call extraction for each page
  - Save incrementally to database
  - Call processing after all pages scraped
- [ ] Implement retry logic with exponential backoff
  - 3 max retries per page
  - Backoff: 1s, 2s, 4s
  - Configurable via config file
- [ ] Implement adaptive rate limiting
  - Start at 200ms delay
  - Increase to 2s if error rate >20%
  - Adjust based on server response times
- [ ] Implement dynamic content handling
  - Wait for network idle (Playwright built-in)
  - Detect and click pagination buttons
  - Detect and handle infinite scroll
- [ ] Implement incremental saves
  - Save each page immediately after extraction
  - Update book status after completion
  - Store failed URLs in `failed_scrapes` table
- [ ] Write integration tests
  - End-to-end scrape of small test site
  - Simulated network failures (test retry)
  - Simulated rate limiting (test backoff)

**Owner:** Backend Dev
**Dependencies:** 1.2 (Discovery), 1.3 (Extraction), 1.4 (Processing)
**Acceptance Criteria:**
- Handles network failures gracefully (retries, continues)
- Saves progress incrementally (recoverable from interruption)
- Adapts rate limiting based on server response
- Handles pagination and infinite scroll automatically
- Integration tests pass on diverse test sites

---

#### 1.6 CLI Interface (Day 4-5 - 6 hours)
- [ ] Update `minerva/cli/app.py`
- [ ] Add `ingest website <url>` subcommand
- [ ] Add auto-detect logic to `ingest <url>`
  - `read.amazon.com/*` → Kindle
  - Everything else → Website
- [ ] Implement CLI options
  - `--max-pages INTEGER`
  - `--max-depth INTEGER`
  - `--include-subdomains`
  - `--verbose`
  - `--quiet`
  - `--output-log PATH`
- [ ] Implement `retry <book_id>` command
  - Fetch failed URLs from `failed_scrapes` table
  - Re-attempt scraping
  - Update database on success
- [ ] Write CLI tests
  - Test option parsing
  - Test auto-detection
  - Test command execution (mocked)

**Owner:** Backend Dev
**Dependencies:** 1.5 (Orchestrator)
**Acceptance Criteria:**
- `minerva ingest website <url>` works end-to-end
- Auto-detect correctly identifies Kindle vs. website URLs
- All CLI options functional
- `minerva retry` successfully retries failed pages
- CLI tests pass

---

#### 1.7 Progress Dashboard (Day 5 - 5 hours)
- [ ] Install `rich` library
- [ ] Create progress tracker in orchestrator
- [ ] Implement live dashboard
  - Progress bar (pages scraped / total)
  - Real-time stats (speed, errors, estimated time)
  - Current page being scraped
  - Success/error counts
- [ ] Implement summary report
  - Total pages scraped, failed, duration
  - Content stats (words, chunks)
  - Cost estimate (embeddings)
  - List of failed URLs
  - Next steps suggestions
- [ ] Test on long-running scrapes (>50 pages)

**Owner:** Backend Dev
**Dependencies:** 1.5 (Orchestrator)
**Acceptance Criteria:**
- Dashboard updates in real-time during scrape
- Summary report is comprehensive and actionable
- Terminal output is beautiful and informative
- Works in both TTY and non-TTY environments

---

#### 1.8 Configuration & Documentation (Day 6 - 4 hours)
- [ ] Update `~/.minerva/config.yaml` with scraping defaults
- [ ] Document all configuration options
- [ ] Update README.md
  - Add website scraping section
  - Add examples
  - Add troubleshooting guide
- [ ] Write user guide: `docs/user-guide/website-scraping.md`
  - Getting started
  - Common use cases
  - Advanced options
  - Troubleshooting
- [ ] Update API documentation

**Owner:** Backend Dev + Docs Writer
**Dependencies:** All above tasks
**Acceptance Criteria:**
- Configuration file is well-commented
- README is updated with clear examples
- User guide covers all common scenarios
- API documentation is accurate

---

#### 1.9 Testing & QA (Day 6-7 - 8 hours)
- [ ] Run full test suite
  - Unit tests (all modules)
  - Integration tests (end-to-end)
  - Manual testing (diverse websites)
- [ ] Test on production websites
  - [ ] peptidedosages.com (WordPress, dynamic)
  - [ ] documentation site (static HTML)
  - [ ] blog site (pagination)
  - [ ] Large site (>100 pages, test limits)
- [ ] Load testing
  - Test with 500+ page site
  - Monitor memory usage, performance
- [ ] Edge case testing
  - Empty pages, 404s, timeouts
  - Malformed HTML
  - Sites with no content
- [ ] Bug fixes and refinements
- [ ] Performance optimization

**Owner:** QA + Backend Dev
**Dependencies:** All above tasks
**Acceptance Criteria:**
- All unit tests pass (>80% coverage)
- All integration tests pass
- Manual testing successful on 5+ diverse websites
- No critical bugs, no memory leaks
- Performance meets benchmarks (<2 min for 50 pages)

---

#### 1.10 Production Deployment (Day 7 - 2 hours)
- [ ] Database migration on production (Neon)
- [ ] Deploy updated code to Fly.io
- [ ] Smoke test on production
- [ ] Update production documentation
- [ ] Announce release to users

**Owner:** DevOps + Backend Dev
**Dependencies:** 1.9 (Testing)
**Acceptance Criteria:**
- Migration runs successfully on production database
- Production deployment stable
- Smoke tests pass
- No regressions in Kindle ingestion

---

### v1.0 Deliverables

✅ **Core Features:**
- Website scraping with hybrid discovery (sitemap → crawler)
- Smart content extraction (Trafilatura + Readability)
- Metadata extraction (meta tags, Schema.org, inference)
- Robust error handling (retry, incremental saves)
- Adaptive rate limiting
- Deduplication (page-level + chunk-level)
- Live progress dashboard (rich)
- CLI: `minerva ingest website <url>` with options
- CLI: `minerva retry <book_id>`

✅ **Quality Assurance:**
- >80% test coverage
- Tested on 5+ diverse websites
- Performance benchmarks met
- Documentation complete

✅ **Non-Functional:**
- Production-ready error handling
- Resumable scraping (incremental saves)
- Beautiful UX (rich dashboard + summary)
- Extensible architecture (ready for v2 features)

---

## Phase 2: Enhancement (v1.1)

**Goal:** Refine v1 based on user feedback, add AI extraction option

**Duration:** 3-5 days

**Status:** 🔴 Blocked (depends on v1.0 completion + user feedback)

### Tasks

#### 2.1 User Feedback Analysis (Day 1 - 2 hours)
- [ ] Collect user feedback (GitHub issues, Discord, direct messages)
- [ ] Analyze production logs for common errors
- [ ] Identify top pain points and feature requests
- [ ] Prioritize improvements

---

#### 2.2 AI-Powered Content Extraction (Day 1-2 - 6 hours)
- [ ] Implement `--use-ai-extraction` flag
- [ ] Integrate GPT-4o-mini for complex page extraction
  - Prompt engineering for content extraction
  - Handle long HTML (truncate to token limits)
  - Cost optimization (only use when heuristics fail)
- [ ] Add AI extraction as fallback option
  - Try Trafilatura → Readability → AI
- [ ] Test cost and quality
  - Compare AI extraction vs. Trafilatura on 50 pages
  - Measure cost per page
  - Measure quality improvement
- [ ] Document when to use AI extraction

**Owner:** Backend Dev
**Dependencies:** v1.0 deployed, user feedback
**Acceptance Criteria:**
- AI extraction produces higher quality than Trafilatura on complex layouts
- Cost is acceptable (<$0.01 per page)
- Documented guidelines for when to use flag

---

#### 2.3 Robots.txt Respect (Day 2 - 4 hours)
- [ ] Implement robots.txt parser
- [ ] Check robots.txt before scraping
- [ ] Honor crawl-delay directive
- [ ] Skip disallowed paths
- [ ] Add `--ignore-robots` flag (with warning)
- [ ] Test on sites with restrictive robots.txt

**Owner:** Backend Dev
**Dependencies:** v1.0 deployed
**Acceptance Criteria:**
- Respects robots.txt by default
- Warns user when using `--ignore-robots`
- Doesn't scrape disallowed paths

---

#### 2.4 Enhanced Metadata Storage (Day 2-3 - 4 hours)
- [ ] Add object storage integration (MinIO/Cloudflare R2)
  - Install `boto3` (S3-compatible client)
  - Configure connection to MinIO or R2
- [ ] Add `--preserve-html` flag
  - Store raw HTML to object storage
  - Store reference URL in database
  - Enable archival use cases
- [ ] Test on large scrapes (100+ pages)

**Owner:** Backend Dev
**Dependencies:** v1.0 deployed, MinIO/R2 setup
**Acceptance Criteria:**
- HTML preserved to object storage when flag used
- PostgreSQL contains only metadata + text (not HTML)
- Can retrieve archived HTML via URL

---

#### 2.5 Performance Optimization (Day 3-4 - 6 hours)
- [ ] Implement parallel page fetching
  - Use asyncio for concurrent requests
  - Limit: 5 concurrent pages
  - Coordinate with rate limiting (global semaphore)
- [ ] Optimize database queries
  - Batch inserts for chunks
  - Reduce transaction overhead
- [ ] Profile and optimize bottlenecks
- [ ] Load test with 1000+ page site

**Owner:** Backend Dev
**Dependencies:** v1.0 deployed
**Acceptance Criteria:**
- 2-3x faster scraping (tested on 100-page site)
- No increase in error rate
- Memory usage stable

---

#### 2.6 Bug Fixes & Refinements (Day 4-5 - 4 hours)
- [ ] Fix bugs reported by users
- [ ] Improve error messages
- [ ] Enhance documentation based on feedback
- [ ] Refactor code for maintainability

**Owner:** Backend Dev
**Dependencies:** User feedback collected
**Acceptance Criteria:**
- All critical bugs fixed
- User-reported issues addressed
- Code quality improved (linting, refactoring)

---

### v1.1 Deliverables

✅ **New Features:**
- AI-powered content extraction (optional)
- Robots.txt respect
- HTML archival to object storage (optional)

✅ **Improvements:**
- 2-3x faster scraping (parallel fetching)
- Better error messages
- Refined documentation
- Bug fixes from v1.0

---

## Phase 3: Advanced Features (v2.0)

**Goal:** Scheduled scraping, auto-citations, PDF support

**Duration:** 3-4 weeks

**Status:** 🔴 Blocked (depends on v1.1 completion)

### Features

#### 3.1 Scheduled Scraping (Week 1-2)
- [ ] Integrate job scheduler (APScheduler or Celery)
- [ ] CLI: `minerva schedule <book_id> --cron "0 0 * * *"`
- [ ] Implement change detection
  - Compare content hash
  - Detect new pages (sitemap diff)
  - Detect updated pages (last-modified header)
- [ ] Implement incremental updates
  - Only re-scrape changed pages
  - Update chunks incrementally
  - Preserve existing embeddings for unchanged content
- [ ] Web UI for managing schedules (optional)

**Expected Impact:**
- Keep knowledge base fresh without manual intervention
- Cost-efficient (only process changes)

---

#### 3.2 Auto-Ingest Cited Links (Week 2-3)
- [ ] Implement citation extraction
  - Regex patterns for URLs in text
  - Detect reference sections
  - Parse bibliography
- [ ] Implement link validation and filtering
  - Check if already ingested
  - Filter by domain whitelist/blacklist
  - Validate URL accessibility
- [ ] Implement recursive scraping with depth limit
  - CLI: `minerva ingest website <url> --follow-citations --citation-depth 2`
- [ ] Build knowledge graph
  - Track citation relationships in database
  - Visualize graph (optional)

**Expected Impact:**
- Automatic knowledge graph building
- Discover related content without manual search

---

#### 3.3 PDF Ingestion (Week 3)
- [ ] Integrate PDF parsing library (pymupdf or pdfplumber)
- [ ] CLI: `minerva ingest pdf <path>`
- [ ] Extract text and metadata (title, author, date)
- [ ] Handle scanned PDFs (integrate Tesseract OCR)
- [ ] Preserve document structure (headings, sections)
- [ ] Test on research papers, clinical protocols

**Expected Impact:**
- Support for research papers, clinical protocols, books

---

#### 3.4 PubMed Integration (Week 4)
- [ ] Integrate PubMed API
- [ ] CLI: `minerva ingest pubmed <pmid>`
- [ ] Extract abstract, full text (PubMed Central)
- [ ] Handle paywalls (gracefully skip or use preprint servers)
- [ ] Extract structured data (methods, results, conclusions)
- [ ] Build citation graph

**Expected Impact:**
- Access to medical research papers
- Integration with peptide research community

---

### v2.0 Deliverables

✅ **Major Features:**
- Scheduled scraping with change detection
- Auto-ingest cited links (knowledge graph)
- PDF ingestion support
- PubMed integration

✅ **Quality:**
- Robust scheduling (handles failures, retries)
- Incremental updates (cost-efficient)
- Comprehensive testing

---

## Phase 4: Ecosystem (v2.5+)

**Goal:** Multi-user, API, advanced AI features

**Duration:** TBD (6+ months)

**Status:** 🔴 Future (Vision Phase)

### Potential Features

#### 4.1 Multi-User & Collaboration
- User authentication and authorization
- Shared knowledge bases
- Annotation and quality ratings
- Conflict resolution

#### 4.2 API Endpoints
- `POST /api/v1/ingest/website` (programmatic scraping)
- `GET /api/v1/sources` (list all sources)
- `DELETE /api/v1/sources/:id` (remove source)

#### 4.3 Multi-Modal Content
- Extract and embed images (CLIP)
- Extract tables and charts (OCR + parsing)
- Visual search and retrieval

#### 4.4 Real-Time Knowledge Graph
- Graph database integration (Neo4j)
- Entity extraction and linking (NER)
- Visual graph exploration UI

#### 4.5 Automated Expert Synthesis
- AI agent for literature review
- Multi-document summarization
- Contradiction detection
- Source credibility scoring

---

## Timeline & Resources

### Phase 1: v1.0 Foundation
- **Duration:** 5-7 days
- **Team:** 1 Backend Dev + 0.5 QA
- **Cost:** ~$50 (OpenAI API for testing)

### Phase 2: v1.1 Enhancement
- **Duration:** 3-5 days
- **Team:** 1 Backend Dev
- **Cost:** ~$30 (AI extraction testing)

### Phase 3: v2.0 Advanced Features
- **Duration:** 3-4 weeks
- **Team:** 1-2 Backend Devs + 0.5 QA
- **Cost:** ~$200 (API testing, infrastructure)

### Phase 4: v2.5+ Ecosystem
- **Duration:** TBD (6+ months)
- **Team:** 2-3 Devs + 1 Designer + 1 QA
- **Cost:** TBD (infrastructure scaling)

### Total Timeline
- **v1.0 MVP:** Week 1
- **v1.1 Refinement:** Week 2-3
- **v2.0 Advanced:** Month 2-3
- **v2.5+ Vision:** 6+ months

---

## Success Metrics

### Phase 1: v1.0 Foundation

**Adoption Metrics:**
- 50+ websites scraped by users in first month
- 10+ GitHub stars/feedback submissions
- <5 critical bugs reported

**Technical Metrics:**
- 100% of tested websites scraped successfully
- <5% error rate on production scrapes
- <2 minutes scraping time for 50-page sites
- >80% test coverage

**User Satisfaction:**
- >80% positive feedback on UX (progress dashboard, summary)
- <10% users require troubleshooting support
- >50% users use auto-detect (vs. explicit source type)

---

### Phase 2: v1.1 Enhancement

**Adoption Metrics:**
- 100+ websites scraped in month 2
- 10+ users adopt AI extraction flag
- 5+ users use HTML preservation

**Technical Metrics:**
- 2-3x faster scraping (parallel fetching)
- <3% error rate on production scrapes
- AI extraction quality improvement >20% on complex sites

**Cost Metrics:**
- AI extraction cost <$0.01 per page
- OpenAI API costs <$10/month for typical user

---

### Phase 3: v2.0 Advanced Features

**Adoption Metrics:**
- 50+ scheduled scrapes active
- 20+ users adopt PDF ingestion
- 10+ users use auto-citation ingestion

**Technical Metrics:**
- Change detection accuracy >95%
- Incremental update cost savings >80%
- PDF extraction accuracy >90%

**Impact Metrics:**
- Knowledge base growth rate increases 3x (scheduled updates)
- Citation graph depth averages 3+ levels

---

## Risk Mitigation

### Risk 1: Website Anti-Bot Measures
**Probability:** Medium
**Impact:** High (blocks scraping entirely)

**Mitigation:**
- Use respectful rate limiting and robots.txt compliance
- Rotate user agents (if needed)
- Document known problematic sites
- Provide troubleshooting guide for users

**Fallback:**
- Offer manual HTML upload feature

---

### Risk 2: Poor Content Extraction Quality
**Probability:** Medium
**Impact:** Medium (reduces knowledge quality)

**Mitigation:**
- Test on diverse websites during QA
- Implement fallback extraction methods (Trafilatura → Readability → AI)
- Add `--use-ai-extraction` for complex sites
- Collect user feedback on extraction quality

**Fallback:**
- Allow users to edit extracted content

---

### Risk 3: Excessive OpenAI API Costs
**Probability:** Low
**Impact:** Medium (user cost burden)

**Mitigation:**
- Batch embedding generation (reduce API calls)
- Deduplicate chunks (reduce embedding count)
- Provide cost estimates before scraping
- Monitor and alert on high costs

**Fallback:**
- Offer local embedding models (slower, free)

---

### Risk 4: Database Performance Degradation
**Probability:** Low
**Impact:** Medium (slow queries, poor UX)

**Mitigation:**
- Add proper indexes on `source_type`, `source_domain`
- Batch inserts for chunks
- Monitor query performance in production
- Optimize pgvector queries

**Fallback:**
- Database sharding or read replicas

---

### Risk 5: User Confusion (Complex CLI)
**Probability:** Low
**Impact:** Low (reduced adoption)

**Mitigation:**
- Provide smart defaults (auto-detect, adaptive limits)
- Clear documentation with examples
- Beautiful progress feedback (rich dashboard)
- Interactive prompts for first-time users (optional)

**Fallback:**
- Build web UI (v2.5+)

---

## Appendix

### Related Documentation
- [Brainstorming Session Results](../brainstorming-session-results.md)
- [Website Scraping Architecture](./website-scraping-architecture.md)
- [User Guide: Website Scraping](../user-guide/website-scraping.md) (TODO)

### Change Log
- **2025-11-13:** Initial roadmap created
- **[Future]:** Update after v1.0 completion

### Feedback
- Submit feedback: GitHub Issues
- Feature requests: GitHub Discussions
- Questions: Discord #minerva-dev

---

*Roadmap subject to change based on user feedback and technical discoveries.*
