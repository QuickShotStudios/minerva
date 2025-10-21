# Minerva API Security Guide

Comprehensive guide to securing your Minerva API deployment.

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Generating API Keys](#generating-api-keys)
- [Using API Keys](#using-api-keys)
- [Security Best Practices](#security-best-practices)
- [Configuration Options](#configuration-options)
- [Protected Endpoints](#protected-endpoints)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)

## Overview

Minerva API implements **API Key Authentication** to protect your API from unauthorized access and prevent abuse of your OpenAI API credits. Since each semantic search request generates embeddings via the OpenAI API (which has associated costs), authentication is critical for production deployments.

### Why Authentication Matters

Without authentication, anyone who discovers your API URL can:
- Make unlimited search requests, draining your OpenAI credits
- Access your knowledge base data
- Potentially overwhelm your server with requests
- Cannot be blocked or rate-limited

**Security Layers:**
1. **CORS** - Limits browser-based access to allowed origins
2. **API Key Authentication** - Validates all API requests
3. **HTTPS** - Encrypted communication (automatic on Fly.io)
4. **Request Logging** - Tracks all access attempts

## Authentication

### How It Works

1. **Client Request** - Client includes API key in `X-API-Key` header
2. **Validation** - Server validates key using constant-time comparison
3. **Access Granted/Denied** - Valid key grants access; invalid returns 401

**Authentication Flow:**
```
Client Request
    │
    ├─ Header: X-API-Key: <your-api-key>
    │
    ▼
Server Validation
    │
    ├─ Compare with configured API_KEY
    │
    ├─ Valid? ──> Process Request ──> Return 200 + Data
    │
    └─ Invalid? ──> Reject ──> Return 401 Unauthorized
```

### Security Features

- **Constant-Time Comparison** - Prevents timing attacks
- **Secure Storage** - Keys stored as secrets (never in code)
- **Request Logging** - Failed auth attempts logged with request ID
- **No Token Expiry** - Simple static key (rotate manually)

## Generating API Keys

### Production Key Generation

Use Python's `secrets` module for cryptographically secure keys:

```bash
# Generate a secure 256-bit key (recommended)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Example output:
# xJ4kP9mR7nQ2vL8fW3bN6cT1yH5sD0gA4eK7jM9pU2xV8zB6
```

**Best Practices:**
- Use at least 32 bytes (256 bits) of entropy
- Never reuse keys across environments
- Store keys in secure password manager
- Rotate keys periodically (every 90-180 days)

### Environment-Specific Keys

Use different keys for each environment:

```bash
# Development
API_KEY=dev-key-xJ4kP9mR7nQ2vL8fW3bN6cT1yH5sD0gA

# Staging
API_KEY=staging-key-xJ4kP9mR7nQ2vL8fW3bN6cT1yH5sD0gA

# Production
API_KEY=prod-key-xJ4kP9mR7nQ2vL8fW3bN6cT1yH5sD0gA
```

## Using API Keys

### Client Integration

#### JavaScript/TypeScript

```javascript
// Recommended: Store in environment variable
const API_KEY = process.env.NEXT_PUBLIC_MINERVA_API_KEY;
const API_URL = 'https://minerva-api.fly.dev/api/v1';

async function searchKnowledgeBase(query) {
  const response = await fetch(`${API_URL}/search/semantic`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify({
      query: query,
      top_k: 10,
      similarity_threshold: 0.5,
    }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Invalid API key');
    }
    throw new Error(`API error: ${response.status}`);
  }

  return await response.json();
}

// Usage
try {
  const results = await searchKnowledgeBase('peptides for muscle growth');
  console.log(results);
} catch (error) {
  console.error('Search failed:', error);
}
```

#### Python

```python
import os
import httpx

API_KEY = os.getenv('MINERVA_API_KEY')
API_URL = 'https://minerva-api.fly.dev/api/v1'

def search_knowledge_base(query: str, top_k: int = 10):
    """Search Minerva knowledge base with API key authentication."""
    response = httpx.post(
        f"{API_URL}/search/semantic",
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY,
        },
        json={
            'query': query,
            'top_k': top_k,
            'similarity_threshold': 0.5,
        },
    )

    if response.status_code == 401:
        raise ValueError('Invalid API key')

    response.raise_for_status()
    return response.json()

# Usage
try:
    results = search_knowledge_base('peptides for muscle growth')
    print(results)
except Exception as e:
    print(f'Search failed: {e}')
```

#### cURL

```bash
# Set your API key
export MINERVA_API_KEY="your-api-key-here"

# Make authenticated request
curl -X POST https://minerva-api.fly.dev/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $MINERVA_API_KEY" \
  -d '{
    "query": "peptides for muscle growth",
    "top_k": 10,
    "similarity_threshold": 0.5
  }'
```

### Frontend Environment Variables

#### Next.js

```bash
# .env.local
NEXT_PUBLIC_MINERVA_API_KEY=your-api-key-here
NEXT_PUBLIC_MINERVA_API_URL=https://minerva-api.fly.dev
```

#### React/Vite

```bash
# .env
VITE_MINERVA_API_KEY=your-api-key-here
VITE_MINERVA_API_URL=https://minerva-api.fly.dev
```

**Important:** Never hardcode API keys in source code. Always use environment variables.

## Security Best Practices

### 1. Key Management

✅ **Do:**
- Store keys in environment variables
- Use password managers for key storage
- Rotate keys every 90-180 days
- Use different keys per environment
- Revoke compromised keys immediately

❌ **Don't:**
- Hardcode keys in source code
- Commit keys to version control
- Share keys via email or chat
- Reuse keys across projects
- Log full keys in application logs

### 2. Deployment Security

**Production Checklist:**
- [ ] `ENVIRONMENT=production` set
- [ ] `REQUIRE_API_KEY=true` enabled
- [ ] Strong API key generated (32+ bytes)
- [ ] API key stored as Fly.io secret
- [ ] CORS configured with allowed origins only
- [ ] HTTPS enabled (automatic on Fly.io)
- [ ] Request logging enabled

**Fly.io Secrets Setup:**
```bash
# Set secrets securely
flyctl secrets set API_KEY=<your-key> -a minerva-api
flyctl secrets set OPENAI_API_KEY=<openai-key> -a minerva-api
flyctl secrets set CORS_ALLOWED_ORIGINS=https://yourdomain.com -a minerva-api

# Verify (values are hidden)
flyctl secrets list -a minerva-api
```

### 3. Frontend Security

**Never expose API keys in:**
- Client-side JavaScript (browser DevTools can read them)
- Public repositories
- Client-side environment variables (e.g., `NEXT_PUBLIC_*`)

**Recommended Architecture:**

```
Frontend (Browser)
    │
    ├─ User Authentication (Auth0, Clerk, etc.)
    │
    ▼
Backend API (Next.js API Routes, Express, etc.)
    │
    ├─ Validates user session
    ├─ Adds X-API-Key header (server-side only)
    │
    ▼
Minerva API
    │
    ├─ Validates API key
    │
    ▼
Returns search results
```

**Next.js API Route Example:**
```typescript
// pages/api/search.ts
import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Validate user is authenticated (your auth logic)
  const session = await getSession(req);
  if (!session) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  // Forward request to Minerva with API key (server-side only)
  const response = await fetch(
    `${process.env.MINERVA_API_URL}/api/v1/search/semantic`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.MINERVA_API_KEY!, // Server-side env var
      },
      body: JSON.stringify(req.body),
    }
  );

  const data = await response.json();
  res.status(response.status).json(data);
}
```

### 4. Key Rotation

**When to rotate:**
- Every 90-180 days (routine)
- When employee with access leaves
- When key may have been compromised
- After security incident

**How to rotate:**
```bash
# 1. Generate new key
NEW_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Update Fly.io secret
flyctl secrets set API_KEY=$NEW_KEY -a minerva-api

# 3. Update frontend environment variables
# (update .env, redeploy frontend)

# 4. Monitor logs for 401 errors (old key usage)
flyctl logs -a minerva-api | grep "api_key_invalid"

# 5. After grace period, old key is fully rotated
```

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Yes (prod) | `None` | Primary API key for authentication |
| `REQUIRE_API_KEY` | No | `true` | Enable/disable authentication |
| `ENVIRONMENT` | No | `development` | Environment (development/production) |
| `CORS_ALLOWED_ORIGINS` | Yes | `http://localhost:3000` | Comma-separated allowed origins |

### Configuration Examples

**Development (No Auth):**
```bash
ENVIRONMENT=development
REQUIRE_API_KEY=false
API_KEY=  # Optional
```

**Development (With Auth):**
```bash
ENVIRONMENT=development
REQUIRE_API_KEY=true
API_KEY=dev-test-key
```

**Production:**
```bash
ENVIRONMENT=production
REQUIRE_API_KEY=true  # Enforced
API_KEY=prod-xJ4kP9mR7nQ2vL8fW3bN6cT1yH5sD0gA  # Required
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Validation Rules

The API enforces these rules at startup:

1. **Production + REQUIRE_API_KEY=true** → `API_KEY` must be set
2. **Production + No API_KEY** → Startup fails with error
3. **Development + No API_KEY** → Allowed if `REQUIRE_API_KEY=false`

## Protected Endpoints

### Authentication Required

All `/api/v1/*` endpoints require authentication:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search/semantic` | POST | Semantic search |
| `/api/v1/books` | GET | List books |
| `/api/v1/books/{id}` | GET | Get book details |
| `/api/v1/chunks/{id}` | GET | Get chunk details |

### Public Endpoints (No Auth)

These endpoints are always public:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | API documentation (Swagger UI) |
| `/redoc` | GET | API documentation (ReDoc) |
| `/openapi.json` | GET | OpenAPI schema |

## Monitoring & Logging

### Security Logs

The API logs all authentication events:

**Successful Authentication:**
```json
{
  "event": "api_key_valid",
  "level": "debug",
  "request_id": "abc123..."
}
```

**Failed Authentication:**
```json
{
  "event": "api_key_invalid",
  "level": "warning",
  "provided_key_prefix": "wrong-ke...",
  "request_id": "abc123..."
}
```

**Authentication Disabled:**
```json
{
  "event": "api_key_check_skipped",
  "level": "debug",
  "reason": "authentication_disabled"
}
```

### Monitoring Commands

```bash
# View all logs
flyctl logs -a minerva-api

# Filter for auth failures
flyctl logs -a minerva-api | grep "api_key_invalid"

# Filter for specific request
flyctl logs -a minerva-api | grep "abc123..."

# Real-time monitoring
flyctl logs -a minerva-api --follow
```

### Metrics to Monitor

1. **401 Unauthorized Rate** - Spike may indicate attack or key rotation issues
2. **Unique Request IDs** - Track individual request chains
3. **Failed Auth Attempts** - Persistent failures may indicate leaked old key
4. **Geographic Distribution** - Unexpected locations may indicate compromise

## Troubleshooting

### Common Issues

#### 1. 401 Unauthorized Error

**Symptoms:**
```json
{
  "detail": "Invalid API key"
}
```

**Solutions:**
```bash
# Check if API_KEY secret is set
flyctl secrets list -a minerva-api

# Verify key matches what your client is sending
# (check frontend environment variables)

# Regenerate and set new key
flyctl secrets set API_KEY=<new-key> -a minerva-api
```

#### 2. Missing X-API-Key Header

**Symptoms:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "x-api-key"],
      "msg": "Field required"
    }
  ]
}
```

**Solutions:**
- Ensure `X-API-Key` header is included in request
- Check header name (case-insensitive but must be `X-API-Key`)
- Verify client code is sending headers correctly

#### 3. API Key Not Configured (500 Error)

**Symptoms:**
```json
{
  "detail": "API authentication is not properly configured"
}
```

**Solutions:**
```bash
# Set API_KEY secret
flyctl secrets set API_KEY=<your-key> -a minerva-api

# Or disable authentication (not recommended)
flyctl secrets set REQUIRE_API_KEY=false -a minerva-api
```

#### 4. CORS + Auth Issues

**Symptoms:**
- Browser shows CORS error
- Network tab shows OPTIONS request failing

**Solutions:**
```bash
# Ensure your frontend domain is in CORS_ALLOWED_ORIGINS
flyctl secrets set CORS_ALLOWED_ORIGINS=https://yourdomain.com -a minerva-api

# Verify headers are sent in actual request (not preflight)
# Preflight (OPTIONS) doesn't require X-API-Key
```

### Debug Mode

Enable debug logging to troubleshoot:

```bash
# Set log level to DEBUG
flyctl secrets set LOG_LEVEL=DEBUG -a minerva-api

# View detailed logs
flyctl logs -a minerva-api
```

## Advanced Topics

### Multiple API Keys (Future Enhancement)

Current implementation supports single API key. For multiple keys:

**Option 1: Multiple Deployments**
- Deploy separate instances for different clients
- Each with its own API_KEY

**Option 2: Custom Implementation**
```python
# Example: Extend security.py for multiple keys
API_KEYS = os.getenv('API_KEYS', '').split(',')

if x_api_key not in API_KEYS:
    raise HTTPException(status_code=401)
```

### Rate Limiting (Future Enhancement)

Not currently implemented. Can be added via:

**Option 1: Fly.io Proxy**
```toml
# fly.toml
[http_service]
  rate_limit = { requests = 100, period = "1m" }
```

**Option 2: Application-Level**
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_api_key)

@limiter.limit("100/minute")
async def semantic_search(...):
    ...
```

### IP Whitelisting

Restrict access by IP address:

```bash
# Fly.io Proxy configuration
flyctl ips list -a minerva-api
# Then use Fly.io network policies to restrict
```

## Security Disclosure

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email: security@yourdomain.com (replace with your email)
3. Include: Description, reproduction steps, impact assessment
4. Allow 90 days for response before public disclosure

## References

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Fly.io Security Best Practices](https://fly.io/docs/reference/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

**Last Updated:** 2024-10-21
**Version:** 1.0.0
