# Minerva

**Automated Kindle book knowledge extraction pipeline with semantic search capabilities**

## Overview

Minerva automates knowledge extraction from Kindle Cloud Reader books into a searchable PostgreSQL vector database. It uses browser automation (Playwright) to capture screenshots, Tesseract OCR to extract text with intelligent UI filtering, semantic chunking to preserve context, and vector embeddings for semantic search.

## Features

- 🤖 **Automated Screenshot Capture** - Playwright browser automation for Kindle Cloud Reader
- 🔍 **Intelligent OCR** - Tesseract-based text extraction with Kindle UI filtering
- ✨ **AI-Powered OCR Cleanup** - Optional GPT-4o-mini formatting for improved accuracy (~$0.01/100 pages)
- 🧹 **UI Filtering** - Automatically removes page numbers, progress bars, and navigation elements
- 📚 **Semantic Chunking** - Context-aware text segmentation for better retrieval
- 🔎 **Vector Search** - OpenAI embeddings with PostgreSQL pgvector
- 🎨 **Search UI** - Modern Tailwind v4 + Alpine.js interface for development
- 🔐 **Session Management** - Multi-service authentication with easy account switching
- ⚙️ **Configurable Navigation** - Adjustable page delays and rewind behavior
- 💬 **Interactive Book-End Detection** - User confirmation for capture completion
- 📤 **Production Export** - Safe SQL exports for deployment
- 🚀 **FastAPI Server** - RESTful API for semantic search

## Goals

- Reduce book extraction time from 4-6 hours (manual) to under 15 minutes (automated)
- Achieve 95%+ text extraction accuracy
- Create semantically searchable corpus with vector embeddings
- Maintain API costs under $2.50 per 100-page book
- Support ethical, legal extraction that respects DRM without circumvention

## Prerequisites

- **Python:** 3.11+
- **PostgreSQL:** 15+ with pgvector extension
- **Tesseract OCR:** 5.0+ for text extraction
- **OpenAI API Key:** For embeddings
- **Poetry:** 1.7+ for dependency management

## Installation

### 1. Install System Dependencies

**macOS:**
```bash
brew install tesseract postgresql@15
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr postgresql-15 postgresql-15-pgvector
```

### 2. Clone and Install Python Dependencies

```bash
git clone <repository-url>
cd kindlescraper
poetry install
```

### 3. Install Playwright Browsers

```bash
poetry run playwright install chromium
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...

# Database Configuration
DATABASE_URL=postgresql://postgres@localhost/mpp_minerva_local

# OCR Configuration (optional)
TESSERACT_CMD=tesseract
FILTER_KINDLE_UI=true  # Remove UI elements (default: true)

# Embedding Configuration
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

### 5. Initialize Database

```bash
# Create database (name matches DATABASE_URL in .env)
createdb mpp_minerva_local

# Run migrations (uses DATABASE_URL from .env)
poetry run alembic upgrade head
```

**Note:** To use a different database name, update `DATABASE_URL` in your `.env` file before running migrations.

### 6. Verify Installation

```bash
# Check Tesseract
tesseract --version

# Check database
psql postgresql://postgres@localhost/mpp_minerva_local -c "SELECT 1"

# Check Minerva CLI
poetry run minerva --version
```

## Quick Start

### 1. Ingest Your First Book

```bash
# Get the Kindle Cloud Reader URL for your book
# Navigate to: https://read.amazon.com/library
# Open a book and copy the URL

# Ingest the book
poetry run minerva ingest "https://read.amazon.com/..." \
  --title "My Book Title" \
  --author "Author Name"
```

On first run, you'll be prompted to log in to Amazon. The session will be saved for future use.

### 2. Process the Book

The ingestion pipeline automatically:
1. ✅ Captures all page screenshots
2. ✅ Extracts text using Tesseract OCR
3. ✅ Filters out Kindle UI elements (page numbers, progress bars)
4. ✅ Chunks text semantically for better retrieval
5. ✅ Generates vector embeddings
6. ✅ Stores everything in PostgreSQL

### 3. Start the API Server

```bash
poetry run uvicorn minerva.main:app --reload --port 8000
```

### 4. Use the Search Interface

**Option A: Web UI (Local Development)**

Visit the interactive search interface:
```
http://localhost:8000/search-ui
```

Features:
- Clean, modern interface with Tailwind CSS
- Real-time search with Alpine.js
- Adjustable similarity threshold and result count
- Context window expansion
- Only available in development mode (secure)

**Option B: API Endpoint**

```bash
curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your search query here",
    "top_k": 10,
    "similarity_threshold": 0.5
  }'
