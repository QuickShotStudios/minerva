# Minerva Project Brief

**Project Name:** Minerva
**Type:** Peptide Research Knowledge Extraction System
**Target User:** Personal research tool (single user)
**Integration:** Backend data layer for MyPeptidePal.ai
**Database:** PostgreSQL + pgvector (configurable via DATABASE_URL)
**Created:** 2025-10-06
**Status:** Planning Phase → MVP Development

---

## Executive Summary

**Minerva** is an automated Python-based knowledge extraction pipeline that captures and converts Kindle Cloud Reader books into a searchable, structured database for peptide research. The system uses Playwright for browser automation, OpenAI's GPT-5/GPT-5-mini Vision API for intelligent text extraction, and PostgreSQL with pgvector for vector-based semantic search.

Unlike traditional e-book converters, Minerva solves the problem of extracting knowledge from DRM-protected Kindle books for legitimate personal research use. It addresses the pain point where manual extraction would take 4-6 hours per book, reducing this to under 15 minutes with 95%+ accuracy while respecting copyright through visual-only capture.

**Key Value Propositions:**
- **Fully Ethical & Legal**: Only captures what's visually displayed, respecting DRM without circumvention
- **High Accuracy**: 95%+ text extraction accuracy using AI vision understanding, not simple OCR
- **Cost-Effective**: $0.30-2.50 per 100-page book depending on model selection
- **Domain-Intelligent**: Optimized for peptide research with optional metadata extraction
- **RAG-Ready**: Semantic chunking with vector embeddings for MyPeptidePal.ai integration
- **Knowledge-Only Export**: Extracts and structures knowledge without redistributing book images

**Architecture:**
- **Local**: Full ingestion pipeline (Playwright + GPT-5 + chunking + embeddings)
- **Production**: API-only deployment serving queries to MyPeptidePal.ai
- **Export**: Manual knowledge-only export (no screenshots in production)

---

## Problem Statement

### Current State

Users who read books on Kindle Cloud Reader have limited options for extracting content for legitimate personal use. Whether for academic research, note-taking, or creating study materials, the current state forces users to:

- **Manually copy-paste text** (extremely time-consuming for full books)
- **Take individual screenshots and manually transcribe** (inefficient and error-prone)
- **Accept that content remains locked** within Amazon's ecosystem
- **Work around restrictive DRM** that prevents text selection in many books

### Impact of the Problem

- **Time Loss**: Manually extracting a 100-page book can take 4-6 hours
- **Research Inefficiency**: Researchers can't integrate Kindle content into their knowledge management systems (Obsidian, Notion, Roam)
- **Knowledge Silos**: Valuable research insights remain trapped in Amazon's walled garden
- **Accessibility Barriers**: Users can't convert content to their preferred accessible formats

### Why Existing Solutions Fall Short

- **Manual methods** are prohibitively slow
- **Third-party tools** often violate Amazon ToS by circumventing DRM
- **Official Kindle features** provide only basic highlights/notes, not full-text extraction
- **OCR tools** require manual screenshot management and lack context understanding

### Urgency and Importance

The shift to digital reading is accelerating, yet tools for personal knowledge management (PKM) are fragmented from reading platforms. Users increasingly need to integrate reading with their thinking tools. With AI-powered text extraction now cost-effective, this problem can be solved ethically without DRM circumvention, making now the ideal time to build this solution.

---

## Proposed Solution

### Core Concept

**Minerva** is an automated Python tool that bridges the gap between Kindle Cloud Reader and modern knowledge management systems. Instead of attempting to circumvent DRM (which is illegal and violates ToS), Minerva mimics what a human reader does: it "reads" each page visually through screenshots and uses AI vision models to extract and structure the text.

### The Approach

1. **Automated Browser Control**: Uses Playwright to navigate Kindle Cloud Reader, managing authentication sessions and page-turning automatically
2. **Visual Page Capture**: Takes high-quality screenshots of each page as it would appear to a human reader
3. **AI-Powered Text Extraction**: Leverages OpenAI's GPT-5/GPT-5-mini Vision API to "read" screenshots and extract text with structure awareness (headers, paragraphs, formatting)
4. **Semantic Chunking**: Breaks extracted text into overlapping semantic chunks optimized for RAG (Retrieval Augmented Generation)
5. **Vector Embeddings**: Generates embeddings using OpenAI's text-embedding-3-small for semantic search
6. **Structured Database Storage**: Stores everything in PostgreSQL with pgvector for efficient similarity search
7. **Knowledge-Only Export**: Exports structured knowledge to production database without book images

### Key Differentiators

- **Fully Ethical & Legal**: Only captures what's visually displayed, respecting DRM without circumvention
- **Context-Aware Extraction**: GPT-5 understands document structure, not just raw OCR - it distinguishes headers from body text, preserves lists, and maintains semantic meaning
- **Cost-Effective**: $0.30-2.50 per 100-page book using configurable model selection
- **High Accuracy**: Targets 95%+ extraction accuracy by leveraging AI understanding
- **RAG-Optimized**: Semantic chunking with overlapping context for high-quality retrieval
- **Domain-Intelligent**: Optional metadata extraction for peptide names, dosages, studies
- **Flexible Architecture**: Configurable models, re-embedding capability, local processing with production API
- **Privacy-First**: Screenshots stay local, only knowledge exported to production

