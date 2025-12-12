"""API security and authentication dependencies."""

import secrets

import structlog
from fastapi import Header, HTTPException, status

from minerva.config import settings

logger = structlog.get_logger(__name__)


async def verify_api_key(x_api_key: str | None = Header(None, description="API key for authentication")) -> None:
    """
    Verify API key from request header.

    This dependency validates the API key provided in the X-API-Key header
    against the configured API_KEY in settings. If authentication is disabled
    (REQUIRE_API_KEY=false), this check is bypassed.

    Args:
        x_api_key: API key from X-API-Key header (optional if REQUIRE_API_KEY=false)

    Raises:
        HTTPException: 401 if API key is invalid or missing when required

    Usage:
        ```python
        @router.get("/protected")
        async def protected_route(api_key: None = Depends(verify_api_key)):
            return {"message": "Access granted"}
        ```
    """
    # Skip authentication if disabled (development mode)
    if not settings.require_api_key:
        logger.debug("api_key_check_skipped", reason="authentication_disabled")
        return

    # Check if API key is provided when required
    if not x_api_key:
        logger.warning("api_key_missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required. Provide it in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check if API key is configured
    if not settings.api_key:
        logger.error("api_key_not_configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API authentication is not properly configured",
        )

    # Get the expected key value
    expected_key = settings.api_key.get_secret_value()

    # Validate API key using constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(x_api_key, expected_key):
        logger.warning(
            "api_key_invalid",
            provided_key_prefix=x_api_key[:8] + "..." if len(x_api_key) > 8 else "***",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.debug("api_key_valid")


async def optional_api_key(x_api_key: str | None = Header(None, description="Optional API key")) -> str | None:
    """
    Optional API key verification for public endpoints.

    This dependency can be used for endpoints that support both authenticated
    and unauthenticated access. If a key is provided, it's validated. If not,
    the request proceeds without authentication.

    Args:
        x_api_key: Optional API key from X-API-Key header

    Returns:
        The validated API key or None if not provided

    Raises:
        HTTPException: 401 if API key is provided but invalid
    """
    # If no key provided, allow access
    if not x_api_key:
        return None

    # If key provided, validate it
    if settings.api_key:
        expected_key = settings.api_key.get_secret_value()
        if not secrets.compare_digest(x_api_key, expected_key):
            logger.warning("optional_api_key_invalid")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    return x_api_key
