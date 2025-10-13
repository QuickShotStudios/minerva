# Source Tree

```plaintext
minerva/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy-production.yml
├── .minerva/                          # Local runtime (gitignored)
│   └── session_state.json
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── script.py.mako
├── docs/
│   ├── prd.md
│   ├── brief.md
│   └── architecture.md                # This document
├── exports/                           # SQL exports (gitignored)
├── screenshots/                       # Local screenshots (gitignored)
│   └── {book_id}/
│       └── page_*.png
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_semantic_chunker.py
│   │   ├── test_embedding_generator.py
│   │   └── test_vector_search.py
│   ├── integration/
│   │   ├── test_ingestion_pipeline.py
│   │   ├── test_database_repository.py
│   │   └── test_api_endpoints.py
│   └── fixtures/
│       ├── sample_screenshot.png
│       └── extracted_text.txt
├── minerva/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py                        # FastAPI app
│   ├── version.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── search.py
│   │   │   ├── books.py
│   │   │   └── chunks.py
│   │   └── schemas/
│   │       ├── search.py
│   │       ├── books.py
│   │       └── common.py
│   ├── cli/
│   │   └── app.py
│   ├── core/
│   │   ├── ingestion/
│   │   │   ├── pipeline.py
│   │   │   ├── kindle_automation.py
│   │   │   ├── text_extraction.py
│   │   │   ├── semantic_chunking.py
│   │   │   ├── embedding_generator.py
│   │   │   └── metadata_extractor.py    # Phase 1.5 - Optional metadata enrichment
│   │   ├── search/
│   │   │   └── vector_search.py
│   │   └── export/
│   │       └── export_service.py
│   ├── db/
│   │   ├── session.py
│   │   ├── models/
│   │   │   ├── book.py
│   │   │   ├── screenshot.py
│   │   │   ├── chunk.py
│   │   │   ├── embedding_config.py
│   │   │   └── ingestion_log.py
│   │   └── repositories/
│   │       ├── book_repository.py
│   │       ├── screenshot_repository.py
│   │       ├── chunk_repository.py
│   │       └── base_repository.py
│   └── utils/
│       ├── logging.py
│       ├── exceptions.py
│       ├── openai_client.py
│       ├── token_counter.py
│       ├── retry.py
│       └── quality_validation.py
├── scripts/
│   ├── setup_local_db.sh
│   ├── reset_db.sh
│   └── run_migrations.sh
├── .env.example
├── .env                               # Local config (gitignored)
├── .gitignore
├── .python-version
├── pyproject.toml
├── poetry.lock
├── alembic.ini
├── mypy.ini
├── pytest.ini
├── .ruff.toml
├── Dockerfile
├── docker-compose.yml
├── README.md
└── LICENSE
```

---
