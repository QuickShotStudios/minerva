"""FastAPI application for Minerva production API."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from minerva.api.middleware import RequestLoggingMiddleware
from minerva.api.routes import api_v1_router, health
from minerva.config import settings
from minerva.utils.logging import configure_logging
from minerva.version import __version__

# Import UI router for development mode
if settings.environment == "development":
    from minerva.api.routes import ui

# Configure logging based on environment
configure_logging(log_level=settings.log_level, environment=settings.environment)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    # Startup
    logger.info("application_startup", version=__version__)
    yield
    # Shutdown
    logger.info("application_shutdown")


# Initialize FastAPI application
app = FastAPI(
    title="Minerva API",
    description="Knowledge base query API for peptide research",
    version=__version__,
    lifespan=lifespan,
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)  # Health check (no version prefix)
app.include_router(api_v1_router)  # Versioned API endpoints

# Register UI router (development only)
if settings.environment == "development":
    app.include_router(ui.router)
    logger.info("ui_router_registered", message="Search UI available at /search-ui")


# Global error handlers
@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle database errors with appropriate logging and response."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("database_error", error=str(exc), request_id=request_id)
    return JSONResponse(status_code=500, content={"detail": "Database error occurred"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("unhandled_exception", error=str(exc), request_id=request_id)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
