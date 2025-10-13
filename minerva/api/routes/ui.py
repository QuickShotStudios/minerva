"""UI routes for local development (search interface)."""

from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

from minerva.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="", tags=["ui"])

# Path to HTML template
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SEARCH_TEMPLATE = TEMPLATES_DIR / "search.html"


@router.get(
    "/search-ui",
    response_class=HTMLResponse,
    summary="Development search UI",
    description="Simple search interface for local testing (only available in development)",
    include_in_schema=settings.environment == "development",
)
async def search_ui() -> HTMLResponse:
    """
    Serve a simple search UI for local development.

    Only accessible when ENVIRONMENT=development or APP_ENV=local.
    Returns 404 in production environments for security.

    Returns:
        HTMLResponse with embedded search interface
    """
    # Security check: only allow in development
    if settings.environment != "development":
        logger.warning(
            "search_ui_access_denied",
            environment=settings.environment,
            message="UI endpoint accessed in non-development environment",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    # Check if template exists
    if not SEARCH_TEMPLATE.exists():
        logger.error(
            "search_template_missing",
            template_path=str(SEARCH_TEMPLATE),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search template not found",
        )

    # Read and return HTML template
    try:
        html_content = SEARCH_TEMPLATE.read_text(encoding="utf-8")
        logger.info("search_ui_served")
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(
            "search_template_read_error",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load search template",
        ) from e
