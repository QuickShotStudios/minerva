# REST API Specification

Minerva provides a RESTful API for querying the knowledge base. This API is deployed in production only (lightweight deployment without ingestion capabilities).

See full OpenAPI 3.0 specification in the PRD document at `docs/prd.md` for complete endpoint definitions including:
- POST /api/v1/search/semantic - Vector similarity search
- GET /api/v1/books - List books with pagination
- GET /api/v1/books/{book_id} - Book details
- GET /api/v1/chunks/{chunk_id} - Chunk with context
- GET /health - Health check endpoint

All endpoints return JSON responses with standard error handling and validation via Pydantic.

---
