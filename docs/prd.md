# Minerva Product Requirements Document (PRD)

**Project:** Minerva
**Version:** 1.0
**Created:** 2025-10-06
**Status:** Draft

---

## Goals and Background Context

### Goals

- Enable efficient knowledge extraction from Kindle books into structured, searchable database for MyPeptidePal.ai integration
- Reduce book extraction time from 4-6 hours (manual) to under 15 minutes (automated)
- Achieve 95%+ text extraction accuracy using AI vision models
- Create semantically searchable corpus of peptide research materials with vector embeddings
- Maintain API costs under $2.50 per 100-page book
- Enable source attribution and verification through screenshot references
- Support ethical, legal extraction that respects DRM without circumvention

### Background Context

Researchers reading books on Kindle Cloud Reader face a critical knowledge management problem: valuable research content remains locked within Amazon's ecosystem. Manual extraction methods are prohibitively slow (4-6 hours per book), and existing third-party tools often violate Amazon's Terms of Service by circumventing DRM. This creates knowledge silos that prevent researchers from integrating Kindle content into modern knowledge management systems like Obsidian or custom AI-powered research tools.

Minerva solves this by mimicking human reading behavior: it uses Playwright for browser automation to "read" each page visually through screenshots, then leverages OpenAI's GPT-5/GPT-5-mini Vision API to extract and structure text with 95%+ accuracy. Unlike simple OCR, the AI understands document structure, preserving headers, paragraphs, and semantic meaning. The extracted knowledge is chunked semantically with overlapping context, embedded using OpenAI's text-embedding-3-small, and stored in PostgreSQL with pgvector for semantic search. Minerva serves as the foundational data layer for MyPeptidePal.ai, enabling deep, context-aware queries across a corpus of peptide research books. The system operates in two environments: local ingestion (where Playwright + AI processing occurs) and production API (serving queries), with manual knowledge-only export ensuring book images never leave the local machine.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-06 | 1.0 | Initial PRD draft | John (PM Agent) |
| 2025-10-06 | 1.1 | Updated default vision model to gpt-4o-mini, added user workflows, expanded monitoring, added post-MVP criteria | John (PM Agent) |

---

## User Workflows

### Primary Workflow: Ingest New Book

1. **Start**: User has Kindle Cloud Reader URL for a book
2. User runs: `minerva ingest <kindle_url>`
3. System validates environment (API key, database connectivity)
4. **First-time only**: System opens browser, prompts for Amazon login
5. System captures all pages with progress feedback
6. System extracts text from screenshots using GPT vision
7. System chunks text semantically with overlap
8. System generates embeddings and stores in database
9. **Complete**: Book status = "completed", cost summary displayed

**Duration**: ~15 minutes for 100-page book

### Secondary Workflow: Re-embed Existing Book

1. **Start**: User wants to upgrade embedding model for existing book
2. User runs: `minerva re-embed --book-id <uuid> --embedding-model text-embedding-3-large`
3. System validates book exists and has text chunks
4. System generates new embeddings with selected model
5. System updates all chunks with new embeddings
6. **Complete**: Book uses new embedding model, old model archived

**Duration**: ~2-5 minutes for 200 chunks

### Export Workflow: Local → Production

1. **Start**: User wants to make book available to MyPeptidePal.ai
2. User runs: `minerva export --book-id <uuid>`
3. System validates book completed, generates export report
4. User confirms export
5. System generates SQL file (knowledge-only, no screenshots)
6. **Manual step**: User runs SQL file against production database
7. **Complete**: Book queryable via production API

### Query Workflow: MyPeptidePal.ai Integration

1. MyPeptidePal.ai sends POST request to `/api/v1/search/semantic`
2. API generates embedding for query text
3. pgvector finds semantically similar chunks
4. API returns ranked results with book attribution
5. MyPeptidePal.ai displays results to user with source citations

### Edge Case Workflows

**Session Expired During Ingestion:**
1. System detects authentication failure
2. System pauses with message: "Session expired, re-authentication required"
3. System opens browser for re-login
4. User logs in, presses Enter
5. System resumes from last captured page

**API Rate Limit Hit:**
1. OpenAI returns 429 error
2. System logs: "Rate limit hit, retrying in X seconds"
3. System waits with exponential backoff
4. System retries request (up to 3 attempts)
5. If all retries fail: System marks ingestion as "failed" with error message

**Ingestion Failure Mid-Book:**
1. Error occurs (network failure, API error, etc.)
2. System logs error details to ingestion_logs table
3. System updates book.ingestion_status = "failed"
4. System stores error message in book.ingestion_error field
5. User can retry ingestion (system resumes from last successful stage)

---

## Requirements

### Functional Requirements

**FR1:** The system shall authenticate with Amazon Kindle Cloud Reader through a one-time manual login via visible browser window and persist the session state locally for reuse across runs.

**FR2:** The system shall detect expired authentication sessions and prompt the user to re-authenticate when necessary.

**FR3:** The system shall programmatically navigate through Kindle Cloud Reader pages, capturing sequential high-quality screenshots (1920x1080 PNG) with unique identifiers.

**FR4:** The system shall automatically detect the end of a book during page navigation and screenshot capture.

**FR5:** The system shall extract text from screenshots using Tesseract OCR while preserving document structure including paragraphs, headers, and lists, with optional AI-powered formatting cleanup (configurable, disabled by default) to remove OCR artifacts.

**FR6:** The system shall break extracted text into semantic chunks at paragraph/section boundaries with configurable overlap (15% default) to preserve context continuity.

**FR7:** The system shall generate vector embeddings for all chunks using OpenAI's text-embedding-3-small model and store them in PostgreSQL with pgvector extension.

**FR8:** The system shall track which OCR method (tesseract version + optional AI formatting) and embedding model was used for each chunk to support re-extraction and re-embedding capabilities.

**FR9:** The system shall store books, screenshots, and chunks in a PostgreSQL database (database name configured via DATABASE_URL) with schema including: books table, screenshots table, chunks table, and embedding_configs table.

**FR10:** The system shall provide a RESTful API with endpoints for: semantic vector similarity search (POST /search/semantic), listing books (GET /books), retrieving book details (GET /books/{book_id}), and fetching chunk details with context (GET /chunks/{chunk_id}).

**FR11:** The system shall return search results ranked by similarity score with configurable filters for book IDs, similarity threshold, and top K results.

