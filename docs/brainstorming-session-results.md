# Brainstorming Session Results

**Session Date:** 2025-11-13
**Facilitator:** Business Analyst Mary
**Participant:** User

---

## Executive Summary

**Topic:** Website Scraping Architecture for Minerva - Use Cases, Features, and Technical Approaches

**Session Goals:** Design and brainstorm the perfect solution for website scraping functionality in Minerva, ready for immediate implementation. Focus on architecture, technical approaches, and feature set that integrates seamlessly with existing Kindle ingestion pipeline.

**Example Site Analyzed:** [peptidedosages.com](https://peptidedosages.com/) - WordPress-based peptide reference site with dynamic JavaScript content, REST API endpoints, structured protocols (moderate-to-high scraping complexity)

**Techniques Used:**
- Question Storming (10 min)
- Morphological Analysis (25 min)
- SCAMPER Refinement - Substitute, Combine, Adapt (10 min)

**Total Ideas Generated:** 12 architectural dimensions explored, 60+ options evaluated, 12 final decisions made

**Key Themes Identified:**
- Leverage existing Minerva architecture (Playwright, PostgreSQL, semantic chunking pipeline)
- Optimize for AI consumption (clean text, quality embeddings) vs. visual archival
- Production-ready resilience (error handling, retries, incremental saves)
- User-friendly CLI with smart defaults + power-user configurability
- Future-proof design (extensible for PDF, PubMed, auto-link ingestion)

---

## Technique Sessions

### Morphological Analysis - 25 minutes

**Description:** Systematic exploration of technical architecture by breaking down key decision dimensions and evaluating options for each component.

**Ideas Generated:**

#### 1. Content Discovery Method
**Decision:** Hybrid approach (sitemap.xml → crawler fallback)
- Check for sitemap.xml first, parse all URLs
- Fall back to recursive link crawling if no sitemap found
- Maximizes coverage and reliability

#### 2. Scraping Engine
**Decision:** Playwright
- Already in Minerva stack (Kindle ingestion)
- Handles JavaScript, dynamic content, infinite scroll
- Sees exactly what users see (browser automation)
- Consistent architecture across sources

#### 3. Content Extraction Strategy
**Decision:** Smart parsing + optional AI cleanup
- Primary: Readability/Trafilatura algorithms (fast, free)
- Optional: `--use-ai-extraction` flag for complex pages (GPT-4o-mini)
- Mirrors proven Kindle AI cleanup pattern

#### 4. Crawl Scope & Boundaries
**Decision:** Domain-locked default + configurable limits
- Domain-locked by default (stay within same domain)
- Optional flags: `--max-depth <N>`, `--max-pages <N>`, `--include-subdomains`
- Safety valve prevents runaway scraping

#### 5. Dynamic Content Handling
**Decision:** Smart detection with automatic adaptation
- Try network idle first (catches most cases)
- Detect pagination → click through "next" buttons
- Detect infinite scroll → scroll-to-bottom strategy
- No user configuration required

#### 6. Data Storage & Integration
**Decision:** Minimal schema change - add `source_type` enum to Books table
- New field: `source_type` enum ('kindle'|'website'|'pdf')
- Everything else reuses existing schema
- Simplest migration path, no API breakage
- Future-proof for additional sources

#### 7. CLI Interface Design
**Decision:** Explicit source type with auto-detect fallback
```bash
# Explicit (recommended)
minerva ingest website <url> [options]
minerva ingest kindle <url>

# Auto-detect fallback
minerva ingest <url>  # Detects read.amazon.com → kindle, else → website
```
- Clear intent when explicit
- Convenient auto-detection for common cases
- Scales to future sources: `minerva ingest pdf <path>`

#### 8. Error Handling & Resilience
**Decision:** Retry + continue + incremental saves
- Retry failed pages (3 attempts with backoff)
- Continue scraping on persistent failures
- Save successful pages immediately (resume-able)
- Summary report at end: "95/100 pages succeeded, 5 failed"

#### 9. Rate Limiting & Politeness
**Decision:** Adaptive throttling
- Start fast, auto-adjust based on server response
- Slow down if errors detected
- Speed up if server responds quickly
- Intelligent and server-friendly

#### 10. Progress Tracking & User Feedback
**Decision:** Live dashboard using `rich` library
- Real-time stats: pages/min, errors, retries, estimated time remaining
- Modern CLI UX (similar to pytest, npm)
- Beautiful and informative for long-running scrapes

#### 11. Metadata Extraction & Enrichment
**Decision:** Smart metadata with priority cascade
- Priority: Meta tags → Schema.org markup → content inference
- Store: URL, title, description, author, dates, domain, word count
- Optional: `--preserve-html` flag stores raw HTML to object storage
- Comprehensive context without bloat

#### 12. Content Deduplication
**Decision:** Page-level exact + chunk-level fuzzy
- Skip exact duplicate pages (hash-based, fast)
- Dedupe similar chunks after processing (MinHash/SimHash)
- Optimal storage efficiency
- Preserves unique insights from similar pages

**Insights Discovered:**
- All decisions align with existing Minerva patterns (consistency)
- Focus on "AI consumption" (clean text) vs. "visual archival" (HTML)
- Production-ready resilience built-in from start
- Extensible foundation for future sources (PDF, PubMed, auto-citations)

**Notable Connections:**
- Website scraping mirrors Kindle pipeline: capture → extract → clean → chunk → embed
- Same AI cleanup pattern (`--use-ai-extraction` ≈ `--use-ai-formatting`)
- Object storage (MinIO/R2) available for future HTML archival without PostgreSQL bloat

---

### SCAMPER Refinement - 10 minutes

**Description:** Applied creative pressure to challenge assumptions and refine architectural decisions.

**S - Substitute:**
- Ruled OUT: Paid services (Firecrawl) - constraint: must be free/self-hosted
- Storage option: MinIO (local) or Cloudflare R2 (cloud) available for optional HTML preservation
- Priority: Cheapest + Fastest + Most reliable

**C - Combine:**
- Core purpose clarified: Knowledge base for AI consumption (RAG/semantic search)
- Future v2 feature identified: Auto-ingest cited links from books/articles (build knowledge graph)

**A - Adapt:**
- Adapt proven patterns:
  - **Trafilatura** - academic-grade content extraction
  - **Readability algorithm** (Mozilla) - declutter, find main content
  - **Common Crawl** approach - respectful robots.txt, adaptive delays
  - All free, battle-tested, production-ready

---

## Idea Categorization

### Immediate Opportunities
*Ideas ready to implement now*

1. **Core Website Scraping Pipeline (v1)**
   - **Description:** Full implementation of website scraping with hybrid discovery (sitemap → crawler), Playwright engine, smart content extraction, and production-ready error handling
   - **Why immediate:** All architectural decisions made, leverages existing Minerva infrastructure, no paid dependencies
   - **Resources needed:**
     - Python libraries: `playwright`, `trafilatura`, `readability-lxml`, `rich`, `beautifulsoup4`
     - Playwright browser installation
     - Database migration for `source_type` field
   - **Estimated effort:** 2-3 days development + 1 day testing

2. **CLI Command Structure**
   - **Description:** Implement `minerva ingest website <url>` with auto-detect fallback, following existing Kindle patterns
   - **Why immediate:** Design is clear, consistent with existing CLI, minimal code changes to existing ingest command
   - **Resources needed:** CLI framework already in place (Typer)
   - **Estimated effort:** 4-6 hours

3. **Smart Content Extraction (Heuristics)**
   - **Description:** Integrate Trafilatura + Readability for intelligent main content extraction
   - **Why immediate:** Libraries are mature, proven, free; handles WordPress and standard sites well
   - **Resources needed:** Library integration, testing on sample sites
   - **Estimated effort:** 6-8 hours

4. **Adaptive Rate Limiting**
   - **Description:** Implement smart throttling that adjusts based on server response times and error rates
   - **Why immediate:** Prevents bot detection, respectful to servers, protects Minerva from rate limiting
   - **Resources needed:** Simple algorithm with exponential backoff on errors
   - **Estimated effort:** 3-4 hours

5. **Live Progress Dashboard**
   - **Description:** Rich library integration showing real-time scraping progress, stats, and errors
   - **Why immediate:** Dramatically improves UX for long-running scrapes, `rich` is mature and well-documented
   - **Resources needed:** `rich` library (already popular in Python ecosystem)
   - **Estimated effort:** 4-5 hours

### Future Innovations
*Ideas requiring development/research*

1. **Scheduled Scraping (v2)**
   - **Description:** Cron-like scheduling to auto-refresh scraped websites, detect new content, update embeddings
   - **Development needed:**
     - Job scheduler (APScheduler or Celery)
     - Change detection algorithm (content diffing)
     - Incremental update logic (only process changed pages)
   - **Timeline estimate:** 1-2 weeks, depends on scheduler choice

2. **AI-Powered Content Extraction**
   - **Description:** Optional `--use-ai-extraction` flag using GPT-4o-mini for complex page layouts
   - **Development needed:**
     - Prompt engineering for content extraction
     - Cost optimization (only use when heuristics fail)
     - Quality comparison testing vs. Trafilatura
   - **Timeline estimate:** 3-5 days, includes testing and cost analysis

3. **Auto-Ingest Cited Links**
   - **Description:** Parse citations/references from ingested content (books/articles), automatically scrape cited sources, build knowledge graph
   - **Development needed:**
     - Citation extraction (regex patterns, ML models)
     - Link validation and filtering
     - Graph database integration or link tracking table
     - Recursive depth limits
   - **Timeline estimate:** 2-3 weeks, complex feature

4. **PDF Ingestion Support**
   - **Description:** Extend `minerva ingest pdf <path>` with text extraction, metadata parsing, same chunking/embedding pipeline
   - **Development needed:**
     - PDF parsing library (PyPDF2, pdfplumber, or pymupdf)
     - Handle scanned PDFs (OCR integration)
     - Preserve document structure (headings, sections)
   - **Timeline estimate:** 1 week

5. **PubMed/Research Paper Integration**
   - **Description:** `minerva ingest pubmed <pmid>` to scrape research papers, clinical trials, etc.
   - **Development needed:**
     - PubMed API integration
     - Handle paywalls (PubMed Central vs. publisher sites)
     - Extract structured data (abstract, methods, results)
     - Citation graph building
   - **Timeline estimate:** 2-3 weeks

6. **HTML Preservation to Object Storage**
   - **Description:** Optional `--preserve-html` flag stores raw HTML to MinIO/R2 for archival, linked from PostgreSQL metadata
   - **Development needed:**
     - S3-compatible storage integration (boto3)
     - URL generation for archived HTML
     - Storage lifecycle policies
   - **Timeline estimate:** 3-4 days

### Moonshots
*Ambitious, transformative concepts*

1. **Multi-Modal Content Extraction**
   - **Description:** Extract and process images, charts, tables from websites (not just text) - embed diagrams, preserve visual peptide protocols
   - **Transformative potential:** Captures knowledge that's inherently visual (dosage charts, molecular structures, protocol flowcharts)
   - **Challenges to overcome:**
     - Multi-modal embedding models (CLIP, ImageBind)
     - Image storage and retrieval
     - OCR for text in images
     - Significantly higher storage/compute costs

2. **Collaborative Knowledge Curation**
   - **Description:** Multi-user Minerva with shared knowledge bases, annotation, quality ratings on scraped content
   - **Transformative potential:** Community-curated peptide knowledge base (like Wikipedia meets ResearchGate)
   - **Challenges to overcome:**
     - User authentication and authorization
     - Conflict resolution (multiple users scraping same source)
     - Moderation and quality control
     - Infrastructure scaling (multi-tenancy)

3. **Real-Time Knowledge Graph**
   - **Description:** Live graph visualization showing relationships between books, articles, cited sources, topics, peptides - query by traversing graph
   - **Transformative potential:** Discover non-obvious connections, trace information provenance, visual knowledge exploration
   - **Challenges to overcome:**
     - Graph database (Neo4j, NetworkX)
     - Entity extraction and linking (NER, NLP)
     - Relationship inference algorithms
     - UI for graph visualization and interaction

4. **Automated Expert Synthesis**
   - **Description:** AI agent that automatically scrapes multiple sources on a topic (e.g., "BPC-157 dosing"), synthesizes findings, generates summary with citations
   - **Transformative potential:** From "search engine" to "research assistant" - automated literature review
   - **Challenges to overcome:**
     - Multi-document summarization at scale
     - Contradiction detection and resolution
     - Source credibility scoring
     - Hallucination prevention and fact-checking

### Insights & Learnings
*Key realizations from the session*

- **Consistency is power:** Reusing Playwright + existing pipeline means faster development, fewer bugs, consistent UX across all sources (Kindle, websites, future PDFs)

- **AI consumption optimization:** Understanding that the goal is "knowledge base for AI" (not archival) clarifies priorities - clean text extraction and quality embeddings matter more than preserving visual formatting

- **Adaptive over configurable:** Smart detection (pagination, scroll, dynamic content) reduces user friction compared to forcing users to configure scraping behavior per-site

- **Resilience from day one:** Building retry logic, incremental saves, and error reports into v1 (not v2) prevents technical debt and production issues

- **Future-proof minimalism:** Adding just `source_type` field (not full schema refactor) enables multi-source support while keeping v1 scope manageable

- **Progressive enhancement:** Core scraping in v1, AI extraction in v2, scheduled refresh in v3 - allows rapid iteration and user feedback before building advanced features

---

## Action Planning

### Top 3 Priority Ideas

#### #1 Priority: Core Website Scraping Pipeline (v1)

**Rationale:** Delivers immediate value, unblocks use cases, leverages existing infrastructure, no architectural unknowns

**Next steps:**
1. Database migration: Add `source_type` enum field to `books` table (+ Alembic migration)
2. Create `minerva/core/ingestion/web_scraper.py` module with:
   - `WebsiteDiscovery` class (sitemap parser + link crawler)
   - `ContentExtractor` class (Trafilatura + Readability integration)
   - `WebScraperOrchestrator` class (main pipeline)
3. Install dependencies: `playwright`, `trafilatura`, `readability-lxml`, `rich`, `beautifulsoup4`, `lxml`
4. Update CLI: Modify `minerva/cli/app.py` to support `ingest website <url>` with auto-detect
5. Implement adaptive rate limiting with exponential backoff
6. Add live progress dashboard using `rich.progress`
7. Implement deduplication (page-level hash, chunk-level similarity)
8. Write integration tests on sample websites (WordPress, static HTML, JavaScript-heavy)

**Resources needed:**
- Development environment with Playwright browsers installed
- Sample websites for testing (peptidedosages.com, others)
- Database migration tools (Alembic)

**Timeline:** 3-4 days (2-3 days development, 1 day testing and refinement)

---

#### #2 Priority: Metadata Extraction & Smart Parsing

**Rationale:** Critical for search quality and AI context - metadata (author, date, source) improves RAG relevance and citation quality

**Next steps:**
1. Implement metadata extractor with priority cascade:
   - HTML meta tags (OpenGraph, Twitter Cards, standard meta)
   - Schema.org JSON-LD markup
   - Content inference (heuristics for dates, authors in body text)
2. Update database schema: Add metadata fields to `books` table (author, published_date, description, source_domain)
3. Store extracted metadata alongside content chunks
4. Test on diverse websites (blogs, documentation, news sites, WordPress)
5. Handle edge cases: missing metadata, conflicting data sources, non-English content

**Resources needed:**
- Metadata extraction libraries: `extruct` (Schema.org), `newspaper3k` (optional)
- Sample sites with varied metadata quality

**Timeline:** 4-5 days (includes schema updates, extraction logic, testing)

---

#### #3 Priority: Error Handling & Resilience

**Rationale:** Production-ready scraping requires handling failures gracefully - prevents data loss, enables resume-ability, builds user trust

**Next steps:**
1. Implement retry logic with exponential backoff (3 attempts per page)
2. Save successful pages incrementally to database (don't wait for entire scrape to complete)
3. Log failed URLs to database table (`failed_scrapes`) with error messages
4. Generate summary report at end: "95/100 pages succeeded, 5 failed (see logs)"
5. Add `minerva retry <book_id>` command to retry failed pages
6. Test failure scenarios: network timeouts, 404s, server errors, rate limiting

**Resources needed:**
- Logging framework (Python `logging` module)
- Database table for failed scrapes
- Test infrastructure for simulating failures

**Timeline:** 2-3 days (includes retry logic, logging, recovery commands)

---

## Reflection & Follow-up

### What Worked Well
- Morphological analysis systematically covered all technical dimensions without missing critical decisions
- Example website (peptidedosages.com) provided concrete context for discussion
- Clear constraints (no paid services, optimize for AI consumption) focused decision-making
- Building on existing Minerva patterns (Playwright, Kindle pipeline) simplified architecture choices

### Areas for Further Exploration
- **Change detection algorithms:** How to efficiently detect when scraped sites have updated content (content hashing, last-modified headers, RSS feeds)
- **Cost optimization:** Embedding generation costs at scale (batch processing, incremental updates, cheaper models)
- **Anti-bot measures:** Handling CAPTCHAs, IP blocking, JavaScript challenges (rotating proxies, headless browser fingerprinting)
- **Content quality scoring:** How to assess scraped content quality and filter low-value pages (engagement signals, domain authority, content depth)
- **Multi-language support:** Handling non-English content (language detection, translation, multilingual embeddings)

### Recommended Follow-up Techniques
- **Five Whys:** Deep-dive on change detection: "Why do we need to detect changes?" → optimization directions
- **Assumption Reversal:** Challenge "websites are main content source" - what if we focused on structured data APIs instead?
- **Time Shifting:** "How would this architecture look in 2030 with more advanced AI?" (proactive future-proofing)

### Questions That Emerged
- How should we handle paywalled content? (Respect paywall vs. authenticated scraping with user credentials)
- What's the optimal chunk size for web content vs. books? (Web articles may have different structure/length characteristics)
- Should we build a web UI for managing scraped sources? (CRUD operations, re-scrape triggers, content preview)
- How do we handle dynamic single-page applications (SPAs) with client-side routing? (React/Vue apps that don't have distinct URLs per page)
- Should we expose scraping as an API endpoint? (`POST /api/v1/ingest/website` for programmatic access)
- How do we credit original sources in AI responses? (Citation formatting, attribution requirements)

### Next Session Planning
- **Suggested topics:**
  - PDF ingestion architecture (similar morphological analysis)
  - Scheduled scraping and change detection deep-dive
  - Multi-modal content extraction (images, tables, charts)
- **Recommended timeframe:** After v1 website scraping implementation complete (2-4 weeks)
- **Preparation needed:**
  - Deploy v1 website scraping to production
  - Gather user feedback on real-world usage
  - Analyze cost/performance metrics from production data
  - Identify top feature requests and pain points

---

*Session facilitated using the BMAD-METHOD™ brainstorming framework*