```

**Option C: Interactive API Docs**

Visit the auto-generated documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Search Tips:**
- Start with a similarity threshold of **0.5** (balanced)
- Lower threshold (0.2-0.4): More results, less precise
- Higher threshold (0.7-0.9): Fewer results, more precise
- Use multi-word phrases for better semantic matching
- Example: "teaching and expertise" works better than "experience"

## CLI Commands

### Book Ingestion

#### Basic Usage

```bash
# Basic ingestion (full pipeline: screenshots → OCR → chunking → embeddings)
poetry run minerva ingest <kindle_url>

# With metadata
poetry run minerva ingest <kindle_url> \
  --title "Book Title" \
  --author "Author Name"

# Limit number of pages
poetry run minerva ingest <kindle_url> --max-pages 50
```

#### Navigation Controls

Control the ingestion behavior with fine-grained parameters:

```bash
# Customize backward navigation (default: 100 presses)
poetry run minerva ingest <kindle_url> --rewind-presses 50

# Adjust page turn delays (default: 5-10 seconds)
poetry run minerva ingest <kindle_url> \
  --page-delay-min 5.0 \
  --page-delay-max 10.0

# Fast mode for testing (shorter delays, fewer rewinds)
poetry run minerva ingest <kindle_url> \
  --rewind-presses 50 \
  --page-delay-min 1 \
  --page-delay-max 3 \
  --max-pages 20

# Conservative mode (longer delays, more rewinds for reliability)
poetry run minerva ingest <kindle_url> \
  --rewind-presses 200 \
  --page-delay-min 8 \
  --page-delay-max 15
```

**Navigation Parameters:**
- `--rewind-presses`: Number of backward key presses to reach book start (default: 100)
  - Lower values (50-75): Faster, suitable for shorter books
  - Higher values (150-200): More reliable for longer books
- `--page-delay-min`: Minimum seconds between page turns (default: 5.0)
- `--page-delay-max`: Maximum seconds between page turns (default: 10.0)
  - Randomized delays appear more human-like
  - Adjust based on your internet speed and server response time

#### AI-Powered OCR Cleanup

By default, Minerva uses **Tesseract OCR** (free, local) to extract text from screenshots. For improved quality, you can enable **AI-powered cleanup** using GPT-4o-mini:

```bash
# Default: Tesseract OCR only (free)
poetry run minerva ingest <kindle_url>

# Enhanced: Tesseract + AI cleanup (small cost)
poetry run minerva ingest <kindle_url> --use-ai-formatting
```

**What `--use-ai-formatting` does:**
- ✅ Removes OCR artifacts and formatting glitches
- ✅ Fixes common OCR errors (e.g., `l` → `1`, `O` → `0`, `rn` → `m`)
- ✅ Standardizes paragraph breaks and structure
- ✅ Preserves ALL original content (no summarization or omission)
- ✅ Uses GPT-4o-mini for cost-effective cleanup

**Cost Impact:**
- Approximately **$0.01 per 100 pages** (GPT-4o-mini: $0.15/1M input tokens, $0.60/1M output tokens)
- Example: 300-page book = ~$0.03 extra for AI cleanup
- Cost is logged during processing for transparency

**When to use:**
- 📖 Books with poor scan quality or faded text
- 🔬 Technical books with special characters or formulas
- 📊 Documents with tables or complex formatting
- ✨ When maximum text accuracy is critical

**When to skip (default):**
- Modern books with high-quality scans
- Cost-sensitive processing of large volumes
- Initial testing or preview ingestion

**Example with full options:**
```bash
poetry run minerva ingest <kindle_url> \
  --title "Advanced Peptide Research" \
  --author "Dr. Smith" \
  --use-ai-formatting \
  --max-pages 100