**FR12:** The system shall provide a command-line interface using Typer with commands for: initiating book ingestion, exporting to production database, and regenerating embeddings.

**FR13:** The system shall support manual export from local database to production database by generating SQL INSERT statements for books, chunks, and screenshot metadata (excluding screenshot file paths).

**FR14:** The system shall support re-embedding functionality allowing users to regenerate embeddings with different models for existing books.

### Non-Functional Requirements

**NFR1:** Text extraction accuracy shall meet or exceed 95% as measured by spot-checking random pages against source screenshots.

**NFR2:** The system shall process pages at approximately 2-3 seconds per page total processing time, completing a 100-page book in under 15 minutes end-to-end.

**NFR3:** API vector similarity search queries shall respond in under 200ms for typical searches.

**NFR4:** API costs shall remain under $2.00 per 100-page book for embeddings (Tesseract OCR is free), with optional AI formatting adding ~$0.01 if enabled (excluding optional metadata enrichment).

**NFR5:** The system shall achieve a 90%+ successful completion rate for full book ingestion without manual intervention.

**NFR6:** Amazon Kindle Cloud Reader credentials and session data shall never leave the local machine; only knowledge (text) shall be exported to production.

**NFR7:** The system shall not circumvent DRM and shall only capture content that is visually displayed to a human reader, respecting Amazon's Terms of Service for personal use.

**NFR8:** Screenshot storage shall be maintained locally with reasonable disk usage (under 500MB per 100-page book).

**NFR9:** The system shall support configurable model selection via environment variables to allow cost optimization and quality tuning without code changes.

**NFR10:** The production API deployment shall be lightweight, containing no browser automation dependencies or screenshot storage capabilities.

---

## Technical Assumptions

### Repository Structure: **Monorepo**

**Rationale:** Single repository containing all Minerva components (CLI, API, core ingestion logic, database models) simplifies development for a solo developer. The project is cohesive enough that splitting into multiple repos would add unnecessary overhead. The two-environment architecture (local ingestion vs. production API) is achieved through deployment configuration, not repository separation.

### Service Architecture

**Architecture Type:** Modular Monolith with Two-Environment Deployment

**Local Environment (Ingestion):**
- Full ingestion pipeline: Playwright browser automation + OpenAI Vision API + semantic chunking + embedding generation
- Local PostgreSQL database (database name configured via DATABASE_URL)
- Screenshot storage on local disk
- CLI interface (Typer)
- Optional local API instance for testing

**Production Environment (Query API):**
- FastAPI application serving read-only queries
- Production PostgreSQL database (database name configured via DATABASE_URL)
- Lightweight deployment (no Playwright, no screenshot storage, no heavy dependencies)
- RESTful endpoints only

**Communication:** Manual export process (local DB → SQL export → production DB import)

**Rationale:** This architecture keeps Amazon Kindle credentials and book screenshots on the local machine (security + legal), reduces production deployment complexity and cost, allows content review before publishing, and separates compute-intensive ingestion from lightweight query serving.

### Testing Requirements

**Testing Strategy:** Unit + Integration with Manual Validation

**Unit Testing:**
- Core modules: text extraction, semantic chunking, embedding generation, vector search
- Database operations (CRUD, async sessions)
- API endpoint logic
- Framework: pytest + pytest-asyncio

**Integration Testing:**
- End-to-end pipeline: screenshot capture → extraction → chunking → embedding → storage
- API integration: full request/response cycles with test database
- Database migrations and schema validation
- Export/import workflow validation

**Manual Testing & Validation:**
- Playwright automation reliability (UI changes detection)
- Text extraction quality (spot-checking random pages for 95% accuracy)
- Semantic search relevance (RAG query quality assessment)
- Cost tracking and budget validation

**No Automated E2E for Kindle:** Kindle Cloud Reader automation is fragile and subject to Amazon UI changes. Automated E2E tests would be brittle. Instead, rely on POC validation and periodic manual verification.

**Rationale:** Personal research tool with single user doesn't require extensive automated testing. Focus testing effort on core logic (chunking, embeddings, search) where bugs would corrupt the knowledge base. Accept manual validation for Playwright automation since it's inherently fragile and requires human oversight anyway.

### Additional Technical Assumptions and Requests

**Language & Framework:**
- **Python 3.11+**: Primary language for all components
- **FastAPI 0.104+**: Web framework for API layer (async, OpenAPI auto-documentation)
- **SQLModel 0.0.14+**: Unified ORM and API models (combines SQLAlchemy + Pydantic)

**Database:**
- **PostgreSQL 15+**: Primary database with pgvector extension for vector similarity search
- **asyncpg**: Async PostgreSQL driver
- **Alembic**: Database migrations

**Browser Automation:**
- **Playwright 1.40+**: Chromium browser automation for Kindle Cloud Reader

**AI/ML Services:**
- **Tesseract OCR 5.0+**: Local text extraction from screenshots (no API costs, no content restrictions)
- **OpenAI API (openai Python SDK v1.12+)**:
  - Embedding Model: **text-embedding-3-small** (1536 dimensions)
  - Optional Formatting: **gpt-4o-mini** for OCR cleanup (disabled by default)
  - Future metadata extraction: gpt-5-mini with JSON mode (Phase 1.5)

**Configuration Management:**
- **Pydantic Settings**: Environment-based configuration
- **python-dotenv**: .env file support
- All model selections, API keys, database URLs configurable via environment variables

**CLI:**
- **Typer**: Command-line interface framework

**Logging:**
- **structlog**: Structured logging for debugging and monitoring

**Dependency Management:**
- **Poetry**: Python package and dependency management

**Development Platform:**
- **macOS (Darwin 25.0.0)**: Primary development environment

**Production Deployment:**
- **Target Platform**: Linux server or containerized deployment (Docker)
- **Hosting Options**: Railway, Fly.io, or similar (lightweight API hosting)
- **Production Database**: Hosted PostgreSQL with pgvector (Supabase/Neon recommended)

**Performance Considerations:**
- Async/await throughout API and database operations for concurrent request handling
- pgvector ivfflat index for efficient similarity search at scale
- Configurable API rate limiting and exponential backoff for OpenAI calls
- Screenshot processing parallelization where possible (future optimization)

**Security & Compliance:**
- Environment variables for all secrets (no hardcoded credentials)
- PostgreSQL user with limited permissions for production API
- Local-only storage of Kindle credentials and screenshots
- Knowledge-only export (no screenshot redistribution)
- Personal use only (no commercial deployment)

