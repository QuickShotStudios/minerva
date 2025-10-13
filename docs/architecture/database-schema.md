# Database Schema

Minerva uses PostgreSQL 15+ with the pgvector extension for vector similarity search. The schema supports both local ingestion and production query environments.

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Books table
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255),
    kindle_url TEXT NOT NULL,
    total_screenshots INTEGER,
    capture_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingestion_status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
    ingestion_error TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT chk_books_ingestion_status CHECK (ingestion_status IN (
        'in_progress', 'screenshots_complete', 'text_extracted',
        'chunks_created', 'embeddings_generated', 'completed', 'failed'
    ))
);

CREATE INDEX idx_books_status ON books(ingestion_status);
CREATE INDEX idx_books_capture_date ON books(capture_date DESC);
CREATE INDEX idx_books_metadata ON books USING GIN(metadata);

-- Screenshots table
CREATE TABLE screenshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    file_path TEXT,  -- NULL in production (not exported)
    screenshot_hash VARCHAR(64) NOT NULL,
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_screenshots_book_sequence UNIQUE (book_id, sequence_number)
);

CREATE INDEX idx_screenshots_book_id ON screenshots(book_id);
CREATE INDEX idx_screenshots_hash ON screenshots(screenshot_hash);

-- Embedding configs table
CREATE TABLE embedding_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    dimensions INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_embedding_configs_active ON embedding_configs(is_active) 
    WHERE is_active = TRUE;

-- Chunks table with pgvector
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    screenshot_ids UUID[] NOT NULL,
    chunk_sequence INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_token_count INTEGER NOT NULL,
    embedding_config_id UUID REFERENCES embedding_configs(id),
    embedding VECTOR(1536),
    vision_model VARCHAR(50) NOT NULL,
    metadata_model VARCHAR(50),
    extracted_peptides TEXT[],
    extracted_dosages TEXT[],
    extracted_studies TEXT[],
    contains_peptide_data BOOLEAN DEFAULT FALSE,
    extraction_confidence JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_chunks_book_sequence UNIQUE (book_id, chunk_sequence)
);

CREATE INDEX idx_chunks_book_id ON chunks(book_id);
CREATE INDEX idx_chunks_sequence ON chunks(chunk_sequence);
CREATE INDEX idx_chunks_embedding_config ON chunks(embedding_config_id);
CREATE INDEX idx_chunks_peptides ON chunks USING GIN(extracted_peptides);

-- IVFFlat index for vector similarity search (CRITICAL FOR PERFORMANCE)
CREATE INDEX idx_chunks_embedding_ivfflat ON chunks 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Ingestion logs table
CREATE TABLE ingestion_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    log_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT chk_ingestion_logs_level CHECK (log_level IN ('INFO', 'WARNING', 'ERROR'))
);

CREATE INDEX idx_ingestion_logs_book_id ON ingestion_logs(book_id);
CREATE INDEX idx_ingestion_logs_level ON ingestion_logs(log_level);
CREATE INDEX idx_ingestion_logs_created_at ON ingestion_logs(created_at DESC);

-- Helper functions
CREATE OR REPLACE FUNCTION cosine_similarity(a VECTOR, b VECTOR)
RETURNS FLOAT AS $$
    SELECT 1 - (a <-> b);
$$ LANGUAGE SQL IMMUTABLE STRICT PARALLEL SAFE;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_books_updated_at 
    BEFORE UPDATE ON books
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Initial data
INSERT INTO embedding_configs (model_name, model_version, dimensions, is_active)
VALUES ('text-embedding-3-small', NULL, 1536, TRUE)
ON CONFLICT DO NOTHING;
```

---