```

#### Interactive Book-End Confirmation

When Minerva detects a possible book end (e.g., disabled "Next Page" button), it will **pause and ask for confirmation**:

```
⚠️  Possible book end detected at page 42
   Reason: "Next Page" button is disabled

💡 You can check the browser window to verify

❓ Is this the end of the book? (y/n): _
```

**Response options:**
- Type `y` or `yes`: Confirm end and stop capture
- Type `n` or `no`: Continue capturing (useful for false positives)

**Why this helps:**
- Some books have navigation issues at certain pages
- Long books may have temporary button states
- You maintain control over when to stop

#### Authentication & Sessions

```bash
# Force new authentication (switch accounts)
poetry run minerva ingest <kindle_url> --force-auth

# Screenshots only (skip OCR and embeddings)
poetry run minerva ingest <kindle_url> --screenshots-only
```

#### Complete Example

```bash
# Production-ready ingestion with custom parameters
poetry run minerva ingest 'https://read.amazon.com/?asin=B08LZLYCXL' \
  --title "Peptide Protocols" \
  --author "William A Seeds MD" \
  --max-pages 500 \
  --rewind-presses 100 \
  --page-delay-min 5 \
  --page-delay-max 10
```

### Session Management

Minerva saves your Amazon login session for convenience. Manage sessions with:

```bash
# View all sessions
poetry run minerva session status

# View specific service
poetry run minerva session status kindle

# Clear session (logout)
poetry run minerva session clear kindle

# Clear all sessions
poetry run minerva session clear --all
```

**Use cases:**
- Switch between Amazon accounts
- Troubleshoot authentication issues
- Logout before sharing your computer

### Export to Production

```bash
# Export a specific book
poetry run minerva export <book_id>

# Export all completed books
poetry run minerva export --all

# Custom output directory
poetry run minerva export <book_id> --output-dir /path/to/exports
```

## Features in Detail

### Intelligent UI Filtering

Minerva automatically removes Kindle Cloud Reader UI elements from extracted text:

**Filtered elements:**
- Page indicators: "Page x of 209 » 39%"
- Location indicators: "Location 2 of 2771 « 0%"
- Navigation text: "Kindle Library", "Learning reading speed"
- Progress bars and percentage indicators
- Font controls and sync status messages

**Benefits:**
- Cleaner chunks with only book content
- Better embedding quality for semantic search
- More relevant search results
- No UI noise in your knowledge base

**Configuration:**
```bash
# Enable/disable in .env
FILTER_KINDLE_UI=true  # Default: enabled
```

**Example:**
```
Before filtering:
"Page x of 209 » 39% Kindle Library Learning reading speed,+
If you've ever had the crazy dream to start your own business..."

After filtering:
"If you've ever had the crazy dream to start your own business..."
```

### Session Management

Multi-service authentication with future-proof design:

**File structure:**
```
~/.minerva/
  └── sessions/
      └── kindle.json    # Kindle Cloud Reader session
```

**Benefits:**
- Automatic login on subsequent runs
- Easy account switching with `--force-auth`
- Secure session storage (0600 permissions)
- Backward compatible with legacy sessions
- Ready for future services (PubMed, PDFs, etc.)

### Semantic Chunking

Context-aware text segmentation for optimal retrieval:

**Features:**
- Preserves paragraph boundaries
- Maintains semantic coherence
- Configurable chunk sizes
- Screenshot-to-chunk mapping
- Token counting for cost estimation

### Vector Search

Powered by PostgreSQL pgvector:

**Search options:**
- `top_k`: Number of results (default: 10)
- `similarity_threshold`: Minimum similarity (0-1, default: 0.7)
- `context_window`: Include surrounding chunks
- `book_ids`: Filter by specific books
- `date_range`: Filter by capture date

## API Reference

### Base URL

- **Local:** `http://localhost:8000`
- **Production:** `https://your-domain.com`

### Endpoints

#### Health Check
```http
GET /health
```

Returns API status and database connectivity.

#### Search UI (Development Only)
```http
GET /search-ui
```

