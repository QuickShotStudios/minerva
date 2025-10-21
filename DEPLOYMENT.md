# Minerva Deployment Guide - Fly.io

Complete guide for deploying the Minerva API to Fly.io.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Database Setup](#database-setup)
- [Secrets Configuration](#secrets-configuration)
- [First Deployment](#first-deployment)
- [Verification](#verification)
- [Managing Your App](#managing-your-app)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Scaling](#scaling)
- [Cost Estimates](#cost-estimates)

## Prerequisites

Before deploying, ensure you have:

1. **Fly.io Account**
   - Sign up at https://fly.io/app/sign-up
   - Credit card required (generous free tier available)

2. **flyctl CLI**
   ```bash
   # macOS
   brew install flyctl

   # Linux
   curl -L https://fly.io/install.sh | sh

   # Windows
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

3. **OpenAI API Key**
   - Get from https://platform.openai.com/api-keys
   - Needed for generating embeddings during search

4. **Exported Book Data**
   - At least one book exported from local ingestion
   - See main README.md for export instructions

## Initial Setup

### 1. Install flyctl and Authenticate

```bash
# Install flyctl (see Prerequisites above)

# Authenticate with Fly.io
flyctl auth login

# Verify authentication
flyctl auth whoami
```

### 2. Customize fly.toml

Edit `fly.toml` and update:

```toml
app = "minerva-api"  # Change to your unique app name
primary_region = "ord"  # Change to your preferred region
```

**Available regions:**
- `ord` - Chicago, Illinois (US)
- `iad` - Ashburn, Virginia (US)
- `sjc` - San Jose, California (US)
- `lhr` - London (UK)
- `ams` - Amsterdam (NL)
- `fra` - Frankfurt (DE)
- `syd` - Sydney (AU)
- Full list: https://fly.io/docs/reference/regions/

## Database Setup

### Option 1: Fly Postgres (Recommended)

Create a managed PostgreSQL database on Fly.io:

```bash
# Create Postgres cluster
flyctl postgres create

# Follow the prompts:
# - App name: minerva-db (or your choice)
# - Region: same as your app (e.g., ord)
# - Configuration: Development (smallest, free tier)
# - Scale to zero: Yes (recommended for cost savings)

# Note the connection string shown after creation:
# postgres://postgres:<password>@minerva-db.internal:5432/minerva
```

**Enable pgvector extension:**

```bash
# Connect to the database
flyctl postgres connect -a minerva-db

# In the psql prompt:
CREATE EXTENSION IF NOT EXISTS vector;

# Verify installation
\dx vector

# Exit psql
\q
```

**Attach database to your app:**

```bash
# This creates a DATABASE_URL secret automatically
flyctl postgres attach minerva-db -a minerva-api
```

### Option 2: External Database

If using an external PostgreSQL database (e.g., Supabase, AWS RDS):

1. Ensure pgvector extension is installed
2. Get the connection string in format:
   ```
   postgresql+asyncpg://user:password@host:port/database
   ```
3. Set the DATABASE_URL secret manually (see Secrets Configuration below)

## Secrets Configuration

### Generate API Key

First, generate a secure API key to protect your API from unauthorized access:

```bash
# Generate a secure random API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Example output:
# xJ4kP9mR7nQ2vL8fW3bN6cT1yH5sD0gA4eK7jM9pU2xV8zB6
```

**Save this key securely** - you'll need to:
1. Set it as a Fly.io secret (below)
2. Configure your frontend to send it in requests
3. **Never commit it to git**

### Set Required Secrets

Configure all required secrets for your application:

```bash
# REQUIRED: Set API key for authentication
flyctl secrets set API_KEY=<your-generated-key> -a minerva-api

# REQUIRED: Set OpenAI API key
flyctl secrets set OPENAI_API_KEY=sk-proj-... -a minerva-api

# REQUIRED: Set CORS origins (comma-separated list)
flyctl secrets set CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com -a minerva-api

# If using external database (skip if you attached Fly Postgres):
flyctl secrets set DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db -a minerva-api

# Verify secrets are set (values are hidden)
flyctl secrets list -a minerva-api
```

**Important:**
- Never commit secrets to git
- The secrets are encrypted and stored securely on Fly.io
- Your API key protects against unauthorized usage and OpenAI cost abuse

### Optional: Disable Authentication (Not Recommended)

If you want to disable API key authentication (NOT recommended for production):

```bash
flyctl secrets set REQUIRE_API_KEY=false -a minerva-api
```

## First Deployment

### 1. Deploy the Application

```bash
# Deploy from project root
flyctl deploy

# This will:
# 1. Build the Docker image
# 2. Push to Fly.io registry
# 3. Run database migrations (release_command)
# 4. Start the application
# 5. Wait for health checks to pass
```

### 2. Import Your Book Data

After deployment, you need to import your exported book data:

```bash
# If using Fly Postgres, create a proxy connection:
flyctl proxy 5432 -a minerva-db

# In a new terminal, import your data:
psql "postgresql://postgres:<password>@localhost:5432/minerva" -f exports/book_<uuid>.sql

# Close the proxy when done (Ctrl+C in first terminal)
```

**For external databases:**
```bash
# Import directly to your database
psql $DATABASE_URL -f exports/book_<uuid>.sql
```

## Verification

### 1. Check Application Health

```bash
# Open your app in browser
flyctl open -a minerva-api

# Should redirect to /health endpoint
# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "timestamp": "2024-10-21T..."
# }
```

### 2. Test the API

```bash
# Get your app URL
APP_URL=$(flyctl info -a minerva-api | grep Hostname | awk '{print $2}')

# Test health endpoint (public - no API key required)
curl https://$APP_URL/health

# Test API docs (public - no API key required)
open https://$APP_URL/docs

# Test semantic search (requires API key)
curl -X POST https://$APP_URL/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{
    "query": "peptides for muscle growth",
    "top_k": 5,
    "similarity_threshold": 0.5
  }'
```

**Important:** All `/api/v1/*` endpoints require the `X-API-Key` header with your API key.

**Frontend Integration Example:**

```javascript
// JavaScript/TypeScript
const response = await fetch('https://minerva-api.fly.dev/api/v1/search/semantic', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': process.env.NEXT_PUBLIC_MINERVA_API_KEY, // Store in environment variable
  },
  body: JSON.stringify({
    query: 'peptides for muscle growth',
    top_k: 5,
    similarity_threshold: 0.5,
  }),
});

const data = await response.json();
```

```python
# Python
import os
import httpx

response = httpx.post(
    "https://minerva-api.fly.dev/api/v1/search/semantic",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": os.getenv("MINERVA_API_KEY"),  # Store in environment variable
    },
    json={
        "query": "peptides for muscle growth",
        "top_k": 5,
        "similarity_threshold": 0.5,
    },
)

data = response.json()
```

### 3. View Logs

```bash
# Stream live logs
flyctl logs -a minerva-api

# View specific number of lines
flyctl logs -a minerva-api --lines 100
```

## Managing Your App

### View App Status

```bash
# Get app information
flyctl info -a minerva-api

# View app status
flyctl status -a minerva-api

# List all apps
flyctl apps list

# View machine status
flyctl machine list -a minerva-api
```

### Update Secrets

```bash
# Update a secret
flyctl secrets set OPENAI_API_KEY=sk-new-key -a minerva-api

# Remove a secret
flyctl secrets unset SECRET_NAME -a minerva-api

# List secrets (values hidden)
flyctl secrets list -a minerva-api
```

### Deploy Updates

```bash
# After making code changes, deploy again
git add .
git commit -m "Update API"
flyctl deploy
```

### Rollback Deployment

```bash
# List releases
flyctl releases -a minerva-api

# Rollback to previous version
flyctl releases rollback -a minerva-api
```

## Monitoring & Troubleshooting

### View Logs

```bash
# Real-time logs
flyctl logs -a minerva-api

# Filter logs
flyctl logs -a minerva-api | grep ERROR

# Export logs
flyctl logs -a minerva-api > logs.txt
```

### Check Database Connection

```bash
# Connect to Postgres console
flyctl postgres connect -a minerva-db

# Check book count
SELECT COUNT(*) FROM books;

# Check chunk count
SELECT COUNT(*) FROM chunks;

# Check embeddings
SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;
```

### Performance Monitoring

```bash
# View metrics dashboard
flyctl dashboard -a minerva-api

# View resource usage
flyctl status -a minerva-api

# View machine metrics
flyctl machine status <machine-id> -a minerva-api
```

### Common Issues

**1. Health check failures**
```bash
# Check logs for errors
flyctl logs -a minerva-api

# Verify database connection
flyctl secrets list -a minerva-api  # Check DATABASE_URL exists

# SSH into machine for debugging
flyctl ssh console -a minerva-api
```

**2. Database connection errors**
```bash
# Verify pgvector extension
flyctl postgres connect -a minerva-db
\dx vector

# Check database connectivity
flyctl postgres db list -a minerva-db
```

**3. Out of memory errors**
```bash
# Scale VM memory
flyctl scale memory 2048 -a minerva-api  # 2GB

# Check current resources
flyctl scale show -a minerva-api
```

**4. Slow responses**
```bash
# Check database indexes
flyctl postgres connect -a minerva-db
\d+ chunks  # View indexes

# Scale VM if needed
flyctl scale vm shared-cpu-2x -a minerva-api
```

## Scaling

### Scale to Zero (Cost Optimization)

Your app is configured to scale to zero when idle:

```toml
[http_service]
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
```

**How it works:**
- App stops after 5 minutes of inactivity
- Automatically starts on first request (adds ~1-2s latency)
- Ideal for development/low-traffic APIs

### Always-On (Production)

For production with consistent traffic:

```bash
# Set minimum machines to 1
flyctl scale count 1 -a minerva-api

# Or update fly.toml:
# min_machines_running = 1
```

### Increase Resources

```bash
# Scale memory
flyctl scale memory 1024 -a minerva-api  # 1GB
flyctl scale memory 2048 -a minerva-api  # 2GB
flyctl scale memory 4096 -a minerva-api  # 4GB

# Scale VM type
flyctl scale vm shared-cpu-1x -a minerva-api  # 1 CPU (default)
flyctl scale vm shared-cpu-2x -a minerva-api  # 2 CPUs
flyctl scale vm shared-cpu-4x -a minerva-api  # 4 CPUs

# View current scale
flyctl scale show -a minerva-api
```

### Database Scaling

```bash
# Scale Postgres resources
flyctl postgres update -a minerva-db

# Follow prompts to change:
# - VM size
# - Disk size
# - High availability (add replicas)
```

## Cost Estimates

### Free Tier (Hobby)

Fly.io provides generous free allowances:
- Up to 3 shared-cpu-1x VMs (256MB RAM)
- 3GB persistent storage
- 160GB outbound data transfer

**Typical Minerva API cost on free tier:**
- API app: Free (1 VM, 512MB-1GB RAM, scales to zero)
- Postgres: Free (Development config)
- Total: **$0/month** for low-traffic usage

### Paid (Production)

**Example production setup:**
- API: 1x shared-cpu-1x with 1GB RAM = ~$5/month
- Postgres: 1x shared-cpu-1x with 10GB storage = ~$15/month
- Outbound data: ~$0.02/GB beyond free tier
- **Total: ~$20-25/month** for moderate traffic

**Cost optimization tips:**
1. Use scale-to-zero for development
2. Start small and scale up as needed
3. Monitor usage via `flyctl dashboard`
4. Use external database if you have one
5. Enable request caching if applicable

View your usage:
```bash
flyctl dashboard -a minerva-api
```

## Additional Resources

- **Fly.io Documentation:** https://fly.io/docs/
- **Fly.io Pricing:** https://fly.io/docs/about/pricing/
- **Fly.io Postgres:** https://fly.io/docs/postgres/
- **Fly.io Status:** https://status.flyio.net/

## Support

If you encounter issues:

1. Check logs: `flyctl logs -a minerva-api`
2. Review Fly.io community forum: https://community.fly.io/
3. Fly.io support: https://fly.io/docs/about/support/
4. Minerva issues: GitHub issues (your repository)

---

**Next Steps:**
1. Complete initial deployment
2. Import your book data
3. Test the API thoroughly
4. Configure your frontend to use the API URL
5. Monitor performance and scale as needed
