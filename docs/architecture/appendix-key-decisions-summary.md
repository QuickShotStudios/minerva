# Appendix: Key Decisions Summary

**Architectural Decisions:**
1. Two-environment deployment (local ingestion + production API)
2. Modular monolith with clear component boundaries
3. Manual export workflow for security and control
4. Async-first design throughout
5. Repository pattern for data access

**Technology Decisions:**
1. Python 3.11+ with FastAPI and SQLModel
2. PostgreSQL 15+ with pgvector for vector search
3. Playwright for browser automation
4. OpenAI gpt-4o-mini for vision, text-embedding-3-small for embeddings
5. Poetry for dependency management

**Security Decisions:**
1. No authentication for MVP (localhost + trusted network)
2. Environment variables for all secrets
3. Screenshots never leave local machine
4. HTTPS enforcement in production
5. CORS restricted to MyPeptidePal.ai

**Testing Decisions:**
1. 80%+ unit test coverage for core logic
2. Integration tests with test database
3. Manual E2E validation (no automated Kindle testing)
4. GitHub Actions CI/CD pipeline

**Deployment Decisions:**
1. Railway/Fly.io for production API hosting
2. Supabase/Neon for managed PostgreSQL
3. Docker for containerized production deployment
4. Git-based rollback strategy

---

_Architecture Document Version 1.1 - Updated 2025-10-06 by Winston (Architect)_
