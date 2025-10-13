# External APIs

Minerva integrates with external services for AI-powered embeddings and optional text formatting. These integrations are critical to the system's core functionality.

## OpenAI API (Embeddings + Optional Formatting)

**Purpose:** Provides text-embedding models for semantic vector generation and optional GPT models for OCR output formatting cleanup.

**Documentation:** https://platform.openai.com/docs/api-reference

**Base URL(s):**
- `https://api.openai.com/v1/embeddings` (Embeddings)
- `https://api.openai.com/v1/chat/completions` (Optional formatting cleanup)

**Authentication:** Bearer token (API key)
- Method: `Authorization: Bearer $OPENAI_API_KEY`
- API key stored in environment variable `OPENAI_API_KEY`
- Never logged or exposed in error messages

**Rate Limits:**
- **Tier 1** (default for new accounts):
  - 500 requests per minute (RPM)
  - 200,000 tokens per minute (TPM)
- **Tier 2+** (after $50+ spending):
  - 5,000 RPM, 2,000,000 TPM
- **Batch API:** 50% cost reduction, 24-hour processing window

**Key Endpoints Used:**

**1. Embeddings API (Vector Generation)**
- `POST /v1/embeddings`
- Purpose: Generate 1536-dimensional vector embeddings for semantic search
- Cost: $0.02 per 1M tokens (standard) or $0.01 per 1M tokens (batch)
- Batch size: Up to 2048 inputs per request
- Expected tokens per chunk: ~500-800
- Estimated cost per 200 chunks: ~$0.01-0.02

**2. Chat Completions API (Optional Text Formatting)**
- `POST /v1/chat/completions`
- Purpose: Optional cleanup of Tesseract OCR output to remove artifacts
- Model: gpt-4o-mini
- Cost: $0.15 per 1M input tokens + $0.60 per 1M output tokens
- Expected tokens per page: ~500-1000 input, ~200-400 output
- Estimated cost per page: ~$0.0001-0.0002 (only if formatting enabled)
- Configurable via `USE_AI_FORMATTING` environment variable (default: false)

**Integration Notes:**

**Error Handling:**
- **429 (Rate Limit):** Exponential backoff starting at 1s, max 3 retries
- **5xx (Server Error):** Retry up to 3 times with 2s delay
- **4xx (Client Error):** Log and fail immediately (no retry)
- Track retry attempts in ingestion logs

**Cost Optimization:**
- Batch embeddings requests (100 chunks per call)
- Consider Batch API for non-urgent books (50% cost savings)
- Keep AI formatting disabled by default (free Tesseract OCR is sufficient for most cases)
- Log all token usage for budget tracking

**Timeout Configuration:**
- Embeddings API: 30s timeout (typically fast)
- Chat Completions (formatting): 30s timeout
- Connection timeout: 10s

## Tesseract OCR

**Purpose:** Local OCR engine for extracting text from screenshot images without AI content policy restrictions.

**Type:** Local binary (not an API)

**Installation:**
- macOS: `brew install tesseract`
- Linux: `apt-get install tesseract-ocr`
- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki

**Integration:** Via `pytesseract` Python wrapper or direct subprocess calls

**Configuration:**
- PSM Mode: 3 (automatic page segmentation with fully automatic orientation and script detection)
- Output: Plain text with structure preservation
- Language: English (eng) default, configurable via `--lang` flag
- Version: 5.0+ recommended

**Cost:** $0 (open-source, runs locally)

**Performance:**
- Processing time: ~1-2 seconds per page
- Accuracy: 95%+ on clean book screenshots
- No rate limits (local processing)

**Error Handling:**
- Missing tesseract binary: Fail with clear installation instructions
- Invalid image format: Convert with Pillow or reject with error message
- OCR confidence threshold: Log warnings for low-confidence extractions (future enhancement)
- Subprocess timeout: 30s timeout per page, log error and continue

**Optional AI Formatting Pass:**
- After OCR extraction, optionally use gpt-4o-mini to clean artifacts
- Prompt: "Clean this OCR-extracted text by removing artifacts, standardizing formatting, and preserving all content. Return only the cleaned text."
- Cost: Minimal (~$0.01 per 100 pages if used)
- Configurable via `USE_AI_FORMATTING` environment variable (default: false)
- Use cases: Heavy OCR artifacts, tables, complex formatting

## Kindle Cloud Reader (Amazon)

**Purpose:** Source of book content. Minerva accesses Kindle books through browser automation (Playwright), not a formal API.

**Access Method:** Web scraping via Playwright browser automation

**Base URL(s):** `https://read.amazon.com/`

**Authentication:**
- Method: Manual login via visible browser window (one-time)
- Session persistence: Browser context state saved to `~/.minerva/session_state.json`
- Session duration: Typically 30-90 days before re-authentication required
- Security: Credentials never stored, only session cookies

**Integration Notes:**

**Reliability Concerns:**
- Amazon UI changes can break automation (medium risk)
- Solution: Use robust selectors, test regularly, graceful fallback
- Session expiration: Detect auth failures, prompt for re-login

**Legal & Terms of Service:**
- Minerva respects Amazon's ToS by:
  - Only capturing visual content (no DRM circumvention)
  - Personal use only (not commercial)
  - No redistribution of screenshots
  - Mimicking human reading behavior
- Screenshots stored locally only, never exported to production

**Error Handling:**
- Session expired: Detect, pause, prompt user to re-authenticate
- Network failures: Retry with exponential backoff (3 attempts)
- Page load timeout: 30s timeout, retry on failure
- Duplicate pages: Skip if screenshot hash matches previous

**Security:**
- Session state file permissions: 600 (owner read/write only)
- Location: `~/.minerva/session_state.json` (outside project directory)
- Never committed to git
- Excluded from exports (production never has Amazon credentials)

---