Interactive search interface built with Tailwind v4 and Alpine.js. Features:
- Modern, responsive design
- Adjustable search parameters (top_k, similarity threshold)
- Collapsible context windows
- Color-coded similarity scores
- Real-time search with loading states

**Security:** Only accessible when `ENVIRONMENT=development`. Returns 404 in production.

#### Semantic Search
```http
POST /api/v1/search/semantic
Content-Type: application/json

{
  "query": "your search query",
  "top_k": 10,
  "similarity_threshold": 0.7,
  "context_window": 1,
  "book_ids": ["uuid"],
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "chunk_text": "...",
      "similarity_score": 0.89,
      "book_title": "Book Title",
      "book_author": "Author Name",
      "chunk_sequence": 42,
      "context_before": "previous chunk...",
      "context_after": "next chunk..."
    }
  ],
  "query_metadata": {
    "total_results": 10,
    "search_time_ms": 145,
    "embedding_model": "text-embedding-3-small"
  }
}
```

#### List Books
```http
GET /api/v1/books?limit=50&offset=0&status=completed
```

#### Get Book Details
```http
GET /api/v1/books/{book_id}
```

#### Get Chunk with Context
```http
GET /api/v1/chunks/{chunk_id}?context_window=2
```

### Interactive Documentation

Visit `/docs` for Swagger UI or `/redoc` for ReDoc documentation.

## Database Management

### Switching Databases

All Minerva commands (ingestion, migrations, API) use the `DATABASE_URL` from your `.env` file. To switch databases, simply update this value:

```bash
# Edit .env file
DATABASE_URL=postgresql+asyncpg://postgres@localhost/your_database_name
```

**Common database configurations:**

```bash
# Development
DATABASE_URL=postgresql+asyncpg://postgres@localhost/minerva_dev

# Testing
DATABASE_URL=postgresql+asyncpg://postgres@localhost/minerva_test

# Staging
DATABASE_URL=postgresql+asyncpg://postgres@localhost/minerva_staging

# Production (local setup)
DATABASE_URL=postgresql+asyncpg://postgres@localhost/minerva_prod
```

**All commands will use the configured database:**
```bash
# Create and migrate database
createdb your_database_name
poetry run alembic upgrade head

# Ingest books
poetry run minerva ingest <url>

# Start API
poetry run uvicorn minerva.main:app --reload
```

## Production Deployment

### Database Setup

```bash
# Create production database
createdb minerva_production

# Update .env with production database
DATABASE_URL=postgresql+asyncpg://postgres@localhost/minerva_production

# Run migrations
poetry run alembic upgrade head
```

### Export and Import

```bash
# 1. Export from local
poetry run minerva export <book_id> --output-dir exports/

# 2. Validate export
python scripts/validate_export.py exports/book_<uuid>.sql

# 3. Backup production (if data exists)
pg_dump $PRODUCTION_DATABASE_URL > backup_$(date +%Y%m%d).sql

# 4. Import to production
psql $PRODUCTION_DATABASE_URL -f exports/book_<uuid>.sql

# 5. Verify import
psql $PRODUCTION_DATABASE_URL -c \
  "SELECT COUNT(*) FROM chunks WHERE book_id = '<uuid>'"
```

### Docker Deployment

```bash
# Build image
docker build -t minerva-api .

# Run container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e ENVIRONMENT=production \
  minerva-api
```

### Environment Variables (Production)