**Future Flexibility:**
- Model configurability supports easy testing of new OpenAI models
- Re-embedding capability allows switching embedding models without re-ingestion
- Export mechanism can be automated in Phase 2
- Architecture supports adding metadata enrichment (Phase 1.5) without major refactoring

---

## Epic List

### Epic 1: Foundation & Automated Screenshot Capture
Establish project infrastructure (repository, database schema, configuration management, CLI framework) and deliver automated Kindle Cloud Reader authentication with programmatic screenshot capture of entire books.

### Epic 2: AI-Powered Knowledge Extraction & Vector Database
Extract text from screenshots using OpenAI vision models with structure preservation, implement semantic chunking with overlap, generate vector embeddings, and store searchable knowledge in PostgreSQL with pgvector.

### Epic 3: Query API & Production Export
Implement RESTful API with semantic search endpoints for MyPeptidePal.ai integration, create manual export mechanism to production database, and deploy production API.

---

## Epic 1: Foundation & Automated Screenshot Capture

**Expanded Goal:** Establish the complete technical foundation for Minerva including project repository, database schema, configuration management, and CLI framework. Deliver reliable, automated Kindle Cloud Reader authentication with programmatic screenshot capture that can process entire books from start to finish. After this epic, the system can capture high-quality screenshots of any Kindle book and store them with proper metadata, providing the raw material for subsequent knowledge extraction.

---

### Story 1.1: Project Initialization and Repository Structure

As a **developer**,
I want **a properly structured Python project with dependency management and development environment**,
so that **I have a solid foundation for building Minerva components**.

#### Acceptance Criteria

1. Poetry-based Python 3.11+ project initialized with pyproject.toml containing core dependencies (FastAPI, SQLModel, asyncpg, Playwright, openai, Pydantic Settings, python-dotenv, Typer, structlog, pytest)
2. Repository directory structure created following the architecture specified in technical assumptions (minerva/ with api/, core/, db/, cli/, utils/ subdirectories)
3. .gitignore configured to exclude screenshots/, .env, __pycache__, .pytest_cache, and other development artifacts
4. README.md created with project description, setup instructions, and basic usage
5. .env.example template created with placeholders for all required environment variables (OPENAI_API_KEY, VISION_MODEL, EMBEDDING_MODEL, DATABASE_URL, SCREENSHOTS_DIR)
6. Development environment validated: `poetry install` succeeds and `poetry run playwright install chromium` completes successfully
7. Basic project structure imports successfully in Python REPL without errors

---

### Story 1.2: Database Foundation with SQLModel and Migrations

As a **developer**,
I want **PostgreSQL database schema with SQLModel models and Alembic migrations**,
so that **I can store books, screenshots, chunks, and embeddings with proper relationships and types**.

#### Acceptance Criteria

1. SQLModel models created in db/models.py for all tables: Book, Screenshot, EmbeddingConfig, Chunk with proper field types, relationships, and constraints matching the schema from the project brief
2. Book model includes: id (UUID), title, author, kindle_url, total_screenshots, capture_date, ingestion_status, ingestion_error, metadata (JSONB), timestamps
3. Screenshot model includes: id (UUID), book_id (FK), sequence_number, file_path, screenshot_hash, captured_at with unique constraint on (book_id, sequence_number)
4. Chunk model includes: id (UUID), book_id (FK), screenshot_ids (UUID[]), chunk_sequence, chunk_text, chunk_token_count, embedding_config_id (FK), embedding (VECTOR), vision_model, metadata fields
5. EmbeddingConfig model includes: id (UUID), model_name, model_version, dimensions, is_active, created_at
6. Alembic initialized with initial migration script that creates all tables, pgvector extension, and indexes (idx_chunks_book_id, idx_chunks_embedding with ivfflat)
7. Database session management implemented in db/session.py with async engine and async session factory
8. Local PostgreSQL database (database name from DATABASE_URL) can be created and migrated successfully with `alembic upgrade head`
9. Basic CRUD operations work: can create/read Book and Screenshot records

---

### Story 1.3: Configuration Management with Pydantic Settings

As a **developer**,
I want **environment-based configuration using Pydantic Settings**,
so that **model selections, API keys, and database connections are configurable without code changes**.

#### Acceptance Criteria

1. Configuration class created in config.py using Pydantic Settings with fields for: openai_api_key, vision_model (default: "gpt-4o-mini"), vision_detail_level (default: "low"), embedding_model (default: "text-embedding-3-small"), embedding_dimensions (default: 1536), database_url, screenshots_dir
2. Configuration loads from environment variables with .env file support via python-dotenv
3. Configuration includes validation: required fields raise errors if missing, vision_model validates against allowed models, embedding_dimensions matches selected model
4. Application-wide configuration singleton accessible via `from minerva.config import settings`
5. Screenshots directory is created automatically if it doesn't exist when config is loaded
6. Configuration can be instantiated and accessed successfully in tests with overrides
7. Structured logging (structlog) configured with log level from environment (default: INFO)

---

### Story 1.4: Playwright POC - Kindle Authentication and Page Capture

As a **researcher**,
I want **automated Kindle Cloud Reader navigation with authentication**,
so that **I can programmatically access and capture book pages without manual intervention**.

#### Acceptance Criteria

1. Playwright automation module created in core/ingestion/kindle_automation.py with KindleAutomation class
2. Browser launches in headed mode (visible window) for initial authentication with configurable headless option
3. System navigates to provided Kindle URL and detects if authentication is required
4. When unauthenticated, system pauses with clear user prompt: "Please log in to Amazon in the browser window, then press Enter to continue"
5. After authentication, system waits for book reader to fully load (canvas element or book content visible)
6. System successfully captures a single high-quality screenshot (1920x1080 PNG) of the current page
7. System can programmatically turn to the next page using appropriate selectors/keyboard navigation
8. POC validates: navigate to book URL → authenticate → capture 10 consecutive pages → save screenshots to local disk with sequential naming
9. Error handling implemented for: network failures, authentication timeouts, page load failures
10. Basic human-like delays added between page turns (1-2 seconds randomized) to avoid detection

---

### Story 1.5: Session Persistence for Reusable Authentication

As a **researcher**,
I want **Kindle authentication sessions persisted locally**,
so that **I don't have to manually log in for every book ingestion**.

#### Acceptance Criteria