### Why This Succeeds Where Others Haven't

- **Timing**: AI vision models have only recently become affordable and accurate enough
- **Legal Position**: Unlike DRM-breaking tools, this operates in a legally defensible space for personal use
- **User Experience**: Fully automated workflow vs. manual screenshot + OCR approaches
- **Structure Preservation**: AI understanding maintains document hierarchy that simple OCR loses
- **Cost Structure**: GPT-5 pricing makes premium extraction accessible ($1.25/1M input tokens)

### High-Level Vision

Minerva enables seamless integration between Amazon's reading ecosystem and modern knowledge management practices, specifically optimized for peptide research. It serves as the foundational data layer for MyPeptidePal.ai, providing deep, structured, semantically searchable knowledge extracted from research books.

---

## Target Users & Use Case

### Primary User
- **You** (solo researcher)
- Personal research tool, not commercial product

### Primary Use Case
- **Peptide research**: Building domain-specific knowledge base
- All books will be about peptides
- Integration with MyPeptidePal.ai chat interface

### User Needs
- Efficient knowledge extraction from Kindle books
- Searchable, structured corpus of research materials
- Semantic search capabilities for research queries
- Source attribution for verification

---

## Goals & Success Metrics

### Personal Research Objectives

- **Enable Efficient Knowledge Extraction**: Convert Kindle books into structured database for integration with MyPeptidePal.ai
- **Time Savings**: Reduce book extraction time from 4-6 hours (manual) to under 15 minutes (automated)
- **Preserve Reading Investments**: Maintain personal library of research materials in accessible, searchable format
- **Support Deep Research**: Create semantically searchable corpus of peptide research materials

### Success Metrics

**Quality Metrics:**
- Text Accuracy: **95%+** extraction accuracy (measured by spot-checking random pages)
- Structure Preservation: Correctly identifies and formats headers, lists, quotes, paragraphs
- Completeness: Successfully processes start-to-finish without missing pages
- Semantic Quality: Chunks preserve context and enable relevant RAG queries

**Performance Metrics:**
- Processing Speed: ~2-3 seconds per page total processing time
- End-to-End Time: Complete 100-page book in **<15 minutes**
- API Response Time: **<200ms** for vector similarity queries
- Reliability: 90%+ successful completion rate

**Cost Efficiency:**
- API Costs: **<$2.50 per 100-page book** (vision + embeddings)
- Storage: Manageable local storage (<500MB per book including screenshots)
- Monthly Budget: **<$125/month** total operating costs

**Usability:**
- Setup Complexity: One-time authentication setup in <5 minutes
- Ease of Use: Single command execution to process entire book
- Recovery: Ability to re-extract or re-embed if needed

### Key Performance Indicators (KPIs)

- **Books Processed Monthly**: Track usage to validate tool value
- **Cost per Book**: Monitor API costs to ensure budget sustainability
- **Error Rate**: Percentage of books requiring manual intervention
- **Extraction Quality Score**: Subjective 1-10 rating of output quality
- **Query Relevance**: MyPeptidePal.ai query quality assessment

---

## MVP Scope

### Core Features (Must Have)

**1. Amazon Authentication & Session Persistence**
- One-time manual login via visible browser window
- Session state saved locally for reuse across runs
- Detects expired sessions and prompts for re-authentication

**2. Automated Page Navigation & Screenshot Capture**
- Programmatic page-turning with sequential screenshot capture (1920x1080 PNG)
- Screenshots saved with unique IDs and preserved for reference
- Progress display during capture
- Auto-detection of book end

**3. AI-Powered Text Extraction**
- Configurable vision model (gpt-5, gpt-5-mini, gpt-4o-mini)
- GPT Vision API extracts text from screenshots
- Preserves structure (paragraphs, headers, lists)
- Low-detail mode for cost efficiency
- Tracks which model extracted each chunk

**4. Semantic Chunking with Overlap**
- Extracted text broken into semantic chunks (by paragraph/section boundaries)
- Configurable overlap between chunks (15% default) to preserve context continuity
- Each chunk references its source screenshot ID(s)
- Token counting for optimization

**5. Vector Embeddings Generation**
- Uses OpenAI text-embedding-3-small to generate embeddings
- Embedding model configuration stored in DB
- Re-embedding capability (can switch models later)

**6. PostgreSQL Database Storage**

**Database Configuration:** All database operations use the `DATABASE_URL` environment variable from your `.env` file. This allows easy switching between development, testing, and production databases.

**Schema:**
- `books` table: title, author, kindle_url, capture_date, metadata
- `screenshots` table: book_id, sequence_number, file_path (local only), screenshot_hash
- `chunks` table: book_id, screenshot_id(s), chunk_text, chunk_sequence, embedding vector (pgvector), metadata
- `embedding_configs` table: tracks embedding model version for re-embedding
- Optional metadata fields: extracted_peptides, extracted_dosages, extracted_studies

**7. Query API Endpoints**

RESTful API for MyPeptidePal.ai:
- **POST /search/semantic**: Vector similarity search with filters
- **GET /books**: List all books
- **GET /books/{book_id}**: Book details
- **GET /chunks/{chunk_id}**: Chunk details with context
- Returns ranked results with similarity scores

