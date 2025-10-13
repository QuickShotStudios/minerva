# Test Strategy and Standards

## Testing Philosophy

**Approach:** Test-After Development with Strategic TDD

**Coverage Goals:**
- Unit tests: 80%+ coverage for core business logic
- Integration tests: All critical workflows
- E2E tests: Manual validation only (no automated E2E for Kindle)

**Test Pyramid:**
- Unit Tests (70%): Fast, reliable, catch most bugs
- Integration Tests (30%): Component interactions
- Manual E2E: Kindle automation validation

## Test Organization

**Unit Tests:**
- Framework: pytest 7.4+ with pytest-asyncio
- Location: `tests/unit/`
- Mocking: unittest.mock + pytest-mock
- Coverage: 80%+ for `minerva/core/` and `minerva/db/repositories/`

**Integration Tests:**
- Scope: Multi-component with real database, mocked external APIs
- Location: `tests/integration/`
- Infrastructure: PostgreSQL test database (created/destroyed per session)

**API Tests:**
- Framework: pytest with httpx.AsyncClient
- Scope: Full HTTP request/response cycle with test database

**E2E Tests:**
- Framework: Manual validation only
- Scope: Full workflows with real Kindle and OpenAI API
- Environment: Local development

## CI Integration

GitHub Actions on every push:
1. Lint: `ruff check .`
2. Format Check: `black --check .`
3. Type Check: `mypy minerva/`
4. Unit Tests: `pytest tests/unit -v --cov=minerva`
5. Integration Tests: `pytest tests/integration -v`

---
