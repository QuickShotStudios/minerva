"""Unit tests for session manager."""

import json
from pathlib import Path

import pytest

from minerva.utils.session_manager import ServiceType, SessionInfo, SessionManager


class TestSessionManager:
    """Test suite for SessionManager class."""

    @pytest.fixture
    def temp_sessions_dir(self, tmp_path: Path) -> Path:
        """Create temporary sessions directory for testing."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        return sessions_dir

    @pytest.fixture
    def session_manager(self, temp_sessions_dir: Path) -> SessionManager:
        """Create SessionManager instance with temp directory."""
        return SessionManager(sessions_dir=temp_sessions_dir)

    def test_initialization(self, session_manager: SessionManager, temp_sessions_dir: Path) -> None:
        """Test SessionManager initialization."""
        assert session_manager.sessions_dir == temp_sessions_dir
        assert temp_sessions_dir.exists()

    def test_get_session_path(self, session_manager: SessionManager) -> None:
        """Test getting session path for a service."""
        path = session_manager.get_session_path(ServiceType.KINDLE)
        assert path.name == "kindle.json"
        assert path.parent == session_manager.sessions_dir

    def test_session_exists_false(self, session_manager: SessionManager) -> None:
        """Test checking for non-existent session."""
        assert not session_manager.session_exists(ServiceType.KINDLE)

    def test_session_exists_true(self, session_manager: SessionManager) -> None:
        """Test checking for existing session."""
        # Create session file
        session_path = session_manager.get_session_path(ServiceType.KINDLE)
        session_path.write_text(json.dumps({"cookies": []}))

        assert session_manager.session_exists(ServiceType.KINDLE)

    def test_get_session_info_no_session(self, session_manager: SessionManager) -> None:
        """Test getting info for non-existent session."""
        info = session_manager.get_session_info(ServiceType.KINDLE)

        assert isinstance(info, SessionInfo)
        assert info.service == ServiceType.KINDLE
        assert not info.exists
        assert info.size_bytes is None
        assert info.modified_at is None
        assert not info.is_valid

    def test_get_session_info_with_session(self, session_manager: SessionManager) -> None:
        """Test getting info for existing session."""
        # Create valid session file
        session_path = session_manager.get_session_path(ServiceType.KINDLE)
        session_data = {"cookies": [{"name": "test", "value": "data"}]}
        session_path.write_text(json.dumps(session_data))

        info = session_manager.get_session_info(ServiceType.KINDLE)

        assert info.service == ServiceType.KINDLE
        assert info.exists
        assert info.size_bytes and info.size_bytes > 0
        assert info.modified_at is not None
        assert info.is_valid

    def test_list_sessions_empty(self, session_manager: SessionManager) -> None:
        """Test listing sessions when none exist."""
        sessions = session_manager.list_sessions()

        assert len(sessions) == len(ServiceType)
        for session in sessions:
            assert not session.exists

    def test_list_sessions_with_data(self, session_manager: SessionManager) -> None:
        """Test listing sessions with some present."""
        # Create Kindle session
        kindle_path = session_manager.get_session_path(ServiceType.KINDLE)
        kindle_path.write_text(json.dumps({"cookies": []}))

        sessions = session_manager.list_sessions()

        kindle_session = next(s for s in sessions if s.service == ServiceType.KINDLE)
        assert kindle_session.exists

        # Other sessions should not exist
        other_sessions = [s for s in sessions if s.service != ServiceType.KINDLE]
        assert all(not s.exists for s in other_sessions)

    def test_clear_session_non_existent(self, session_manager: SessionManager) -> None:
        """Test clearing non-existent session returns False."""
        result = session_manager.clear_session(ServiceType.KINDLE)
        assert not result

    def test_clear_session_success(self, session_manager: SessionManager) -> None:
        """Test successfully clearing a session."""
        # Create session
        session_path = session_manager.get_session_path(ServiceType.KINDLE)
        session_path.write_text(json.dumps({"cookies": []}))
        assert session_path.exists()

        # Clear it
        result = session_manager.clear_session(ServiceType.KINDLE)
        assert result
        assert not session_path.exists()

    def test_clear_all_sessions_empty(self, session_manager: SessionManager) -> None:
        """Test clearing all sessions when none exist."""
        results = session_manager.clear_all_sessions()

        assert all(not cleared for cleared in results.values())

    def test_clear_all_sessions_with_data(self, session_manager: SessionManager) -> None:
        """Test clearing all sessions when some exist."""
        # Create Kindle session
        kindle_path = session_manager.get_session_path(ServiceType.KINDLE)
        kindle_path.write_text(json.dumps({"cookies": []}))

        results = session_manager.clear_all_sessions()

        # Kindle should be cleared
        assert results[ServiceType.KINDLE]
        assert not kindle_path.exists()

        # Others should not be cleared (didn't exist)
        for service in ServiceType:
            if service != ServiceType.KINDLE:
                assert not results[service]

    def test_migrate_legacy_session_no_legacy(
        self, session_manager: SessionManager, tmp_path: Path
    ) -> None:
        """Test migration when no legacy session exists."""
        # Set legacy path to temp location
        session_manager.legacy_session_path = tmp_path / "legacy.json"

        result = session_manager.migrate_legacy_session()
        assert not result

    def test_migrate_legacy_session_success(
        self, session_manager: SessionManager, tmp_path: Path
    ) -> None:
        """Test successful migration of legacy session."""
        # Create legacy session
        legacy_path = tmp_path / "legacy.json"
        legacy_data = {"cookies": [{"name": "legacy", "value": "test"}]}
        legacy_path.write_text(json.dumps(legacy_data))

        session_manager.legacy_session_path = legacy_path

        # Migrate
        result = session_manager.migrate_legacy_session()
        assert result

        # Check legacy is gone
        assert not legacy_path.exists()

        # Check new location exists
        kindle_path = session_manager.get_session_path(ServiceType.KINDLE)
        assert kindle_path.exists()

        # Verify data was copied
        with open(kindle_path) as f:
            migrated_data = json.load(f)
        assert migrated_data == legacy_data

    def test_validate_session_file_valid(
        self, session_manager: SessionManager
    ) -> None:
        """Test validating a valid JSON session file."""
        session_path = session_manager.get_session_path(ServiceType.KINDLE)
        session_path.write_text(json.dumps({"valid": "json"}))

        assert session_manager._validate_session_file(session_path)

    def test_validate_session_file_invalid(
        self, session_manager: SessionManager
    ) -> None:
        """Test validating an invalid JSON session file."""
        session_path = session_manager.get_session_path(ServiceType.KINDLE)
        session_path.write_text("not valid json {")

        assert not session_manager._validate_session_file(session_path)

    def test_validate_session_file_missing(
        self, session_manager: SessionManager
    ) -> None:
        """Test validating a non-existent file."""
        session_path = session_manager.get_session_path(ServiceType.KINDLE)

        assert not session_manager._validate_session_file(session_path)

    def test_get_total_sessions_size_empty(
        self, session_manager: SessionManager
    ) -> None:
        """Test getting total size when no sessions exist."""
        total_size = session_manager.get_total_sessions_size()
        assert total_size == 0

    def test_get_total_sessions_size_with_data(
        self, session_manager: SessionManager
    ) -> None:
        """Test getting total size with existing sessions."""
        # Create sessions with known sizes
        kindle_path = session_manager.get_session_path(ServiceType.KINDLE)
        kindle_data = json.dumps({"test": "data"})
        kindle_path.write_text(kindle_data)

        total_size = session_manager.get_total_sessions_size()
        assert total_size == len(kindle_data)

    def test_service_type_enum_values(self) -> None:
        """Test ServiceType enum has expected values."""
        assert ServiceType.KINDLE.value == "kindle"
        # When adding new services, test them here
        # assert ServiceType.PUBMED.value == "pubmed"