**8. Command-Line Interface**

Simple CLI using Typer:
- `minerva ingest <kindle_url>`: Initiate book ingestion
- `minerva export --book-id <uuid>`: Export to production SQL
- `minerva re-embed --book-id <uuid>`: Regenerate embeddings
- Progress display and logging

**9. Export Mechanism**

- Manual export: Local DB → Production DB
- Generates SQL INSERT statements
- Exports books + chunks + screenshot metadata (no file paths)
- Knowledge-only (no screenshots exported)
- Validation before export

### Out of Scope for MVP

- ❌ Image/Diagram Extraction (deferred to Phase 2)
- ❌ Footnote/Endnote Processing (advanced reference handling)
- ❌ Table of Contents Extraction
- ❌ Resume from Checkpoint (recovery from interruptions)
- ❌ Batch Processing (multiple books in sequence)
- ❌ Image Optimization (screenshot compression)
- ❌ GraphQL API (REST only for MVP)
- ❌ User Authentication (local/single user for MVP)
- ❌ Web UI for Minerva (CLI only; MyPeptidePal.ai provides UI)
- ❌ Metadata Enrichment (peptide extraction - Phase 1.5)

### MVP Success Criteria

The MVP is successful when:

- ✅ A complete peptide research book (100 pages) ingests end-to-end into the database
- ✅ Text extraction accuracy meets **95%** target
- ✅ Semantic chunks preserve context and reference correct screenshots
- ✅ Vector embeddings are generated and stored successfully
- ✅ API query returns relevant chunks when searching "BPC-157"
- ✅ Re-embedding functionality works (can switch embedding models)
- ✅ Total processing time under **15 minutes** for 100-page book
- ✅ API costs under **$2.50 per 100-page book**
- ✅ Export script successfully exports to production DB

---

## Database Schema Design

### Database Schema

**Note:** Database name is configurable via `DATABASE_URL` in your `.env` file. The following schema applies regardless of the database name you choose.

```sql
-- Books table
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255),
    kindle_url TEXT NOT NULL,
    total_screenshots INTEGER,
    capture_date TIMESTAMP DEFAULT NOW(),
    ingestion_status VARCHAR(50), -- 'in_progress', 'completed', 'failed'
    ingestion_error TEXT,
    metadata JSONB, -- flexible storage for ISBN, publication year, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Screenshots table (source of truth)
CREATE TABLE screenshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL, -- 1, 2, 3...
    file_path TEXT, -- local path to PNG (local only, not exported to production)
    screenshot_hash VARCHAR(64), -- SHA256 for deduplication
    captured_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(book_id, sequence_number)
);

-- Embedding configurations (for re-embedding capability)
CREATE TABLE embedding_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL, -- 'text-embedding-3-small'
    model_version VARCHAR(50),
    dimensions INTEGER, -- 1536 for text-embedding-3-small
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chunks table (with pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    screenshot_ids UUID[] NOT NULL, -- array of screenshot IDs this chunk spans
    chunk_sequence INTEGER NOT NULL, -- order within book
    chunk_text TEXT NOT NULL,
    chunk_token_count INTEGER, -- for tracking/optimization
    embedding_config_id UUID REFERENCES embedding_configs(id),
    embedding VECTOR(1536), -- pgvector type for text-embedding-3-small
    vision_model VARCHAR(50), -- track which model extracted this chunk
    metadata_model VARCHAR(50), -- track metadata extraction model

    -- Metadata enrichment fields (Phase 1.5)
    extracted_peptides TEXT[], -- ['BPC-157', 'TB-500', 'GHK-Cu']
    extracted_dosages TEXT[], -- ['250mcg', '5mg', '500mg']
    extracted_studies TEXT[], -- study references or DOIs
    contains_peptide_data BOOLEAN DEFAULT FALSE,
    extraction_confidence JSONB, -- {'peptides': 0.95, 'dosages': 0.87}

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chunks_book_id ON chunks(book_id);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops);

-- Ingestion logs (for debugging)
CREATE TABLE ingestion_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    log_level VARCHAR(20), -- 'INFO', 'WARNING', 'ERROR'
    message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints Specification

### Base URL
`http://localhost:8000/api/v1` (local)
`https://minerva-api.example.com/api/v1` (production)

### Core Query Endpoints (for MyPeptidePal.ai)

**1. Vector Similarity Search**

```http
POST /search/semantic
Content-Type: application/json

{
  "query": "What are the benefits of BPC-157 for gut health?",
  "top_k": 10,
  "similarity_threshold": 0.7,
  "filters": {
    "book_ids": ["uuid1", "uuid2"],  // optional
    "peptide_names": ["BPC-157"],    // optional (Phase 1.5)
    "date_range": {                   // optional
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "chunk_text": "BPC-157 has shown...",
      "similarity_score": 0.92,
      "book": {
        "id": "uuid",
        "title": "Peptide Protocols",
        "author": "Dr. Smith"
      },
      "screenshot_ids": ["screenshot_uuid1", "screenshot_uuid2"],
      "context_window": "...previous chunk... [CURRENT CHUNK] ...next chunk..."
    }
  ],
  "query_metadata": {
    "embedding_model": "text-embedding-3-small",
    "processing_time_ms": 145
  }
}
```

