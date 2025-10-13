# Coding Standards

These standards are **MANDATORY** for all AI agents and human developers.

## Core Standards

**Languages & Runtimes:**
- Python 3.11+ (exactly, not 3.12+)
- All code must have type hints (enforced by mypy)
- Use `async/await` for all I/O operations

**Style & Linting:**
- Formatter: black (line length: 88)
- Linter: ruff
- Type Checker: mypy (strict mode)

## Critical Rules

1. **Never Access Environment Variables Directly** - Use `from minerva.config import settings`
2. **All Database Operations Must Use Repository Pattern** - No direct session.execute() in business logic
3. **All I/O Operations Must Be Async** - No requests, psycopg2, or sync file operations
4. **Never Use `print()` for Logging** - Use structlog
5. **All External API Calls Must Have Timeouts** - Prevent hanging operations
6. **UUIDs Must Be Stored as Strings in APIs** - JSON serialization compatibility
7. **All SQLModel Classes Must Inherit from SQLModel** - Single model for DB and API
8. **Never Commit Secrets or API Keys** - Use .env files (gitignored)
9. **All Retry Logic Must Have Max Attempts** - Prevent infinite loops
10. **Database Sessions Must Use Context Managers** - Automatic cleanup
11. **All Error Logs Must Include Context** - book_id, screenshot_id, etc.
12. **OpenAI API Calls Must Track Token Usage** - Budget tracking
13. **File Paths Must Use pathlib.Path** - Cross-platform compatibility
14. **All Public Functions Must Have Type Hints and Docstrings** - Documentation
15. **Screenshot File Paths Must Never Be Exported** - Security and legal compliance

---