1. Browser context state (cookies, local storage, session data) saved to local file after successful authentication
2. Session state file stored in a secure location (e.g., ~/.minerva/session_state.json) with restricted permissions
3. On subsequent runs, system attempts to load saved session state before launching browser
4. System validates session by checking if book content loads without authentication prompt
5. If session expired or invalid, system detects authentication requirement and prompts user to log in again
6. After new authentication, session state is updated and saved
7. Session state path configurable via environment variable SESSION_STATE_PATH
8. Clear logging messages indicate: "Using saved session", "Session expired, re-authentication required", "New session saved"
9. Successfully demonstrates: authenticate once → ingest book A → close browser → ingest book B using saved session without re-authentication

---

### Story 1.6: Full Book Screenshot Capture with Progress Tracking

As a **researcher**,
I want **automated capture of all pages in a Kindle book with progress feedback**,
so that **I can process entire books unattended and monitor ingestion status**.

#### Acceptance Criteria

1. Screenshot capture method enhanced to detect end of book (last page indicators, navigation disabled, or duplicate screenshots)
2. Screenshot hashing (SHA256) implemented to detect duplicate pages and confirm book end
3. Progress display shows: current page number, estimated total pages (if detectable), capture rate (pages/second), elapsed time
4. Screenshots saved with book_id directory structure: screenshots/{book_id}/page_{sequence}.png
5. Screenshot metadata recorded in database: book_id, sequence_number, file_path, screenshot_hash, captured_at
6. Book record created/updated with: title (extracted from page or provided), kindle_url, total_screenshots, ingestion_status ("in_progress" during capture, "screenshots_complete" when done)
7. Graceful error recovery: if capture fails mid-book, system logs error, updates ingestion_status to "failed", and stores error message in ingestion_error field
8. System successfully captures a complete 100+ page book from start to finish without manual intervention
9. All screenshots verified: sequential numbering, no missing pages, readable text quality
10. Ingestion log entries created for key events: capture started, every 10 pages, capture completed, errors

---

### Story 1.7: CLI Framework with Ingest Command

As a **researcher**,
I want **a command-line interface for initiating book ingestion**,
so that **I can easily start processing books with a simple terminal command**.

#### Acceptance Criteria

1. Typer-based CLI application created in cli/app.py with application entry point
2. `minerva ingest <kindle_url>` command implemented that accepts Kindle Cloud Reader URL as required argument
3. Optional parameters supported: `--title`, `--author` for manual metadata entry
4. Command output includes: welcome message, configuration summary (vision model, database), progress updates during capture, completion summary (total pages, time elapsed, cost estimate)
5. Command handles errors gracefully: invalid URL format, database connection failures, Playwright errors, keyboard interruption (Ctrl+C)
6. On successful completion, command displays: book_id, total screenshots captured, screenshots directory path, next steps message
7. CLI installed as executable: `poetry install` makes `minerva` command available system-wide
8. Help text accessible via `minerva --help` and `minerva ingest --help` with clear descriptions
9. Command validates environment: checks for required config (OPENAI_API_KEY, DATABASE_URL), verifies database connectivity, ensures screenshots directory writable
10. End-to-end test: `minerva ingest <url>` successfully ingests a full book and displays appropriate output

---

## Epic 2: AI-Powered Knowledge Extraction & Vector Database

**Expanded Goal:** Transform captured screenshots into searchable, structured knowledge by extracting text using OpenAI vision models with structure preservation, implementing semantic chunking with configurable overlap to maintain context continuity, generating vector embeddings for semantic search, and storing all knowledge in PostgreSQL with pgvector. After this epic, the complete ingestion pipeline processes screenshots into a searchable vector database, enabling semantic queries across book content with proper source attribution and support for model upgrades through re-embedding.

---

### Story 2.1: Tesseract OCR Integration for Text Extraction

As a **developer**,
I want **integration with OpenAI Vision API to extract text from screenshots**,
so that **I can convert book page images into structured text while preserving document formatting**.

#### Acceptance Criteria

1. Text extraction module created in core/ingestion/text_extraction.py with TextExtractor class
2. OpenAI client initialized using openai Python SDK v1.12+ with API key from configuration
3. Vision model selection uses configured VISION_MODEL (default: gpt-4o-mini) with fallback logic
4. Screenshot sent to vision API with prompt: "Extract all text from this book page. Preserve structure including paragraphs, headers, lists, and formatting. Return only the extracted text."
5. API call uses configured detail level (default: "low") to optimize cost
6. Response includes extracted text with structure markers (e.g., markdown formatting for headers, lists)
7. Error handling for: API rate limits (429), network failures, invalid responses, token limits
8. Exponential backoff implemented for rate limit errors with configurable max retries (default: 3)
9. Token usage tracked and logged for cost monitoring
10. Vision model used is recorded with extracted text for traceability
11. Successfully extracts text from 5 test screenshots with visual validation of accuracy
12. Extraction preserves: paragraph breaks, numbered/bulleted lists, headers/subheaders, basic formatting

---

### Story 2.2: Semantic Chunking with Configurable Overlap

As a **developer**,
I want **semantic text chunking with overlap between chunks**,
so that **knowledge is broken into optimal sizes for vector search while preserving context across chunk boundaries**.

#### Acceptance Criteria

1. Semantic chunking module created in core/ingestion/semantic_chunking.py with SemanticChunker class
2. Chunking strategy breaks text at natural boundaries: paragraph breaks, section breaks, or semantic separators (avoid mid-sentence splits)
3. Chunk size target configurable via environment (default: ~500-800 tokens per chunk)
4. Overlap percentage configurable (default: 15%) - each chunk includes last N% of previous chunk text
5. Token counting implemented using tiktoken library to accurately measure chunk sizes
6. Each chunk records: chunk_text, chunk_sequence (order in book), source screenshot_ids (array of screenshot UUIDs this chunk spans)
7. Chunking handles edge cases: very short text (single chunk), very long paragraphs (split intelligently), empty screenshots (skip)
8. Chunk metadata includes: start/end character positions in source text, token count
9. Successfully chunks a full book's extracted text (e.g., 100 pages → ~200 chunks) with validated overlap
10. Manual inspection confirms: no context loss at boundaries, overlap preserves continuity, chunks are semantically coherent
11. All chunks reference correct source screenshots (single screenshot for most chunks, multiple for overlapping chunks)

---

### Story 2.3: Vector Embedding Generation with OpenAI