**2. List Books**

```http
GET /books?limit=20&offset=0&status=completed
```

**Response:**
```json
{
  "books": [
    {
      "id": "uuid",
      "title": "Peptide Protocols",
      "author": "Dr. Smith",
      "total_screenshots": 250,
      "total_chunks": 487,
      "capture_date": "2024-01-15T10:30:00Z",
      "ingestion_status": "completed"
    }
  ],
  "total": 5,
  "has_more": false
}
```

**3. Get Book Details**

```http
GET /books/{book_id}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Peptide Protocols",
  "author": "Dr. Smith",
  "total_screenshots": 250,
  "total_chunks": 487,
  "capture_date": "2024-01-15T10:30:00Z",
  "ingestion_status": "completed",
  "metadata": {
    "isbn": "978-1234567890",
    "publication_year": 2023
  }
}
```

**4. Get Chunk with Context**

```http
GET /chunks/{chunk_id}
```

**Response:**
```json
{
  "chunk_id": "uuid",
  "chunk_text": "BPC-157 has demonstrated...",
  "chunk_sequence": 42,
  "book": {
    "id": "uuid",
    "title": "Peptide Protocols",
    "author": "Dr. Smith"
  },
  "screenshot_ids": ["uuid1", "uuid2"],
  "context": {
    "previous_chunk": "...",
    "next_chunk": "..."
  }
}
```

### Admin/Management Endpoints

**5. Trigger Book Ingestion** (Local only)

```http
POST /ingest/book
Content-Type: application/json

{
  "kindle_url": "https://read.amazon.com/...",
  "metadata": {
    "title": "Advanced Peptide Research",
    "author": "Dr. Johnson"
  }
}
```

**6. Re-Embed Chunks** (Local only)

```http
POST /embeddings/regenerate
Content-Type: application/json

{
  "embedding_model": "text-embedding-3-large",
  "book_ids": ["uuid1", "uuid2"]  // optional, all books if omitted
}
```

---

## Metadata Enrichment (Phase 1.5)

### Vision: Domain-Intelligent Extraction

Instead of just storing raw text, Minerva can automatically identify and extract:
- **Peptide Names**: BPC-157, TB-500, GHK-Cu, Thymosin Beta-4
- **Dosages**: 250mcg, 5mg twice daily, 500mg/week
- **Study References**: "Smith et al. 2020", DOIs, clinical trial numbers
- **Administration Routes**: subcutaneous, oral, topical
- **Benefits/Effects**: wound healing, anti-inflammatory, gut repair
- **Side Effects**: nausea, headache, injection site reactions

### Implementation: GPT-5-mini Structured Extraction

During chunking, send chunk text through GPT-5-mini with structured output (JSON mode):

**Cost Impact:**
- Additional ~$0.01-0.03 per chunk
- For 100-page book with ~200 chunks: +$2-6
- Trade-off: Higher initial ingestion cost, but massive value for research queries

**MVP Recommendation:** Start without metadata extraction, add as Phase 1.5 after validating core pipeline.

### Query Power Unlocked

With metadata enrichment, MyPeptidePal.ai can answer:

**Query:** "What's the typical dosage of BPC-157 for gut health?"

**Without Enrichment:**
- Vector search returns 10 chunks mentioning "BPC-157" and "gut"
- User must read through all chunks to find dosages

**With Enrichment:**
- Filter: `peptide = 'BPC-157' AND contains_dosages = true AND benefits CONTAINS 'gut'`
- Return only relevant dosages with context
- Aggregate: "Typical dosages range from 250mcg-500mcg twice daily (mentioned in 12 chunks across 3 books)"

---

## Post-MVP Vision

### Phase 2 Features (Weeks 9-12)

**1. Admin Dashboard (React + Shadcn UI)**
- Visual book library management interface
- Real-time ingestion progress monitoring with WebSocket updates
- Screenshot gallery viewer with navigation
- Chunk explorer with inline editing capabilities
- Cost tracking and usage analytics dashboard
- One-click re-embedding with model comparison

**2. Advanced Metadata Enrichment**
- GPT-5-mini structured extraction for peptides, dosages, studies
- Peptide catalog with canonical names and alias normalization
- Benefit/side effect categorization
- Administration route extraction (subcutaneous, oral, topical, etc.)
- Stacking protocol detection ("BPC-157 + TB-500 for injury recovery")
- Confidence scoring for all extracted metadata

**3. Resume from Checkpoint**
- State persistence during ingestion (page-level checkpoints)
- Automatic recovery from failures with resume capability
- Partial re-ingestion for failed chunks only
- Progress restoration across restarts

**4. Edge Case Handling**
- Two-page spread detection and handling
- Image/diagram extraction
- Footnote/endnote processing
- Table of Contents extraction

### Long-term Vision (6-12 months)

**Minerva as Peptide Research Intelligence Platform:**

The ultimate vision is for Minerva to become the foundational data layer for comprehensive peptide research, powering MyPeptidePal.ai with deep, structured knowledge.

