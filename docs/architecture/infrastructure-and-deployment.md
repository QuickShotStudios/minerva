# Infrastructure and Deployment

## Deployment Strategy

**Local Environment (Ingestion):**
- Deployment Method: Direct installation on developer machine
- Dependencies: Full stack (Playwright + Chromium, all Python packages)
- Database: Local PostgreSQL 15+ with pgvector
- Access: CLI only (`minerva` command)
- Updates: `git pull && poetry install && alembic upgrade head`

**Production Environment (API):**
- Deployment Method: Containerized deployment (Docker)
- Platform: Railway.app (recommended) or Fly.io
- CI/CD Platform: GitHub Actions
- Deployment Trigger: Push to `main` branch (automatic)
- Database: External managed PostgreSQL (Supabase/Neon)
- Health Checks: `/health` endpoint for platform monitoring

## Environments

| Environment | Purpose | Backend URL | Database |
|-------------|---------|-------------|----------|
| Development | Local dev, ingestion testing | http://localhost:8000 | Local PostgreSQL |
| Production | Live API serving queries | https://minerva-api.railway.app | Supabase/Neon |

## Rollback Strategy

**Primary Method:** Git-based rollback

**Rollback Procedure:**
1. Identify last known good commit
2. Revert to stable version: `git revert <commit-hash>`
3. Push revert: `git push origin main`
4. GitHub Actions automatically deploys previous version
5. Verify health: `curl https://minerva-api.railway.app/health`

**Recovery Time Objective (RTO):** 5 minutes

---
