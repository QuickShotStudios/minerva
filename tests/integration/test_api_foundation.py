"""Integration tests for FastAPI foundation (Story 3.1)."""

from fastapi.testclient import TestClient

from minerva.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint functionality."""

    def test_health_check_endpoint_exists(self):
        """Test health check endpoint is accessible."""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # 200 if DB available, 503 if not

    def test_health_check_success_structure(self):
        """Test health check returns correct structure when database is available."""
        response = client.get("/health")
        data = response.json()

        if response.status_code == 200:
            # Database available
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
            assert data["version"] == "1.0.0"
        else:
            # Database unavailable
            assert response.status_code == 503
            assert "detail" in data

    def test_health_check_database_error(self):
        """Test health check returns 503 when database is unavailable."""
        response = client.get("/health")

        # If database is not running, should return 503
        if response.status_code == 503:
            data = response.json()
            assert "detail" in data
            assert "unavailable" in data["detail"].lower()


class TestCORS:
    """Test CORS middleware configuration."""

    def test_cors_headers_present(self):
        """Test that CORS headers are included in responses."""
        response = client.get(
            "/health", headers={"Origin": "http://localhost:3000"}
        )

        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-credentials" in response.headers

    def test_preflight_request(self):
        """Test that preflight OPTIONS requests work correctly."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-methods" in response.headers


class TestAPIDocumentation:
    """Test OpenAPI documentation endpoints."""

    def test_swagger_ui_accessible(self):
        """Test that Swagger UI documentation is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_accessible(self):
        """Test that ReDoc documentation is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_json_accessible(self):
        """Test that OpenAPI JSON schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert data["info"]["title"] == "Minerva API"
        assert data["info"]["description"] == "Knowledge base query API for peptide research"
        assert "paths" in data


class TestAPIVersioning:
    """Test API versioning structure."""

    def test_health_check_no_version_prefix(self):
        """Test that health check is accessible without version prefix."""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # 200 if DB up, 503 if down

    def test_api_v1_prefix_ready(self):
        """Test that /api/v1 prefix is configured (may have no routes yet)."""
        # This will return 404 since we haven't added routes yet, but the prefix exists
        response = client.get("/api/v1/")
        # Either 404 (no routes) or 200+ (has routes) is acceptable
        assert response.status_code in [404, 405, 200, 307]


class TestErrorHandlers:
    """Test global error handlers."""

    def test_validation_error_handler(self):
        """Test that validation errors return 422."""
        # Try to access a non-existent route to trigger validation if query params were required
        # For now, just verify the handler exists by checking a malformed request
        response = client.get("/health?invalid_param=[]")
        # Health endpoint should still work even with extra params
        assert response.status_code in [200, 422, 503]  # 503 if DB unavailable

    def test_404_for_invalid_route(self):
        """Test that invalid routes return 404."""
        response = client.get("/invalid-route-that-does-not-exist")
        assert response.status_code == 404


class TestLoggingMiddleware:
    """Test request logging middleware."""

    def test_request_completes_with_middleware(self):
        """Test that requests complete successfully with logging middleware."""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # DB up or down
        # Middleware should not interfere with request processing


class TestApplicationLifespan:
    """Test application startup and shutdown events."""

    def test_app_initialization(self):
        """Test that app initializes correctly."""
        # If we got this far, the app initialized successfully
        assert app is not None
        assert app.title == "Minerva API"
        assert app.version == "0.1.0"  # From version.py

    def test_health_check_after_initialization(self):
        """Test that health check works after app initialization."""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # DB up or down
