# Security

## Input Validation

**Validation Library:** Pydantic (built into FastAPI and SQLModel)

**Validation Location:** API boundary, CLI input parsing, database models

**Required Rules:**
1. All external inputs MUST be validated
2. Validation at API boundary before processing
3. Whitelist approach preferred over blacklist

**SQL Injection Prevention:**
- All queries use parameterized queries (SQLAlchemy/asyncpg)
- Never construct SQL with string concatenation

## Authentication & Authorization

**Auth Method:** None for MVP (localhost only, single user)

**Future (Phase 2):** API key authentication for production access

## Secrets Management

**Development:** `.env` file (gitignored) + python-dotenv

**Production:** Railway/Fly.io environment variables

**Code Requirements:**
- ❌ NEVER hardcode secrets
- ✅ Access via `settings` only
- ❌ No secrets in logs or error messages

**Secret Rotation:**
- OpenAI API key: Rotate via dashboard, update environment variable
- Database password: Update in platform, update environment variable

## API Security

**Rate Limiting:** Not implemented for MVP

**CORS Policy:** Configured with specific origins (MyPeptidePal.ai)

**Security Headers:**
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000

**HTTPS Enforcement:**
- Development: HTTP acceptable (localhost)
- Production: HTTPS only (platform provides SSL)

## Data Protection

**Encryption at Rest:**
- Local: Filesystem encryption (macOS FileVault)
- Production: Supabase/Neon automatic encryption (AES-256)

**Encryption in Transit:**
- API Communication: HTTPS (TLS 1.3)
- Database Connection: SSL/TLS required for production
- OpenAI API: HTTPS (SDK enforces)

**PII Handling:**
- No PII collected (single user, no accounts)
- Amazon credentials: Never stored, only session cookies (local only)

**Screenshot Security:**
- Stored locally only (never uploaded to cloud)
- Not included in exports
- File permissions: 644

## Dependency Security

**Scanning Tool:** GitHub Dependabot (automatic)

**Update Policy:**
- Critical vulnerabilities: Update immediately
- High vulnerabilities: Update within 7 days
- Medium/Low: Update during regular maintenance

**Dependency Pinning:** Pin major versions in pyproject.toml, allow minor/patch updates

---