```bash
# Required
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
ENVIRONMENT=production

# Optional
LOG_LEVEL=INFO
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Local Environment                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Playwright  │→ │  Tesseract   │→ │   Semantic   │      │
│  │  Automation  │  │     OCR      │  │   Chunking   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         v                  v                  v              │
│  ┌─────────────────────────────────────────────────┐        │
│  │         PostgreSQL + pgvector (Local)           │        │
│  └─────────────────────────────────────────────────┘        │
│                         │                                    │
│                         │ SQL Export                         │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          v
┌─────────────────────────┼────────────────────────────────────┐
│                Production Environment                         │
│  ┌─────────────────────────────────────────────────┐         │
│  │         PostgreSQL + pgvector (Production)      │         │
│  └──────────────────────┬──────────────────────────┘         │
│                         │                                     │
│                         v                                     │
│  ┌─────────────────────────────────────────────────┐         │
│  │         FastAPI Server (Read-only API)          │         │
│  └─────────────────────────────────────────────────┘         │
│                         │                                     │
│                         v                                     │
│            ┌────────────────────────────┐                     │
│            │  Clients (Web, Mobile, AI) │                     │
│            └────────────────────────────┘                     │
└───────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Capture** → Playwright navigates Kindle Cloud Reader, captures page screenshots
2. **Extract** → Tesseract OCR extracts text, filters UI elements
3. **Chunk** → Semantic chunker creates context-aware segments
4. **Embed** → OpenAI API generates vector embeddings
5. **Store** → PostgreSQL stores chunks with pgvector embeddings
6. **Export** → SQL export for production deployment
7. **Search** → FastAPI serves semantic search queries

## Project Structure

```
minerva/
├── minerva/                    # Main package
│   ├── api/                   # FastAPI application
│   │   ├── routes/           # API endpoints
│   │   ├── schemas/          # Pydantic models
│   │   └── middleware.py     # CORS, logging
│   ├── cli/                  # CLI commands
│   │   └── app.py           # Typer CLI app
│   ├── core/                 # Core business logic
│   │   ├── ingestion/       # Screenshot, OCR, chunking
│   │   │   ├── kindle_automation.py
│   │   │   ├── text_extraction.py
│   │   │   ├── text_cleaner.py      # UI filtering
│   │   │   ├── semantic_chunking.py
│   │   │   └── embedding_generator.py
│   │   ├── search/          # Vector search
│   │   └── export/          # Production export
│   ├── db/                   # Database layer
│   │   ├── models/          # SQLAlchemy models
│   │   └── repositories/    # Data access
│   ├── utils/               # Utilities
│   │   ├── session_manager.py    # Session management
│   │   ├── exceptions.py
│   │   └── logging.py
│   └── config.py            # Configuration
├── alembic/                  # Database migrations
│   └── versions/            # Migration files
├── tests/                    # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
├── .env.example             # Environment template
├── pyproject.toml           # Poetry configuration
├── alembic.ini              # Alembic configuration
├── Dockerfile               # Docker image
└── README.md                # This file
```

## Development

### Setup Development Environment

```bash
# Install dev dependencies
poetry install

# Install pre-commit hooks (if available)
poetry run pre-commit install

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=minerva --cov-report=html
```

### Code Quality

```bash
# Format code
poetry run black .

# Lint
poetry run ruff check .

# Type check
poetry run mypy minerva/

# Run all checks
poetry run black . && poetry run ruff check . && poetry run mypy minerva/
```

### Database Migrations

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/unit/test_text_cleaner.py

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=minerva --cov-report=term-missing

# Run only unit tests
poetry run pytest tests/unit/

# Run only integration tests
poetry run pytest tests/integration/
```

## Troubleshooting

### Common Issues

**1. Tesseract not found**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Verify installation
tesseract --version
```

**2. pgvector extension missing**
```sql
-- Connect to database
psql $DATABASE_URL

-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;
```

**3. Authentication issues**
```bash
# Clear saved session and re-authenticate
poetry run minerva session clear kindle
poetry run minerva ingest <url> --force-auth
```

**4. OCR quality issues**
- Ensure Tesseract 5.0+ is installed
- Check screenshot quality (should be 1920x1080 minimum)
- Enable AI formatting for better results (costs extra)

**5. Database connection errors**
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection string
psql $DATABASE_URL -c "SELECT 1"

# Check database exists
psql -l | grep minerva
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
poetry run minerva ingest <url> -v
```

### Getting Help

- **Issues:** https://github.com/your-repo/issues
- **Discussions:** https://github.com/your-repo/discussions
- **Documentation:** `docs/` directory

## Performance

### Costs

- **Text Extraction (Tesseract):** Free
- **Embeddings (text-embedding-3-small):** ~$0.02 per 100 pages
- **Total per book (200 pages):** ~$0.04

### Speed