**Key Capabilities:**
- **Multi-Source Ingestion**: Beyond Kindle - PDFs, research papers, clinical trial databases
- **Knowledge Graph**: Relationships between peptides, studies, researchers, outcomes
- **Automated Literature Review**: Track new publications, auto-ingest relevant papers
- **Cross-Reference Intelligence**: "This study contradicts findings from Smith et al. 2020"
- **Temporal Analysis**: Track evolving research consensus over time
- **Dosage Recommendation Engine**: Aggregate safety data across sources

**Expansion Opportunities:**
1. Multi-format support (PDF, ePub, web scraping)
2. Specialized extraction pipelines (clinical trials, research papers, forums)
3. Collaborative research features (multi-user, shared knowledge base)
4. Local LLM option (privacy-focused alternative)
5. Advanced analytics (peptide safety dashboard, dosage analysis)

---

## Technical Considerations

### Platform Requirements

**Target Platforms:**
- **Primary Development**: macOS (Darwin 25.0.0)
- **Deployment Target**: Linux server or containerized (Docker)
- **Database**: PostgreSQL 15+ with pgvector extension

**Browser Requirements:**
- Chromium-based browser (managed by Playwright)
- Headless mode for production, headed mode for initial authentication

**Performance Requirements:**
- API response time: <200ms for vector similarity queries
- Ingestion throughput: 2-3 seconds per page
- Concurrent API requests: Support 10+ simultaneous queries

### Technology Stack

**Backend Framework & Language:**
- **Python 3.11+**: Primary development language
- **FastAPI**: Web framework and API layer (async, OpenAPI docs)
- Version: 0.104+

**Database Layer:**
- **PostgreSQL 15+**: Primary database
- **pgvector Extension**: Vector similarity search
- **SQLModel**: ORM and data validation (unified DB + API models)
- **asyncpg**: Async PostgreSQL driver
- Version: SQLModel 0.0.14+

**Browser Automation:**
- **Playwright**: Web automation and screenshot capture
- Browser: Chromium
- Version: 1.40+

**AI/ML Services:**
- **OpenAI API**: Text extraction and embeddings
  - Vision Model: gpt-5, gpt-5-mini, or gpt-4o-mini (configurable)
  - Embedding Model: text-embedding-3-small (1536 dimensions)
  - Metadata Extraction: gpt-5-mini with structured output (JSON mode)
  - SDK: openai Python package v1.12+

**Additional Core Libraries:**
- **Pydantic Settings**: Environment configuration management
- **python-dotenv**: .env file support
- **Typer**: Command-line interface
- **structlog**: Structured logging
- **Pillow**: Image processing (future optimization)

**Testing & Quality:**
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **httpx**: Async HTTP client for API testing

### Architecture

**Two-Environment Setup:**

**LOCAL (Development/Ingestion Machine):**
- Full Minerva ingestion pipeline
- Playwright + GPT-5 + chunking + embeddings
- Local PostgreSQL (database name configured via DATABASE_URL)
- Screenshot storage on local disk
- CLI for book ingestion
- Optional: Local API instance for testing

**PRODUCTION (Deployed API):**
- API only - No ingestion capabilities
- FastAPI serving queries
- Production PostgreSQL (database name configured via DATABASE_URL)
- Read-only operations (search, retrieval)
- Lightweight deployment (no Playwright, no heavy deps)

**Export Process:**
- Manual export: Local DB → Production DB
- Review/curate content locally before publishing
- Knowledge-only export (no screenshots)
- SQL INSERT statements for import

**Benefits:**
- ✅ Security: Kindle credentials never leave local machine
- ✅ Cost: Heavy processing on local machine, not cloud compute
- ✅ Control: Review content before making available
- ✅ Simplicity: Production deployment is lightweight
- ✅ Privacy: Book images never leave local machine
- ✅ Legal: No redistribution of book images

### Repository Structure

```
minerva/
├── .env.example              # Environment template
├── pyproject.toml           # Dependencies (Poetry)
├── alembic/                 # Database migrations
│   └── versions/
├── minerva/
│   ├── __init__.py
│   ├── config.py            # Pydantic Settings
│   ├── main.py              # FastAPI app entry point
│   │
│   ├── api/                 # FastAPI routes
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── search.py
│   │   │   ├── books.py
│   │   │   ├── ingest.py
│   │   │   └── embeddings.py
│   │   ├── dependencies.py  # DB session, auth
│   │   └── schemas.py       # API-only Pydantic models
│   │
│   ├── core/                # Business logic
│   │   ├── ingestion/
│   │   │   ├── kindle_automation.py
│   │   │   ├── text_extraction.py
│   │   │   ├── semantic_chunking.py
│   │   │   ├── embedding_generator.py
│   │   │   └── metadata_extractor.py
│   │   └── search/
│   │       └── vector_search.py
│   │
│   ├── db/                  # Database layer
│   │   ├── models.py        # SQLModel definitions
│   │   ├── session.py       # Async session management
│   │   └── migrations/      # Schema SQL files
│   │
│   ├── cli/                 # Command-line interface
│   │   └── app.py           # Typer CLI app
│   │
│   └── utils/
│       ├── logging.py
│       └── exceptions.py
│
├── screenshots/             # Screenshot storage (gitignored)
│   └── {book_id}/
│       └── page_*.png
│
├── tests/
│   ├── test_api/
│   ├── test_core/
│   └── fixtures/
│
└── docs/
    └── brief.md             # This document!
```