As a **developer**,
I want **vector embedding generation for all text chunks**,
so that **I can perform semantic similarity search across the knowledge base**.

#### Acceptance Criteria

1. Embedding generation module created in core/ingestion/embedding_generator.py with EmbeddingGenerator class
2. OpenAI embeddings API integration using configured EMBEDDING_MODEL (default: "text-embedding-3-small")
3. Batch embedding generation supported: processes multiple chunks in single API call (up to OpenAI's batch limit)
4. Each chunk's text sent to embeddings API, returns 1536-dimensional vector
5. Embedding config record created/retrieved in embedding_configs table with model name, version, dimensions, is_active=true
6. Generated embedding stored in chunks.embedding field (pgvector VECTOR type)
7. Chunk record updated with embedding_config_id reference to track which model generated the embedding
8. Error handling for: API failures, rate limits, network issues with retry logic
9. Cost tracking: log total tokens processed and estimated cost
10. Successfully generates embeddings for all chunks in a test book (e.g., 200 chunks)
11. Embeddings verified: correct dimensions (1536), non-zero values, stored successfully in database
12. Query test: manual vector similarity query returns semantically related chunks

---

### Story 2.4: Complete End-to-End Ingestion Pipeline

As a **researcher**,
I want **a complete pipeline that processes books from screenshots to searchable vector database**,
so that **I can ingest entire books into the knowledge base with a single command**.

#### Acceptance Criteria

1. Ingestion orchestrator created in core/ingestion/pipeline.py that coordinates: screenshot capture → text extraction → chunking → embedding generation → database storage
2. Pipeline processes book in stages with status updates: "Capturing screenshots" → "Extracting text" → "Chunking text" → "Generating embeddings" → "Complete"
3. Book.ingestion_status updated at each stage: "in_progress", "screenshots_complete", "text_extracted", "chunks_created", "embeddings_generated", "completed"
4. Progress tracking displays: current stage, items processed (e.g., "Extracting text: 45/100 pages"), time elapsed, estimated time remaining
5. All data persisted transactionally: if embedding generation fails, previously created chunks are rolled back or marked incomplete
6. Screenshot→Text→Chunk lineage maintained: each chunk links to source screenshots, vision model recorded
7. Cost summary displayed at completion: total API costs (vision + embeddings), cost per page, total tokens used
8. Quality metrics logged: total pages, total chunks, average chunk size, embedding generation success rate
9. Error recovery: pipeline can resume from last successful stage if interrupted (e.g., text extraction complete, embeddings failed → resume at embedding generation)
10. Successfully processes complete test book (100+ pages) end-to-end: screenshots → searchable chunks in database
11. Database validates: all chunks have embeddings, all screenshots referenced, book status = "completed"
12. `minerva ingest` command updated to execute full pipeline (not just screenshot capture)

---

### Story 2.5: Re-embedding Capability for Model Upgrades

As a **researcher**,
I want **the ability to regenerate embeddings with different models**,
so that **I can upgrade to better embedding models without re-ingesting books**.

#### Acceptance Criteria

1. Re-embedding module created in core/ingestion/embedding_generator.py with re_embed_book method
2. New CLI command `minerva re-embed --book-id <uuid>` accepts book UUID and optional --embedding-model parameter
3. Command validates: book exists, has chunks with text, new embedding model differs from current
4. New embedding config created in embedding_configs table with new model details, is_active=true
5. Previous embedding config set to is_active=false (archived but preserved for history)
6. All chunks for the specified book regenerated with new embeddings using new model
7. Chunk records updated: new embedding vector, new embedding_config_id reference
8. Progress tracking shows: "Re-embedding book: [title]", "Processing chunk 50/200", cost estimates
9. Transactional safety: if re-embedding fails partway, old embeddings remain until new process completes successfully
10. Successfully re-embeds test book from text-embedding-3-small to text-embedding-3-large (or vice versa)
11. Database validates: all chunks reference new embedding_config_id, embedding dimensions match new model
12. Vector search works correctly with new embeddings (test query returns relevant results)
13. Optional --all flag supported to re-embed all books in database

---

### Story 2.6: Text Extraction Quality Validation and Testing

As a **researcher**,
I want **automated and manual validation of text extraction quality**,
so that **I can verify the system meets 95%+ accuracy targets**.

#### Acceptance Criteria

1. Quality validation utilities created in utils/quality_validation.py
2. Spot-checking script randomly selects N screenshots (default: 10) from ingested book
3. For each selected screenshot, script displays: original screenshot image, extracted text side-by-side
4. Manual validation prompt: "Rate accuracy (1-10): ", "Note any major errors: "
5. Validation results logged with: screenshot_id, accuracy_rating, notes, timestamp
6. Aggregate quality report generated: average accuracy score, confidence level (based on sample size), error patterns
7. If average accuracy <9.5 (equivalent to 95%), script flags for review and suggests: try different vision model, adjust prompts, review edge cases
8. Test suite (pytest) includes integration test: ingest sample book → validate chunks exist → spot-check 3 random extractions programmatically
9. Sample "golden" test cases created: 5 screenshots with pre-verified correct text for automated regression testing
10. Successfully validates 3 diverse books (different layouts, fonts, formatting) with 95%+ accuracy
11. Error pattern analysis identifies common failures (if any): tables, images, footnotes, special formatting
12. Documentation updated with known limitations and workarounds

---

## Epic 3: Query API & Production Export

**Expanded Goal:** Implement a production-ready RESTful API with FastAPI that serves semantic search queries for MyPeptidePal.ai integration, providing vector similarity search with filtering, book and chunk retrieval endpoints, and proper error handling. Create a robust manual export mechanism that generates SQL scripts to transfer knowledge from local database to production database (knowledge-only, excluding screenshots). Deploy lightweight production API to hosting platform. After this epic, MyPeptidePal.ai can query the Minerva knowledge base via API, and ingested books can be safely exported to production for broader access.

---

### Story 3.1: FastAPI Foundation with Health Check and Documentation

As a **developer**,
I want **FastAPI application skeleton with automatic API documentation**,
so that **I have a solid foundation for building query endpoints with interactive docs**.

#### Acceptance Criteria

1. FastAPI application created in main.py with app initialization and basic configuration
2. CORS middleware configured to allow requests from MyPeptidePal.ai domain (configurable via environment)
3. Database dependency created in api/dependencies.py that provides async database sessions to route handlers
4. Health check endpoint implemented: GET /health returns {"status": "healthy", "database": "connected", "version": "1.0.0"}
5. Health check validates database connectivity and returns appropriate error if database unreachable
6. OpenAPI documentation auto-generated and accessible at /docs (Swagger UI) and /redoc (ReDoc)
7. API versioning implemented: all endpoints under /api/v1 prefix
8. Structured logging integrated with request/response logging middleware
9. Global error handlers implemented for: database errors, validation errors, unhandled exceptions (return proper HTTP status codes)
10. Application startup/shutdown events configured: create database connection pool on startup, close on shutdown
11. Successfully runs locally: `uvicorn minerva.main:app --reload` starts server on localhost:8000
12. /docs endpoint displays interactive API documentation with all registered endpoints

---

### Story 3.2: Vector Similarity Search Implementation

As a **developer**,
I want **vector similarity search logic using pgvector**,
so that **I can find semantically relevant chunks based on query embeddings**.

#### Acceptance Criteria

1. Vector search module created in core/search/vector_search.py with VectorSearch class
2. Search method accepts: query_text, top_k (default: 10), similarity_threshold (default: 0.7), optional filters (book_ids, date_range)
3. Query text converted to embedding using same embedding model as chunks (text-embedding-3-small)
4. SQL query uses pgvector cosine similarity operator (<->) to find nearest neighbor chunks
5. Results filtered by similarity threshold: only chunks with similarity >= threshold returned
6. Optional book_ids filter: if provided, only search within specified books
7. Results ordered by similarity score (descending) and limited to top_k
8. Each result includes: chunk_id, chunk_text, similarity_score, book metadata (id, title, author), screenshot_ids, chunk_sequence
9. Context window support: optionally fetch previous and next chunks for expanded context
10. Query metadata tracked: embedding model used, processing time, total results before/after filtering
11. Successfully executes test query: "BPC-157 for gut health" returns relevant chunks from test database
12. Performance validated: search completes in <200ms for database with 1000+ chunks

---

### Story 3.3: Semantic Search API Endpoint

As a **MyPeptidePal.ai developer**,
I want **a POST /search/semantic endpoint to query the knowledge base**,
so that **I can retrieve relevant information based on user questions**.

#### Acceptance Criteria

1. Search endpoint created in api/routes/search.py: POST /api/v1/search/semantic
2. Request schema (Pydantic model) includes: query (required string), top_k (optional int, default 10), similarity_threshold (optional float, default 0.7), filters (optional object with book_ids, date_range)
3. Response schema includes: results array (chunk_id, chunk_text, similarity_score, book object, screenshot_ids, context_window), query_metadata (embedding_model, processing_time_ms)
4. Endpoint validates input: query not empty, top_k between 1-100, similarity_threshold between 0-1
5. Error responses include: 400 for invalid input, 500 for server errors, 503 for database unavailable
6. Endpoint calls VectorSearch service to execute search
7. Response includes proper HTTP headers: Content-Type application/json, CORS headers
8. Successfully handles concurrent requests: 10 simultaneous queries complete without errors
9. OpenAPI docs updated with example request/response
10. Integration test validates: POST request with valid query → 200 response → results contain expected chunks
11. Edge cases handled: empty results (returns empty array, not error), very long queries (truncated or error), missing embeddings (graceful error)

---

### Story 3.4: Book and Chunk Retrieval Endpoints

As a **MyPeptidePal.ai developer**,
I want **endpoints to list books and retrieve specific book/chunk details**,
so that **I can browse the knowledge base and provide source attribution**.

#### Acceptance Criteria

1. Books list endpoint created: GET /api/v1/books with optional query parameters: limit (default 20), offset (default 0), status (filter by ingestion_status)
2. Books list response includes: books array (id, title, author, total_screenshots, total_chunks, capture_date, ingestion_status), total count, has_more boolean
3. Book details endpoint created: GET /api/v1/books/{book_id} returns full book details including metadata
4. Book details response includes: all book fields, chunk count, screenshot count, ingestion logs (recent errors/warnings)
5. Chunk details endpoint created: GET /api/v1/chunks/{chunk_id} returns chunk with context
6. Chunk details response includes: chunk_id, chunk_text, chunk_sequence, chunk_token_count, book object, screenshot_ids, vision_model, context object (previous_chunk text, next_chunk text)
7. Context retrieval: previous/next chunks fetched based on chunk_sequence for same book
8. All endpoints handle not found: 404 response with clear error message if book_id or chunk_id doesn't exist
9. Books endpoint supports pagination: offset/limit correctly slice results, total count accurate
10. OpenAPI docs include all three endpoints with schemas and examples
11. Integration tests validate: list books → retrieve specific book → retrieve chunk from that book (full workflow)

---

### Story 3.5: Export Script for Production Database

As a **researcher**,
I want **a script to export ingested books to production database**,
so that **I can make curated knowledge available to MyPeptidePal.ai without exposing local screenshots**.

#### Acceptance Criteria

1. Export script created: `minerva export --book-id <uuid>` command in CLI
2. Script validates: book exists, ingestion_status = "completed", embeddings present on all chunks
3. Pre-export report generated: book title, total chunks, total screenshots, estimated export size, warnings (if any)
4. User confirmation prompt: "Export [book title] to production? (y/n)" with summary displayed
5. SQL export file generated with: INSERT statements for book record (excluding local paths), all chunk records (including embeddings), screenshot metadata (id, sequence, hash ONLY - no file_path), embedding config record
6. Export file includes transaction wrapper: BEGIN; ... COMMIT; for atomic import
7. Export validates embedding config exists in production (or includes CREATE statement)
8. Screenshots explicitly excluded: file_path field set to NULL in exported data, clear comment in SQL file
9. Export file saved to: exports/{book_id}_{timestamp}.sql with proper formatting
10. Success message displays: export file path, import instructions ("Run this SQL against production DB")
11. Successfully exports test book: SQL file generated → import to test production DB → chunks queryable → embeddings intact
12. Optional --all flag exports all completed books in batch
13. Export script is idempotent: re-exporting same book generates valid SQL without duplicates (uses INSERT ... ON CONFLICT)

---

### Story 3.6: Production Database Setup and Import Validation

As a **developer**,
I want **production database schema and validated import process**,
so that **exported knowledge can be safely imported to production environment**.

#### Acceptance Criteria

1. Production database setup script created: alembic migration applicable to production DB
2. Production schema identical to local schema except: screenshots.file_path nullable (always NULL in production), appropriate indexes created
3. Import validation script created: validates SQL export file before import (syntax check, required tables exist, no file paths included)
4. Import instructions documented in README: connection to production DB, running export SQL, verification queries
5. Test production database created (database name configured via DATABASE_URL) on local machine for validation
6. Successfully imports exported SQL to test production DB: all books, chunks, embeddings present
7. Post-import validation queries: count chunks, verify embeddings non-null, check book status
8. Production DB performance validated: vector search queries <200ms with realistic data volume (1000+ chunks)
9. Rollback procedure documented: how to safely remove imported book if issues discovered
10. Security validated: production DB user has limited permissions (INSERT, SELECT only - no DELETE or ALTER)
11. Connection string for production DB configurable via PRODUCTION_DATABASE_URL environment variable

---

### Story 3.7: API Deployment and Production Testing

As a **researcher**,
I want **Minerva API deployed to production hosting**,
so that **MyPeptidePal.ai can access the knowledge base from anywhere**.

#### Acceptance Criteria

1. Deployment configuration created for Railway/Fly.io/similar platform with Dockerfile or buildpack config
2. Dockerfile creates lightweight production image: includes only API dependencies (no Playwright, no screenshot libs)
3. Environment variables configured in hosting platform: DATABASE_URL (production), OPENAI_API_KEY, ALLOWED_ORIGINS (CORS)
4. Health check endpoint used by platform for deployment verification and monitoring
5. Production deployment successful: API accessible at public URL (e.g., https://minerva-api.railway.app)
6. SSL/TLS enabled: API served over HTTPS
7. Production health check passes: GET /health returns 200 with database connected
8. Production search query validated: POST /search/semantic with test query returns results from production DB
9. API rate limiting configured (optional for MVP): basic protection against abuse
10. Monitoring configured: deployment platform tracks uptime, response times, error rates
11. Structured logging configured: all logs output to stdout in JSON format for platform log aggregation (Railway/Fly.io native logging)
12. Error alerting configured: critical errors logged with ERROR level for visibility in platform dashboards
13. Cost monitoring enabled: OpenAI API usage tracked via OpenAI dashboard, production hosting costs monitored via platform billing
14. Successfully handles request from external client (e.g., curl, Postman, MyPeptidePal.ai test)
15. Documentation updated with production API base URL, authentication requirements (if any), and monitoring/logging approach
16. Cost tracking validated: production hosting costs within budget (<$20/month for MVP)

---

### Story 3.8: End-to-End MVP Validation

As a **researcher**,
I want **complete end-to-end validation of the MVP system**,
so that **I can confirm all success criteria are met before considering Epic 3 complete**.

#### Acceptance Criteria

1. Full workflow test: ingest complete book (100+ pages) → export to production → query via production API
2. Text extraction accuracy validated: spot-check 10 random pages, confirm 95%+ accuracy
3. Processing time validated: 100-page book ingests in <15 minutes end-to-end
4. API performance validated: semantic search queries return in <200ms average over 10 test queries
5. Cost tracking validated: calculate total API costs for test book, confirm <$2.50 per 100 pages
6. Re-embedding validated: successfully re-embed test book with different model, search still works
7. Export/import validated: exported book imports to production without errors, data integrity confirmed
8. Production API validated: MyPeptidePal.ai can successfully query production API and retrieve relevant results
9. Error handling validated: test failure scenarios (expired session, API rate limit, database down) → appropriate errors logged/displayed
10. Documentation complete: README with setup instructions, API documentation, troubleshooting guide
11. All MVP success criteria from project brief verified and documented
12. Known limitations documented: edge cases, unsupported features, future improvements
13. Celebration: MVP is complete and functional! 🎉

---

## Post-MVP Decision Criteria

### When to Implement Phase 1.5 (Metadata Enrichment)

**Trigger Criteria - Implement if ALL are met:**
1. ✅ MVP validation complete: 3+ books ingested with 95%+ accuracy
2. ✅ Cost tracking confirms sustainability: actual costs ≤ $2.50 per 100-page book
3. ✅ MyPeptidePal.ai successfully querying production API with satisfactory results
4. ✅ User (you) actively using Minerva for research and finding value
5. ✅ Budget allows for increased costs: Phase 1.5 adds ~$2-6 per book for metadata extraction

**Phase 1.5 Features (Metadata Enrichment):**
- GPT-5-mini structured extraction for: peptide names, dosages, study references, administration routes, benefits/side effects
- Enhanced search filters: query by peptide name, dosage range, etc.
- Aggregated insights: "typical dosages across all books"

**Defer Phase 1.5 if:**
- ❌ Costs exceeding budget with baseline features
- ❌ Accuracy issues need resolution first
- ❌ Low usage/value from MVP
- ❌ Time constraints (focus on MyPeptidePal.ai instead)

### When to Implement Phase 2 (Admin Dashboard + Advanced Features)

**Trigger Criteria - Implement if ANY are met:**
1. 📚 Knowledge base grows: 10+ books ingested, difficult to manage via CLI
2. 🔍 Need for visual debugging: want to see screenshot gallery, inspect chunks visually
3. 📊 Analytics desired: cost tracking dashboard, ingestion success rates, quality trends
4. 👥 Multi-user consideration: want to share Minerva with collaborators
5. 🎨 UI preference: prefer graphical interface over CLI

**Phase 2 Features:**
- React + Shadcn UI admin dashboard
- Visual book library with screenshot gallery
- Real-time ingestion progress with WebSocket updates
- Chunk explorer with inline editing
- Cost tracking and usage analytics
- Resume from checkpoint (error recovery)
- Edge case handling (two-page spreads, images, footnotes, TOC extraction)

**Defer Phase 2 if:**
- ✅ CLI workflow is sufficient
- ✅ Book volume remains low (<10 books)
- ✅ Time better spent on MyPeptidePal.ai features
- ✅ Solo user with no sharing needs

### Success Metrics Review Cadence

**Weekly Check-in (First Month):**
- How many books processed this week?
- Did costs stay within budget?
- Any ingestion failures? What caused them?
- Is search quality meeting research needs?

**Monthly Review (Ongoing):**
- Total books in knowledge base
- Average cost per book (trend over time)
- Accuracy spot-checks maintaining 95%+?
- Value assessment: Is Minerva improving research workflow?
- Decision: Continue with MVP, add Phase 1.5, or build Phase 2?

### Pivot/Abandon Criteria

**Consider pausing or abandoning Minerva if:**
- 🚫 Playwright automation unreliable (>50% failure rate after mitigations)
- 🚫 Costs consistently exceed $5 per book despite optimization
- 🚫 Accuracy drops below 85% and cannot be improved
- 🚫 Amazon changes ToS or actively blocks automation
- 🚫 Not using the tool (no books ingested in 2+ months)
- 🚫 MyPeptidePal.ai not benefiting from Minerva data

**Alternatives if abandoned:**
- Manual extraction for critical books only
- Commercial services (if they emerge)
- Focus MyPeptidePal.ai on other data sources (research papers, forums)

---

## Checklist Results Report

### Executive Summary

**Overall PRD Completeness:** 90% (after updates)

**MVP Scope Appropriateness:** Just Right

**Readiness for Architecture Phase:** ✅ READY

**Assessment:** The Minerva PRD is comprehensive, well-structured, and ready for architectural design. All HIGH priority recommendations from the PM checklist have been addressed.

### Category Validation Results

| Category                         | Status  | Critical Issues |
| -------------------------------- | ------- | --------------- |
| 1. Problem Definition & Context  | PASS    | None - well articulated |
| 2. MVP Scope Definition          | PASS    | Clear MVP boundaries, good rationale |
| 3. User Experience Requirements  | PASS    | User workflows now documented |
| 4. Functional Requirements       | PASS    | Comprehensive, testable requirements |
| 5. Non-Functional Requirements   | PASS    | Specific metrics, clear constraints |
| 6. Epic & Story Structure        | PASS    | Excellent sequencing and sizing |
| 7. Technical Guidance            | PASS    | Detailed stack, rationale provided |
| 8. Cross-Functional Requirements | PASS    | Monitoring requirements expanded |
| 9. Clarity & Communication       | PASS    | Clear language, good structure |

### Updates Applied

**✅ Completed Improvements:**
1. Updated default vision model from gpt-5-nano to **gpt-4o-mini** (verified OpenAI model availability)
2. Added **User Workflows** section documenting primary, secondary, export, and edge case workflows
3. Expanded **Story 3.7 monitoring requirements** with structured logging, error alerting, and cost monitoring
4. Added **Post-MVP Decision Criteria** section with Phase 1.5 and Phase 2 trigger conditions

**📊 Final Assessment:**
- **21 user stories** across 3 epics (appropriate for 6-8 week MVP)
- **14 functional requirements** + **10 non-functional requirements**
- **Clear technical stack** with rationale
- **Excellent epic sequencing** with incremental value delivery
- **Comprehensive acceptance criteria** (average 10-12 per story)

### Strengths

- ✅ **Clear Problem-Solution Fit:** Well-articulated pain point with quantified impact (4-6 hours → 15 minutes)
- ✅ **Appropriate MVP Scope:** Truly minimal while remaining viable - no bloat
- ✅ **Excellent Story Sizing:** 2-6 hour stories, perfect for AI agent execution
- ✅ **Strong Technical Foundation:** Two-environment architecture addresses security, legal, and cost concerns
- ✅ **Measurable Success Criteria:** 95% accuracy, <15 min, <$2.50/book, <200ms API response
- ✅ **Risk Awareness:** Playwright reliability, GPT quality, cost management identified upfront
- ✅ **Future-Proofing:** Configurable models, re-embedding, export automation pathway

### Next Steps

**Ready for handoff to:**
1. **Architect** - Design technical implementation, create architecture diagrams, define development workflow
2. **UX Expert** (optional for Phase 2 only) - Admin dashboard UI/UX design when Phase 2 triggers

---

## Next Steps

### UX Expert Prompt

*Note: UX expertise not required for MVP (CLI-only tool). Defer to Phase 2 when Admin Dashboard is needed.*

**When Phase 2 is triggered, use this prompt:**

> I have a completed Minerva MVP (CLI-based knowledge extraction tool for Kindle books). We're ready to build Phase 2: Admin Dashboard.
>
> Please review `/Users/clizaola/Code/kindlescraper/docs/prd.md` and `/Users/clizaola/Code/kindlescraper/docs/brief.md` to understand the system.
>
> Design a React + Shadcn UI admin dashboard that provides:
> - Visual book library management
> - Real-time ingestion progress monitoring (WebSocket)
> - Screenshot gallery viewer
> - Chunk explorer with inline editing
> - Cost tracking and analytics dashboard
> - One-click re-embedding with model comparison
>
> Create wireframes, component specs, and UX flow documentation.

### Architect Prompt

The Minerva PRD is complete and ready for technical implementation. Please proceed with architectural design.

**Review these documents:**
- Primary: `/Users/clizaola/Code/kindlescraper/docs/prd.md` (Product Requirements Document)
- Context: `/Users/clizaola/Code/kindlescraper/docs/brief.md` (Project Brief with detailed background)

**Your mission:**
Design the technical architecture for Minerva, a Python-based knowledge extraction pipeline that processes Kindle books into a searchable vector database for MyPeptidePal.ai integration.

**Key architectural decisions to address:**
1. **Database Schema Details:** Finalize SQLModel definitions, pgvector index configuration (ivfflat parameters), migration strategy
2. **Two-Environment Architecture:** Local ingestion environment vs. lightweight production API deployment
3. **Ingestion Pipeline:** Orchestration of screenshot capture → GPT vision extraction → semantic chunking → embedding generation
4. **Error Recovery:** Checkpoint/resume mechanism, retry policies, rollback procedures
5. **Async Patterns:** FastAPI async request handling, database session management, concurrent API calls
6. **Cost Optimization:** Batch API usage, parallel processing, rate limit handling
7. **Development Workflow:** Git branching, code quality tools (black, mypy, ruff), testing strategy

**Deliverables:**
1. Architecture diagrams (system architecture, data flow, database schema)
2. Detailed technical design document
3. Module breakdown with interfaces
4. Development environment setup guide
5. Risk mitigation strategies for identified technical risks

**Critical constraints:**
- Python 3.11+, FastAPI, SQLModel, PostgreSQL+pgvector, Playwright, OpenAI API
- Personal use only (single user, no multi-user complexity)
- Budget-conscious (optimize for <$2.50 per 100-page book)
- 6-8 week MVP timeline (part-time development)

**Start by reviewing the PRD, then create the architecture document. Ask clarifying questions if any requirements are ambiguous.**

---