- **Screenshot capture:** ~2-3 seconds per page
- **OCR extraction:** ~1-2 seconds per page
- **Embedding generation:** ~0.5 seconds per page
- **Total ingestion time:** ~10-15 minutes per 200-page book

### Storage

- **Screenshots:** ~500KB per page (not stored in production)
- **Text chunks:** ~1KB per chunk
- **Embeddings:** ~6KB per chunk (1536 dimensions)
- **Total per book (200 pages, ~400 chunks):** ~2.8MB

## Security

### Best Practices

- Store API keys in environment variables, never in code
- Use secure session storage (0600 permissions)
- Limit production database permissions (SELECT, INSERT only)
- Enable CORS only for trusted origins
- Use HTTPS in production
- Regularly rotate API keys
- Monitor API usage and costs

### Data Privacy

- Screenshots are never uploaded to external services
- Text extraction happens locally with Tesseract
- Only embeddings are sent to OpenAI API (no raw text)
- Production exports exclude local file paths
- Sessions are stored locally with secure permissions

## Use Cases & Examples

### Testing a New Book (Quick Mode)
```bash
# Fast capture for preview/testing
poetry run minerva ingest 'https://read.amazon.com/?asin=...' \
  --max-pages 20 \
  --rewind-presses 50 \
  --page-delay-min 1 \
  --page-delay-max 2
```

### Production Ingestion (Conservative Mode)
```bash
# Reliable capture with longer delays
poetry run minerva ingest 'https://read.amazon.com/?asin=...' \
  --title "Complete Book Title" \
  --author "Author Name" \
  --rewind-presses 150 \
  --page-delay-min 7 \
  --page-delay-max 12
```

### High-Quality OCR for Technical Books
```bash
# Use AI cleanup for optimal accuracy (technical content, poor scans, etc.)
poetry run minerva ingest 'https://read.amazon.com/?asin=...' \
  --title "Advanced Peptide Research" \
  --author "Dr. Smith" \
  --use-ai-formatting
```

### Switching Amazon Accounts
```bash
# Clear current session
poetry run minerva session clear kindle

# Ingest with new account
poetry run minerva ingest <url> --force-auth
```

### Processing Existing Screenshots
```bash
# If you only captured screenshots earlier
poetry run minerva process <book-uuid>
```

### Exporting for Production
```bash
# Export completed book
poetry run minerva export <book-uuid>

# Import to production database
psql $PRODUCTION_DB -f exports/book_<uuid>.sql
```

## Roadmap

### Current Features (v1.0)
- ✅ Kindle Cloud Reader automation
- ✅ Tesseract OCR with UI filtering
- ✅ Semantic chunking and embeddings
- ✅ Vector search with PostgreSQL
- ✅ Session management
- ✅ Interactive book-end confirmation
- ✅ Configurable navigation (delays, rewind)
- ✅ Development search UI (Tailwind v4 + Alpine.js)
- ✅ Production export/import
- ✅ RESTful API

### Planned Features (v1.1)
- 🔲 Support for more e-book platforms
- 🔲 OCR quality validation and retry
- 🔲 Bulk book processing
- 🔲 Progress resumption for failed ingestions
- 🔲 Advanced search filters (date ranges, metadata)

### Future Considerations
- 🔮 Support for PDFs and other document formats
- 🔮 Integration with PubMed and research databases
- 🔮 RAG (Retrieval Augmented Generation) integration
- 🔮 Web UI for book management
- 🔮 API authentication and rate limiting

## Contributing

This is a personal research tool, but contributions are welcome!

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`poetry run pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation
- Keep commits atomic and well-described
- Ensure all tests pass before submitting PR

## License

MIT License - see LICENSE file for details

## Acknowledgments

- **Playwright** - Browser automation framework
- **Tesseract** - Open-source OCR engine
- **OpenAI** - Embedding API
- **PostgreSQL & pgvector** - Vector database
- **FastAPI** - Modern web framework
- **Typer** - CLI framework

## Support

- **Documentation:** `docs/` directory
- **Issues:** GitHub Issues
- **Email:** your-email@example.com

---

Built with ❤️ for researchers and knowledge workers