### Model Configuration

**Environment-Based Configuration (.env):**

```bash
# OpenAI Models (easily swappable)
OPENAI_API_KEY=sk-...

# Vision model for screenshot text extraction
VISION_MODEL=gpt-5-mini  # or gpt-5, gpt-4o-mini
VISION_DETAIL_LEVEL=low    # low, high, auto

# Embedding model for vector generation
EMBEDDING_MODEL=text-embedding-3-small  # or text-embedding-3-large
EMBEDDING_DIMENSIONS=1536

# Metadata extraction model
METADATA_MODEL=gpt-5-mini
METADATA_USE_JSON_MODE=true

# Database (change this to switch between dev/test/prod databases)
DATABASE_URL=postgresql+asyncpg://localhost/minerva_dev

# Paths
SCREENSHOTS_DIR=./screenshots
```

**Benefits:**
- ✅ Future-proof: Easy to adopt new models
- ✅ Cost control: Can downgrade if budget tight
- ✅ Quality optimization: Can upgrade for important books
- ✅ A/B testing: Compare model quality empirically
- ✅ Per-task optimization: Different models for different tasks

### Data Flow Architecture

```
1. CLI/API Trigger
   ↓
2. Kindle Automation (Playwright)
   → Screenshots saved to disk
   ↓
3. Text Extraction (GPT-5/GPT-5-mini)
   → Raw text per screenshot
   ↓
4. Semantic Chunking
   → Text split into overlapping chunks
   ↓
5. Parallel Processing:
   ├─→ Embedding Generation (OpenAI)
   └─→ Metadata Extraction (GPT-5-mini) [Phase 1.5]
   ↓
6. Database Storage (PostgreSQL)
   → Chunks + Vectors + Metadata
   ↓
7. Export (Manual)
   → SQL INSERT statements
   ↓
8. Production Import
   → MyPeptidePal.ai can query
```

### Security & Compliance

**API Security (MVP):**
- No authentication required (runs locally)
- Future: API key authentication for production

**Data Security:**
- Secrets management: Environment variables via .env
- Database credentials: PostgreSQL user with limited permissions
- OpenAI API key: Restricted permissions

**Compliance:**
- Amazon ToS: Only captures visual content (no DRM circumvention)
- OpenAI ToS: Personal research use compliant
- Data Privacy: All data stored locally, no third-party sharing
- Copyright: Knowledge-only export (no book images redistributed)

**Legal Considerations:**
- Tool designed for personal use only
- No redistribution of extracted content
- No commercial use
- Respects copyright through visual-only capture method

---

## Constraints & Assumptions

### Constraints

**Budget:**

**OpenAI API Costs (Standard Tier - Updated with Real Pricing):**

*Vision Models (per 1M tokens):*
- **gpt-5**: $1.25 input / $10.00 output (cached: $0.125 input)
- **gpt-5-mini**: $0.25 input / $2.00 output (cached: $0.025 input)
- **gpt-4o-mini**: $0.15 input / $0.60 output (cached: $0.075 input)

*Embedding Models (per 1M tokens):*
- **text-embedding-3-small**: $0.02 standard / $0.01 batch
- **text-embedding-3-large**: $0.13 standard / $0.065 batch

*Cost-Saving Options:*
- **Batch API**: 50% cheaper (gpt-5: $0.625 input / $5.00 output)
- **Prompt Caching**: 90% discount on cached input tokens

**Per Book Cost (100-page book, ~200 chunks):**

| Scenario | Vision Model | Cost | Use Case |
|----------|--------------|------|----------|
| **Premium** | gpt-5 (standard) | $1.50-2.50 | High-value research books |
| **Balanced** | gpt-5-mini (standard) | $0.30-0.50 | Default for most books |
| **Budget** | gpt-4o-mini (standard) | $0.20-0.35 | Testing or simple layouts |
| **Batch (overnight)** | gpt-5 (batch) | $0.75-1.25 | Non-urgent processing |

*Additional costs per book:*
- Embeddings: ~$0.02-0.03
- Metadata extraction (Phase 1.5): ~$1.00-2.00

**Total per book:**
- Without metadata: $0.25-2.50
- With metadata: $1.50-4.50

**Monthly Operating Costs (10-20 books/month):**
- API costs (without metadata): $5-50/month
- API costs (with metadata): $30-90/month
- Infrastructure (Supabase/Neon + Railway/Fly.io): $15-35/month
- **Total: $20-125/month**

**Key Insight:** GPT-5 pricing is **cheaper than estimated**, making premium extraction very affordable!

**Timeline:**
- MVP Development: **6-8 weeks** (part-time)
  - Week 1-2: Foundation & POC
  - Week 3-4: Text extraction & processing
  - Week 5-6: API & export
  - Week 7-8: Testing & deployment
- Phase 2: 3-4 weeks post-MVP
- No hard deadline (personal project)

**Resources:**
- Developer: Solo developer (you)
- Time Commitment: Part-time (10-15 hours/week)
- Local storage: 500GB+ recommended
- Production: Hosted services

