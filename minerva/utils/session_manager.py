"""Session management utility for multiple services."""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class ServiceType(str, Enum):
    """Supported service types for session management."""

    KINDLE = "kindle"
    # Future services can be added here
    # PUBMED = "pubmed"
    # GOOGLE_SCHOLAR = "google-scholar"
    # PDF = "pdf"


@dataclass
class SessionInfo:
    """Information about a service session."""

    service: ServiceType
    exists: bool
    path: Path
    size_bytes: int | None = None
    modified_at: datetime | None = None
    is_valid: bool = False


class SessionManager:
    """
    Manage authentication sessions for multiple services.

    This class provides centralized session management across different
    data sources (Kindle, PubMed, etc.) with support for:
    - Service-specific session storage
    - Session validation and expiration checking
    - Bulk operations (clear all, list all)
    - Backward compatibility with legacy session files
    """

    def __init__(self, sessions_dir: Path | None = None) -> None:
        """
        Initialize SessionManager.

        Args:
            sessions_dir: Directory for session files (defaults to ~/.minerva/sessions/)
        """
        if sessions_dir is None:
            sessions_dir = Path.home() / ".minerva" / "sessions"

        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Legacy session path for backward compatibility
        self.legacy_session_path = Path.home() / ".minerva" / "session_state.json"

        logger.info("session_manager_initialized", sessions_dir=str(self.sessions_dir))

    def get_session_path(self, service: ServiceType) -> Path:
        """
        Get session file path for a specific service.

        Args:
            service: Service type

        Returns:
            Path to service session file
        """
        return self.sessions_dir / f"{service.value}.json"

    def session_exists(self, service: ServiceType) -> bool:
        """
        Check if a session file exists for a service.

        Args:
            service: Service type

        Returns:
            True if session file exists, False otherwise
        """
        return self.get_session_path(service).exists()

    def get_session_info(self, service: ServiceType) -> SessionInfo:
        """
        Get detailed information about a service session.

        Args:
            service: Service type

        Returns:
            SessionInfo with session details
        """
        path = self.get_session_path(service)
        exists = path.exists()

        info = SessionInfo(
            service=service,
            exists=exists,
            path=path,
        )

        if exists:
            try:
                stat = path.stat()
                info.size_bytes = stat.st_size
                info.modified_at = datetime.fromtimestamp(stat.st_mtime)
                info.is_valid = self._validate_session_file(path)
            except Exception as e:
                logger.warning(
                    "failed_to_get_session_info",
                    service=service.value,
                    error=str(e),
                )

        return info

    def list_sessions(self) -> list[SessionInfo]:
        """
        List all available sessions.

        Returns:
            List of SessionInfo for all known services
        """
        sessions = []
        for service in ServiceType:
            sessions.append(self.get_session_info(service))
        return sessions

    def clear_session(self, service: ServiceType) -> bool:
        """
        Clear (delete) session file for a specific service.

        Args:
            service: Service type to clear

        Returns:
            True if session was deleted, False if it didn't exist
        """
        path = self.get_session_path(service)

        if not path.exists():
            logger.info("session_not_found", service=service.value, path=str(path))
            return False

        try:
            path.unlink()
            logger.info("session_cleared", service=service.value, path=str(path))
            return True
        except Exception as e:
            logger.error(
                "failed_to_clear_session",
                service=service.value,
                path=str(path),
                error=str(e),
            )
            raise RuntimeError(f"Failed to clear {service.value} session: {e}") from e

    def clear_all_sessions(self) -> dict[ServiceType, bool]:
        """
        Clear all service sessions.

        Returns:
            Dictionary mapping service types to whether they were cleared
        """
        results = {}
        for service in ServiceType:
            results[service] = self.clear_session(service)

        logger.info("all_sessions_cleared", cleared_count=sum(results.values()))
        return results

    def migrate_legacy_session(self) -> bool:
        """
        Migrate old session file to new location if it exists.

        Returns:
            True if migration was performed, False if no legacy session found
        """
        if not self.legacy_session_path.exists():
            return False

        try:
            # Copy to new location (Kindle service)
            new_path = self.get_session_path(ServiceType.KINDLE)

            # Read old session
            with open(self.legacy_session_path, "r") as f:
                session_data = json.load(f)

            # Write to new location
            with open(new_path, "w") as f:
                json.dump(session_data, f, indent=2)

            # Set secure permissions
            os.chmod(new_path, 0o600)

            # Delete old session
            self.legacy_session_path.unlink()

            logger.info(
                "session_migrated",
                from_path=str(self.legacy_session_path),
                to_path=str(new_path),
            )
            return True

        except Exception as e:
            logger.error(
                "session_migration_failed",
                error=str(e),
                legacy_path=str(self.legacy_session_path),
            )
            # Don't fail - just log the error
            return False

    def _validate_session_file(self, path: Path) -> bool:
        """
        Validate that a session file has valid JSON format.

        Args:
            path: Path to session file

        Returns:
            True if file is valid JSON, False otherwise
        """
        try:
            with open(path, "r") as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def get_total_sessions_size(self) -> int:
        """
        Calculate total size of all session files.

        Returns:
            Total size in bytes
        """
        total_size = 0
        for service in ServiceType:
            info = self.get_session_info(service)
            if info.size_bytes:
                total_size += info.size_bytes
        return total_size
