"""API route initialization and versioning."""

from fastapi import APIRouter

from minerva.api.routes import books, chunks, search

# API v1 router - all versioned endpoints go under /api/v1
api_v1_router = APIRouter(prefix="/api/v1")

# Register routes
api_v1_router.include_router(books.router)
api_v1_router.include_router(chunks.router)
api_v1_router.include_router(search.router)