**Technical Constraints:**
- Amazon Kindle Cloud Reader dependency (no API, subject to UI changes)
- OpenAI API rate limits (500 RPM, 200k TPM for Tier 1)
- pgvector performance (adequate for <1000 books, ~200k vectors)
- Two-environment architecture (local ingestion, manual export)
- Legal/ethical constraints (personal use only, no DRM circumvention)

### Key Assumptions

**Technical Assumptions:**
- Playwright can reliably automate Kindle Cloud Reader
- GPT-5/GPT-5-mini achieves 95% accuracy on peptide books
- Semantic chunking preserves context with 15% overlap
- PostgreSQL + pgvector performs adequately at expected scale
- OpenAI pricing remains stable
- Model selection is configurable and testable

**User/Usage Assumptions:**
- Single user (you), no concurrent jobs
- Books are text-based peptide research
- Average book: 100-300 pages
- Ingestion frequency: 2-5 books/week
- Query volume: <1000/day initially
- Manual export workflow acceptable

**Product Assumptions:**
- Knowledge extraction sufficient without screenshots
- MyPeptidePal.ai can use vector search effectively
- Source attribution provides adequate provenance
- Local screenshot storage adequate for verification
- Export/import workflow acceptable for MVP

**Business Assumptions:**
- Personal research tool (not commercial)
- Domain-specific for peptide research
- Cost per book ($0.25-4.50) is acceptable
- Future expansion possible but not required

**Critical Assumptions to Validate Early:**
1. Playwright automation reliability (Week 1)
2. GPT-5-mini extraction quality (Week 1)
3. OpenAI costs vs budget (first 5 books)
4. Chunking strategy effectiveness (first book)

**Assumptions That Can Change:**
- Model selection (configurable via .env)
- Metadata enrichment (can skip if too expensive)
- Embedding model (can switch)
- Production hosting (start with free tiers)
- Export automation (can build tooling later)

---

## Risks & Open Questions

### Technical Risks (Prioritized)

**HIGH PRIORITY:**

**1. Playwright Automation Reliability**
- **Risk**: Amazon blocks automation or changes UI
- **Impact**: Complete system failure
- **Likelihood**: Medium
- **Mitigation**: Stealth mode, human-like timing, fallback to manual mode
- **Validate**: Week 1 POC

**2. GPT-5-mini Extraction Quality**
- **Risk**: Doesn't achieve 95% accuracy
- **Impact**: Poor quality knowledge base
- **Likelihood**: Low-Medium
- **Mitigation**: Configurable models, A/B testing, re-extraction capability
- **Validate**: Week 1 POC, test on 5 books

**3. Semantic Chunking Effectiveness**
- **Risk**: Chunking breaks context, poor RAG quality
- **Impact**: Irrelevant MyPeptidePal.ai answers
- **Likelihood**: Medium
- **Mitigation**: 15% overlap, iterative testing, adjust based on feedback
- **Validate**: First book, MyPeptidePal.ai integration

**MEDIUM PRIORITY:**

**4. OpenAI API Rate Limits**
- **Risk**: Hit rate limits during ingestion
- **Impact**: Slow ingestion, failed calls
- **Mitigation**: Exponential backoff, Batch API, delays between calls

**5. Database Export/Import Process**
- **Risk**: Manual export error-prone
- **Impact**: Delay in production availability
- **Mitigation**: Robust validation, Phase 2 automation

**6. Amazon Terms of Service**
- **Risk**: Automated access violates ToS
- **Impact**: Account blocked, legal issues
- **Likelihood**: Low-Medium
- **Mitigation**: Personal use only, visual capture only, no DRM circumvention, knowledge-only export

### Open Questions

**CRITICAL (Need Answers Before MVP):**

1. **Chunk Overlap**: What percentage? → Recommend: 15%
2. **Screenshot Retention**: Permanent or temporary? → Recommend: Permanent
3. **Metadata Extraction**: MVP or Phase 1.5? → Recommend: Phase 1.5
4. **Export Workflow**: Manual or automated? → Recommend: Manual for MVP
5. **Default Vision Model**: gpt-5, gpt-5-mini, gpt-4o-mini? → Recommend: gpt-5-mini

**IMPORTANT (Answer During MVP):**

6. Chunk size strategy: Paragraph-based or token-based?
7. Embedding model: text-embedding-3-small or 3-large?
8. Batch API usage: All books or only non-urgent?
9. Production hosting: Supabase, Neon, or Railway?

**Risk Thresholds:**

**When to Pivot:**
- ❌ Playwright blocked → Manual screenshot mode
- ❌ GPT-5-mini accuracy <85% → Explore alternatives
- ❌ Costs exceed $200/month → Switch models
- ❌ Timeline extends beyond 12 weeks → Reduce scope

**When to Accelerate:**
- ✅ GPT-5-mini >95% accuracy → Make it default
- ✅ First 5 books flawless → Accelerate to Phase 2
- ✅ Costs under $50/month → Consider upgrading to gpt-5

---

## Next Steps & Implementation Plan

### MVP Implementation Roadmap (6-8 Weeks)

**Phase 1: Foundation & Proof of Concept (Weeks 1-2)**

