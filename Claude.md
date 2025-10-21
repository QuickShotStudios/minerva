# Claude Code Session Notes

## Deployment Session - October 21, 2025

### Objective
Deploy Minerva API to production on Fly.io with Neon database

### Summary
Successfully deployed Minerva API to Fly.io at https://minerva-api.fly.dev with API key authentication and Neon serverless PostgreSQL backend.

## Key Decisions

### 1. Database Platform: Neon vs Fly Postgres
**Decision:** Use Neon serverless PostgreSQL instead of Fly Postgres

**Rationale:**
- Fly Postgres doesn't include pgvector extension by default
- Architecture documentation specified Neon for production
- Neon provides built-in pgvector support
- Serverless capabilities align with Fly.io auto-scaling

**Alternative Considered:**
- Fly Postgres with custom image (rejected: added complexity)

### 2. Security Implementation
**Decision:** Implement API key authentication before production deployment

**Rationale:**
- Protect production API from unauthorized access
- Prevent OpenAI API cost abuse
- Required for public API deployment
- Minimal implementation complexity

**Implementation:**
- X-API-Key header authentication
- Constant-time comparison for security
- Secrets managed via Fly.io environment
- Health endpoint remains public

### 3. Dockerfile Fix
**Decision:** Add `ENV PYTHONPATH=/app` to Dockerfile

**Rationale:**
- Alembic couldn't import minerva module during migrations
- Python module path not set in container environment
- Simple one-line fix vs restructuring package

## Technical Implementation

### Database Migration
```bash
# Export from local PostgreSQL
pg_dump --schema-only > /tmp/minerva_schema.sql
pg_dump -t embedding_configs --data-only > /tmp/minerva_embedding_configs.sql
pg_dump -t books -t chunks -t screenshots -t ingestion_logs --data-only > /tmp/minerva_data.sql

# Import to Neon (with ssl=require for asyncpg)
psql "postgresql://...?ssl=require" -f /tmp/minerva_schema.sql
psql "postgresql://...?ssl=require" -f /tmp/minerva_embedding_configs.sql
psql "postgresql://...?ssl=require" -f /tmp/minerva_data.sql
```

**Data Migrated:**
- 9 books
- 930 chunks with embeddings
- 1 embedding configuration
- All supporting metadata

### Fly.io Deployment
```bash
# Create app
flyctl apps create minerva-api --org quickshot-studios-llc

# Configure secrets
flyctl secrets set \
  API_KEY=0UASNDRS1cQyA99wALsilyi9rx1DflkYZJvFXL2FCfI \
  DATABASE_URL="postgresql+asyncpg://...?ssl=require" \
  OPENAI_API_KEY=sk-... \
  CORS_ALLOWED_ORIGINS='["https://minerva-api.fly.dev"]' \
  -a minerva-api

# Deploy with Dockerfile
flyctl deploy
```

**Configuration:**
- Region: Chicago (ord)
- Auto-scaling: 0-2 machines (scales to zero when idle)
- Health checks: /health every 15s
- Release command: alembic upgrade head

## Issues Encountered

### Issue 1: Fly Postgres Missing pgvector
**Error:** `extension "vector" is not available`

**Resolution:**
- Deleted Fly Postgres database
- Created Neon database
- Enabled pgvector extension
- Updated connection string

### Issue 2: Module Import Error During Migration
**Error:** `ModuleNotFoundError: No module named 'minerva'`

**Resolution:**
- Added `ENV PYTHONPATH=/app` to Dockerfile
- Ensures Python can find minerva package during alembic migrations

### Issue 3: SSL Parameter Mismatch
**Error:** `TypeError: connect() got an unexpected keyword argument 'sslmode'`

**Resolution:**
- Changed `?sslmode=require` to `?ssl=require`
- asyncpg uses different parameter name than psycopg2

## Production Verification

### Health Check
```bash
curl https://minerva-api.fly.dev/health
# Response: {"status":"healthy","database":"connected","version":"1.0.0"}
```

### Semantic Search
```bash
curl -X POST https://minerva-api.fly.dev/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 0UASNDRS1cQyA99wALsilyi9rx1DflkYZJvFXL2FCfI" \
  -d '{"query": "peptides for muscle growth", "top_k": 3, "similarity_threshold": 0.5}'
# Response: Successfully returned relevant chunks about peptides and muscle growth
```

### Books List
```bash
curl https://minerva-api.fly.dev/api/v1/books \
  -H "X-API-Key: 0UASNDRS1cQyA99wALsilyi9rx1DflkYZJvFXL2FCfI"
# Response: 9 books (8 completed, 1 failed)
```

## Files Modified

### Created
- `minerva/api/security.py` - API key authentication
- `docs/SECURITY.md` - Security documentation
- `Minerva_API.postman_collection.json` - API testing collection

### Modified
- `Dockerfile` - Added PYTHONPATH environment variable
- `README.md` - Added production deployment section
- `docs/stories/3.7.api-deployment.md` - Updated with completion details
- `minerva/config.py` - Added API key configuration
- `minerva/api/routes/*.py` - Added authentication to endpoints
- `minerva/api/schemas/books.py` - Made capture_date nullable
- `.env` - Added API key for local testing

## Production Credentials

**API URL:** https://minerva-api.fly.dev

**Documentation:** https://minerva-api.fly.dev/docs

**Production API Key:** Configured in Fly.io secrets (0UASNDRS1c...)

**Database:** Neon serverless PostgreSQL
- Host: ep-noisy-breeze-aefc11at-pooler.c-2.us-east-2.aws.neon.tech
- Database: neondb
- Connection: postgresql+asyncpg://neondb_owner@.../neondb?ssl=require

## Performance Metrics

- Docker image: 245 MB (optimized)
- Health check: <100ms response time
- Search queries: 1-2.5 seconds (including embedding generation)
- Auto-scaling: Scales to zero when idle (cost savings)
- Database: Neon serverless (usage-based pricing)

## Next Steps

1. Update Postman collection with production URL
2. Monitor OpenAI API usage
3. Monitor Fly.io costs
4. Consider implementing:
   - Rate limiting
   - Request caching
   - Analytics/metrics
   - Client SDK

## Lessons Learned

1. **Check platform capabilities early** - Discovered Fly Postgres limitation after setup
2. **Architecture docs are authoritative** - Neon was specified in original design
3. **PYTHONPATH matters in containers** - Module imports can fail without proper path
4. **SSL parameter names vary** - asyncpg uses different params than psycopg2
5. **Security first** - Adding auth before deployment was the right call

## Commands for Future Reference

### View logs
```bash
flyctl logs -a minerva-api
```

### Check app status
```bash
flyctl status -a minerva-api
```

### Monitor dashboard
```bash
flyctl dashboard -a minerva-api
```

### Scale machines
```bash
flyctl scale count 2 -a minerva-api
```

### Update secrets
```bash
flyctl secrets set KEY=value -a minerva-api
```

### Redeploy
```bash
flyctl deploy
```

## Success Criteria Met

- ✅ API deployed to public URL (https://minerva-api.fly.dev)
- ✅ SSL/TLS enabled (automatic via Fly.io)
- ✅ Health check passing
- ✅ Semantic search working with production data
- ✅ API key authentication implemented
- ✅ Database connected (Neon with pgvector)
- ✅ Auto-scaling configured
- ✅ Documentation updated
- ✅ 9 books with 930 chunks deployed

## Total Time
Approximately 2-3 hours including:
- Security implementation (API key auth)
- Database migration (Fly Postgres → Neon)
- Data export/import (9 books, 930 chunks)
- Deployment configuration
- Issue resolution
- Testing and verification
- Documentation updates
