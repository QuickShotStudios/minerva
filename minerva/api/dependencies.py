"""FastAPI dependencies for route handlers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from minerva.db.session import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide async database session to route handlers.

    This dependency function provides an async database session with automatic
    cleanup and transaction management (commit on success, rollback on error).

    Yields:
        AsyncSession: Database session for the request

    Usage:
        ```python
        @router.get("/books")
        async def get_books(db: AsyncSession = Depends(get_db)):
            # Use db here
            pass
        ```
    """
    async for session in get_session():
        yield session
