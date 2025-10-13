# Tech Stack

This is the **DEFINITIVE technology selection** for the entire project. All development must use these exact versions. This table serves as the single source of truth.

## Cloud Infrastructure

- **Provider:** Hybrid (Local + Cloud Hosting)
- **Local Environment:** macOS (Darwin 25.0.0) for ingestion pipeline
- **Production Hosting:** Railway, Fly.io, or Render (lightweight API deployment)
- **Database Hosting:** Supabase or Neon (PostgreSQL with pgvector support)
- **Deployment Regions:** US-based (single region for MVP)

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|-----------|---------|---------|-----------|
| **Language** | Python | 3.11+ | Primary development language | Modern async/await support, excellent AI/ML ecosystem, type hints, SQLModel compatibility |
| **Package Manager** | Poetry | 1.7+ | Dependency management | Deterministic builds, lockfile for reproducibility, excellent virtual env management |
| **Backend Framework** | FastAPI | 0.104+ | API framework | Best-in-class async support, automatic OpenAPI docs, Pydantic validation, excellent DX |
| **ORM/Models** | SQLModel | 0.0.14+ | Database models + API schemas | Unified Pydantic/SQLAlchemy models, reduces duplication, type safety |
| **Database** | PostgreSQL | 15+ | Primary data store | ACID compliance, pgvector extension support, excellent Python ecosystem |
| **Vector Extension** | pgvector | 0.5+ | Vector similarity search | Native PostgreSQL integration, ivfflat indexing, cosine similarity operators |
| **Database Driver** | asyncpg | 0.29+ | Async PostgreSQL driver | Fastest Python PostgreSQL driver, native async support, connection pooling |
| **Migrations** | Alembic | 1.13+ | Database schema migrations | Industry standard, SQLAlchemy integration, version control for schemas |
| **Browser Automation** | Playwright | 1.40+ | Kindle page capture | Reliable browser automation, screenshot support, session persistence, active maintenance |
| **OCR Engine** | Tesseract | 5.0+ | Screenshot text extraction | Open-source, no content restrictions, 95%+ accuracy, no API costs |
| **OCR Python Wrapper** | pytesseract | 0.3.10+ | Tesseract Python interface | Simple API, image preprocessing support, configurable PSM modes |
| **AI/ML API** | OpenAI Python SDK | 1.12+ | Embeddings + optional text formatting | Official SDK, async support, embedding generation |
| **Text Formatting (Optional)** | gpt-4o-mini | latest | OCR output cleanup | Optional post-processing to fix OCR artifacts, minimal token usage (~$0.01/100 pages) |
| **Embedding Model** | text-embedding-3-small | latest | Vector embeddings (1536 dims) | Cost-effective ($0.02/1M tokens), excellent quality, 1536 dimensions for pgvector |
| **Configuration** | Pydantic Settings | 2.5+ | Environment management | Type-safe config, .env file support, validation, nested settings |
| **Environment Files** | python-dotenv | 1.0+ | .env loading | Simple .env parsing, development convenience |
| **CLI Framework** | Typer | 0.9+ | Command-line interface | Intuitive API, automatic help generation, Pydantic integration, excellent UX |
| **CLI UI** | Rich | 13.7+ | Terminal UI and progress bars | Beautiful progress tracking, formatted tables, colored output for CLI |
| **Logging** | structlog | 24.1+ | Structured logging | JSON logging for production, context binding, excellent async support |
| **Testing Framework** | pytest | 7.4+ | Unit + integration tests | Industry standard, excellent plugin ecosystem, fixture support |
| **Async Testing** | pytest-asyncio | 0.23+ | Async test support | Required for testing FastAPI + asyncpg code |
| **HTTP Client (tests)** | httpx | 0.26+ | API testing client | Async support, drop-in requests replacement, excellent for FastAPI tests |
| **Code Formatting** | black | 24.1+ | Code formatting | Opinionated formatter, eliminates style debates, consistent codebase |
| **Linting** | ruff | 0.1+ | Linting + import sorting | Extremely fast, replaces flake8/isort/pylint, modern Python linter |
| **Type Checking** | mypy | 1.8+ | Static type checking | Catches type errors, enforces type hints, critical for large codebases |
| **Image Processing** | Pillow | 10.1+ | Screenshot handling | Image format conversion, future optimization (compression) |
| **Token Counting** | tiktoken | 0.5+ | Accurate token counting | OpenAI's official tokenizer, accurate cost estimation, chunking optimization |
| **Monitoring (Prod)** | Native platform logging | N/A | Log aggregation | Railway/Fly.io native logging, structlog JSON output |
| **Error Tracking (Prod)** | Sentry | 1.40+ | Error monitoring (optional) | Real-time error tracking, performance monitoring, free tier available |
| **CI/CD** | GitHub Actions | N/A | Automated testing + deployment | Free for public repos, excellent Python support, Railway/Fly.io integration |

---