**Week 1: Core Infrastructure Setup**
- [ ] Set up development environment (Python 3.11+, Poetry, PostgreSQL + pgvector)
- [ ] Initialize project structure
- [ ] Database foundation (SQLModel models, Alembic, initial schema)
- [ ] **CRITICAL POC**: Playwright + Kindle automation (capture 10 pages reliably)
- [ ] **CRITICAL POC**: GPT-5-mini vision extraction (test on 3 pages, measure accuracy)

**Week 2: Configuration & Basic Pipeline**
- [ ] Configuration management (Pydantic Settings, .env)
- [ ] Screenshot capture module (complete automation, session persistence)
- [ ] Basic database operations (CRUD, async sessions)
- [ ] CLI skeleton (Typer)

**Milestone 1:** Can capture full book screenshots via CLI

---

**Phase 2: Text Extraction & Processing (Weeks 3-4)**

**Week 3: Vision Extraction & Chunking**
- [ ] Text extraction module (OpenAI integration, error handling)
- [ ] Semantic chunking implementation (15% overlap)
- [ ] Basic ingestion workflow (end-to-end test on 1 book)
- [ ] Quality validation (spot-check accuracy)

**Week 4: Embeddings & Vector Storage**
- [ ] Embedding generation (text-embedding-3-small)
- [ ] Vector database setup (pgvector, ivfflat index)
- [ ] Re-embedding functionality
- [ ] Complete pipeline test (ingest 2-3 books)

**Milestone 2:** 3 books ingested with 95%+ accuracy

---

**Phase 3: API & Export (Weeks 5-6)**

**Week 5: FastAPI Implementation**
- [ ] API foundation (FastAPI app, SQLModel integration)
- [ ] Core query endpoints (/search/semantic, /books, /chunks)
- [ ] Vector search implementation
- [ ] API testing (validate search quality)

**Week 6: Export Mechanism & Production Prep**
- [ ] Export script implementation (generate SQL)
- [ ] Production database schema
- [ ] Export/import testing
- [ ] Documentation (README, API docs, procedures)

**Milestone 3:** API serving queries, export working, production DB ready

---

**Phase 4: Testing, Polish & Deployment (Weeks 7-8)**

**Week 7: Testing & Quality Assurance**
- [ ] Unit tests (pytest + pytest-asyncio)
- [ ] Integration tests (full pipeline, API endpoints)
- [ ] Quality validation (ingest 5-10 diverse books)
- [ ] Performance optimization

**Week 8: Deployment & Documentation**
- [ ] Production API deployment (Railway/Fly.io)
- [ ] Monitoring setup (logging, health checks, cost tracking)
- [ ] Final documentation
- [ ] MVP validation (all success criteria)

**Milestone 4 (MVP COMPLETE):** Production API deployed, 10+ books ingested, MyPeptidePal.ai integrated

---

### Immediate Next Actions (Start Today)

**1. Environment Setup (30 minutes)**
```bash
mkdir minerva && cd minerva
poetry init
poetry add fastapi sqlmodel asyncpg playwright openai pydantic-settings
poetry run playwright install chromium
brew install postgresql@15 pgvector
createdb minerva_dev  # Or any database name you prefer
```

**2. Create .env File (5 minutes)**
```bash
OPENAI_API_KEY=sk-...
VISION_MODEL=gpt-5-mini
EMBEDDING_MODEL=text-embedding-3-small
DATABASE_URL=postgresql+asyncpg://localhost/minerva_dev
SCREENSHOTS_DIR=./screenshots
```

**3. Critical POC - Playwright (1 hour)**
Test Kindle automation: navigate, login, capture 10 pages

**4. Critical POC - GPT-5-mini Vision (30 minutes)**
Test extraction on 3 sample pages, measure accuracy

---

### Post-MVP Roadmap

**Phase 2 (Weeks 9-12):** Admin Dashboard + Metadata Enrichment + Checkpoint Recovery

**Phase 3 (Months 4-6):** Edge cases + Batch processing + Performance optimization

**Long-term (6-12 months):** Multi-source ingestion + Knowledge graph + Collaborative features

---

### Weekly Check-in Questions

Every Friday:
1. Did I hit this week's milestones?
2. Are costs tracking to budget?
3. Is quality meeting expectations?
4. Am I still motivated?
5. What's the #1 priority for next week?

---

### Resources

**Documentation:**
- Playwright: https://playwright.dev/python/
- FastAPI: https://fastapi.tiangolo.com/
- SQLModel: https://sqlmodel.tiangolo.com/
- pgvector: https://github.com/pgvector/pgvector
- OpenAI API: https://platform.openai.com/docs

**Cost Tracking:**
- OpenAI Usage Dashboard: https://platform.openai.com/usage

---

## Final Thoughts

**You're building something valuable!** Minerva will be the foundational data layer for your peptide research, powering MyPeptidePal.ai with deep, structured knowledge.

**Start small, iterate fast:**
- Week 1 POCs validate the riskiest assumptions
- MVP is intentionally minimal
- Phase 2 adds polish
- Long-term vision guides without blocking

**Key Success Factors:**
- Quality matters more than speed
- Document as you go
- Celebrate milestones
- Have fun!

**Ready to start?** Run the Immediate Next Actions and begin Week 1!

---

**Project Brief Version:** 1.0
**Last Updated:** 2025-10-06
**Next Review:** After MVP Complete
