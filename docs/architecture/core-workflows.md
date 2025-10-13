# Core Workflows

These sequence diagrams illustrate critical system workflows, showing how components interact to fulfill key user journeys from the PRD.

## Workflow 1: Book Ingestion (End-to-End)

```mermaid
sequenceDiagram
    actor User
    participant CLI
    participant Pipeline
    participant Kindle as Kindle Automation
    participant Extract as Text Extraction
    participant Chunk as Semantic Chunker
    participant Embed as Embedding Generator
    participant Repo as Database Repository
    participant DB as PostgreSQL
    participant OpenAI as OpenAI API
    participant KCR as Kindle Cloud Reader

    User->>CLI: minerva ingest <kindle_url>
    CLI->>Pipeline: ingest_book(kindle_url, metadata)

    Note over Pipeline: Stage 1: Screenshot Capture
    Pipeline->>Repo: create_book(status='in_progress')
    Repo->>DB: INSERT book
    DB-->>Repo: Book created

    Pipeline->>Kindle: capture_all_pages(kindle_url)
    Kindle->>KCR: Navigate to book URL
    alt Session Valid
        KCR-->>Kindle: Book loaded
    else Session Expired
        Kindle->>User: Prompt for login
        User->>KCR: Manual login
        Kindle->>Kindle: Save session state
    end

    loop For each page
        Kindle->>KCR: Take screenshot
        KCR-->>Kindle: PNG image
        Kindle->>Kindle: Calculate SHA256 hash
        Kindle->>Repo: save_screenshot(image, hash)
        Repo->>DB: INSERT screenshot
        Kindle->>KCR: Next page (arrow key)
        alt Duplicate hash detected
            Note over Kindle: Book end reached
        end
    end
    Kindle-->>Pipeline: List[Screenshot]
    Pipeline->>Repo: update_book_status('screenshots_complete')

    Note over Pipeline: Stage 2: Text Extraction
    Pipeline->>Extract: extract_text_batch(screenshots)
    loop Batch of screenshots (parallel)
        Extract->>OpenAI: POST /chat/completions (Vision)
        Note over Extract,OpenAI: gpt-4o-mini with image
        alt Success
            OpenAI-->>Extract: Extracted text
        else Rate Limit (429)
            Extract->>Extract: Exponential backoff (1s, 2s, 4s)
            Extract->>OpenAI: Retry request
        end
    end
    Extract-->>Pipeline: List[ExtractedText]
    Pipeline->>Repo: update_book_status('text_extracted')

    Note over Pipeline: Stage 3: Semantic Chunking
    Pipeline->>Chunk: create_chunks(extracted_texts)
    Chunk->>Chunk: Split at paragraph boundaries
    Chunk->>Chunk: Calculate 15% overlap
    Chunk->>Chunk: Count tokens (tiktoken)
    Chunk-->>Pipeline: List[Chunk] (without embeddings)
    Pipeline->>Repo: save_chunks(chunks)
    Repo->>DB: INSERT chunks (embedding=NULL)
    Pipeline->>Repo: update_book_status('chunks_created')

    Note over Pipeline: Stage 4: Embedding Generation
    Pipeline->>Embed: generate_embeddings(chunks)
    Embed->>Repo: get_or_create_embedding_config('text-embedding-3-small')
    loop Batches of 100 chunks
        Embed->>OpenAI: POST /embeddings (batch)
        OpenAI-->>Embed: 1536-dim vectors
        Embed->>Repo: update_chunk_embeddings(chunks, vectors)
        Repo->>DB: UPDATE chunks SET embedding
    end
    Embed-->>Pipeline: Success
    Pipeline->>Repo: update_book_status('completed')

    Pipeline-->>CLI: Book ingestion complete
    CLI-->>User: Success! Cost: $2.15, Time: 12m 34s
```

## Workflow 2: Semantic Search Query (Production API)

```mermaid
sequenceDiagram
    actor MPP as MyPeptidePal.ai
    participant API as FastAPI
    participant Search as Vector Search
    participant Repo as Repository
    participant DB as PostgreSQL
    participant OpenAI as OpenAI API

    MPP->>API: POST /api/v1/search/semantic
    Note over MPP,API: {query: "BPC-157 gut health", top_k: 10}

    API->>API: Validate request (Pydantic)
    API->>Search: search_semantic(query, filters)

    Note over Search: Generate query embedding
    Search->>OpenAI: POST /embeddings
    Note over Search,OpenAI: text-embedding-3-small
    OpenAI-->>Search: [1536-dimensional vector]

    Note over Search: Vector similarity search
    Search->>Repo: find_similar_chunks(embedding, filters)
    Repo->>DB: SELECT with pgvector <-> operator
    Note over DB: Using IVFFlat index for fast search
    DB-->>Repo: Ranked chunks (cosine similarity)

    Repo->>Repo: Filter by similarity_threshold (0.7)
    Repo->>Repo: Join with books table for metadata
    Repo-->>Search: List[Chunk with Book]

    Search->>Search: Format search results
    Search-->>API: SearchResponse

    API-->>MPP: 200 OK
    Note over API,MPP: {results: [...], query_metadata: {...}}
```

## Workflow 3: Export to Production

```mermaid
sequenceDiagram
    actor User
    participant CLI
    participant Export as Export Service
    participant Repo as Repository
    participant DB as Local DB
    participant SQL as SQL File
    participant ProdDB as Production DB

    User->>CLI: minerva export --book-id <uuid>
    CLI->>Export: export_book(book_id)

    Note over Export: Pre-export validation
    Export->>Repo: get_book_by_id(book_id)
    Repo->>DB: SELECT book WHERE id = ?
    DB-->>Repo: Book record

    alt Book not completed
        Export-->>CLI: Error: Book ingestion not complete
        CLI-->>User: Cannot export incomplete book
    end

    Export->>Repo: get_all_chunks(book_id)
    Repo->>DB: SELECT chunks WHERE book_id = ?
    DB-->>Repo: List[Chunk with embeddings]

    Export->>Repo: get_screenshots_metadata(book_id)
    Repo->>DB: SELECT id, book_id, sequence, hash
    Note over Export,DB: Excludes file_path (local only)
    DB-->>Repo: List[Screenshot metadata]

    Export->>Repo: get_embedding_config(book)
    Repo->>DB: SELECT embedding_configs
    DB-->>Repo: EmbeddingConfig

    Note over Export: Generate SQL export
    Export->>SQL: Write BEGIN transaction
    Export->>SQL: Write INSERT INTO books
    Export->>SQL: Write INSERT INTO screenshots (no file_path)
    Export->>SQL: Write INSERT INTO chunks (with embeddings)
    Export->>SQL: Write INSERT INTO embedding_configs
    Export->>SQL: Write COMMIT
    Note over SQL: Uses ON CONFLICT for idempotency

    Export-->>CLI: Export complete
    CLI-->>User: Success! Export file: exports/book_uuid_timestamp.sql
    CLI-->>User: Instructions: Run SQL against production DB

    Note over User,ProdDB: Manual step
    User->>ProdDB: psql -f exports/book_uuid_timestamp.sql
    ProdDB-->>User: Data imported successfully
```

_(Continued in next message due to length...)_
