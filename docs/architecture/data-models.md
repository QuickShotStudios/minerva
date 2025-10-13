# Data Models

These are the core data entities that represent Minerva's knowledge base. Models are defined using SQLModel, which provides both database schema (SQLAlchemy) and API validation (Pydantic) in a single definition.

## Book

**Purpose:** Represents a single Kindle book that has been ingested or is in the process of ingestion. Tracks metadata, ingestion status, and relationships to screenshots and chunks.

**Key Attributes:**
- `id`: UUID - Primary key, unique identifier for the book
- `title`: str - Book title (extracted from Kindle or user-provided)
- `author`: str (optional) - Book author
- `kindle_url`: str - Kindle Cloud Reader URL for this book
- `total_screenshots`: int (optional) - Count of captured screenshots
- `capture_date`: datetime - When screenshot capture started
- `ingestion_status`: str - Current state: 'in_progress', 'screenshots_complete', 'text_extracted', 'chunks_created', 'embeddings_generated', 'completed', 'failed'
- `ingestion_error`: str (optional) - Error message if ingestion failed
- `metadata`: dict (JSONB) - Flexible storage for ISBN, publication year, etc.
- `created_at`: datetime - Record creation timestamp
- `updated_at`: datetime - Last update timestamp

**Relationships:**
- One-to-many with Screenshot (book has many screenshots)
- One-to-many with Chunk (book has many chunks)
- One-to-many with IngestionLog (book has many log entries)

## Screenshot

**Purpose:** Represents a single page screenshot captured from Kindle Cloud Reader. Stores file location, sequence order, and hash for deduplication. Screenshots are stored locally only and never exported to production.

**Key Attributes:**
- `id`: UUID - Primary key, unique identifier for the screenshot
- `book_id`: UUID - Foreign key to Book
- `sequence_number`: int - Page order (1, 2, 3...), unique per book
- `file_path`: str - Local filesystem path to PNG file (e.g., `screenshots/{book_id}/page_001.png`)
- `screenshot_hash`: str - SHA256 hash for duplicate detection and book-end verification
- `captured_at`: datetime - Timestamp when screenshot was captured

**Relationships:**
- Many-to-one with Book (screenshot belongs to one book)
- Referenced by Chunk.screenshot_ids array (chunks can span multiple screenshots)

**Constraints:**
- Unique constraint on (book_id, sequence_number) - prevents duplicate page numbers

## EmbeddingConfig

**Purpose:** Tracks which embedding model and version was used to generate embeddings. Enables re-embedding capability and model upgrade tracking. Multiple configs can exist (historical), but only one is active at a time.

**Key Attributes:**
- `id`: UUID - Primary key, unique identifier for the config
- `model_name`: str - OpenAI model name (e.g., 'text-embedding-3-small')
- `model_version`: str (optional) - Model version identifier if available
- `dimensions`: int - Vector dimensions (1536 for text-embedding-3-small)
- `is_active`: bool - True if this is the current embedding model
- `created_at`: datetime - When this config was created

**Relationships:**
- One-to-many with Chunk (config is referenced by many chunks)

## Chunk

**Purpose:** Represents a semantic text chunk extracted from book screenshots. Contains the extracted text, its vector embedding for semantic search, and references to source screenshots. This is the primary searchable entity.

**Key Attributes:**
- `id`: UUID - Primary key, unique identifier for the chunk
- `book_id`: UUID - Foreign key to Book
- `screenshot_ids`: list[UUID] - Array of screenshot IDs this chunk spans (typically 1, sometimes 2 for overlapping chunks)
- `chunk_sequence`: int - Order of chunk within book (1, 2, 3...)
- `chunk_text`: str - Extracted text content (500-800 tokens typically)
- `chunk_token_count`: int - Actual token count using tiktoken
- `embedding_config_id`: UUID - Foreign key to EmbeddingConfig
- `embedding`: Vector(1536) - pgvector type, semantic embedding
- `vision_model`: str - Which GPT model extracted this text (e.g., 'gpt-4o-mini')
- `metadata_model`: str (optional) - Which model extracted metadata (Phase 1.5)
- `extracted_peptides`: list[str] (optional) - Peptide names found (Phase 1.5)
- `extracted_dosages`: list[str] (optional) - Dosages mentioned (Phase 1.5)
- `extracted_studies`: list[str] (optional) - Study references (Phase 1.5)
- `contains_peptide_data`: bool - Flag for filtering (Phase 1.5)
- `extraction_confidence`: dict (JSONB, optional) - Confidence scores (Phase 1.5)
- `created_at`: datetime - Record creation timestamp

**Relationships:**
- Many-to-one with Book (chunk belongs to one book)
- Many-to-one with EmbeddingConfig (chunk uses one embedding config)
- References multiple Screenshot entities via screenshot_ids array

**Indexes:**
- B-tree index on book_id (for filtering searches by book)
- IVFFlat index on embedding (for fast cosine similarity search)

## IngestionLog

**Purpose:** Debugging and audit trail for ingestion pipeline. Tracks key events, errors, and warnings during book processing. Useful for troubleshooting failed ingestions.

**Key Attributes:**
- `id`: UUID - Primary key
- `book_id`: UUID - Foreign key to Book
- `log_level`: str - 'INFO', 'WARNING', 'ERROR'
- `message`: str - Human-readable log message
- `metadata`: dict (JSONB, optional) - Additional structured context
- `created_at`: datetime - Log entry timestamp

**Relationships:**
- Many-to-one with Book (log entry belongs to one book)

---
