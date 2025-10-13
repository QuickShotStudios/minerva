"""Health check endpoint for monitoring and deployment verification."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.api.dependencies import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:  # noqa: B008
    """
    Health check endpoint that verifies API and database connectivity.

    Returns:
        dict: Health status including database connection state and API version

    Raises:
        HTTPException: 503 if database is unavailable
    """
    try:
        # Verify database connectivity
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "version": "1.0.0"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database unavailable") from e
