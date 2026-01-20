"""Tests for middleware functionality.

Basic integration tests for all middleware components.
"""
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_otel_common.core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI application with middleware.
    
    Returns:
        FastAPI: Configured test application
    """
    app = FastAPI()
    
    # Add middleware
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/")
    async def root():
        return {"message": "Hello"}
    
    @app.get("/error")
    async def error():
        raise ValueError("Test error")
    
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client.
    
    Args:
        app: FastAPI application fixture
        
    Returns:
        TestClient: Test client for the application
    """
    return TestClient(app)


def test_request_id_middleware(client: TestClient) -> None:
    """Test that request ID is added to response headers in UUID format."""
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    # Verify it's a valid UUID format
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36  # UUID format: 8-4-4-4-12
    assert request_id.count("-") == 4


def test_security_headers(client: TestClient) -> None:
    """Test that all required security headers are present and correct."""
    response = client.get("/")
    
    # Check all security headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in response.headers
    # Note: CSP is only added to Swagger UI endpoints (/docs, /redoc, /openapi.json)


def test_error_handling(client: TestClient) -> None:
    """Test that errors are handled gracefully with proper error response."""
    response = client.get("/error")
    
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "internal error" in data["detail"].lower()
    assert "request_id" in data


def test_rate_limiting() -> None:
    """Test that rate limiting enforces request limits per minute."""
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=5,  # Low limit for testing
        requests_per_hour=100
    )
    
    @app.get("/test")
    async def test_endpoint() -> dict:
        return {"status": "ok"}
    
    client = TestClient(app)
    
    # Make requests up to the limit
    for i in range(5):
        response = client.get("/test")
        assert response.status_code == 200, f"Request {i+1} failed"
    
    # Next request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    data = response.json()
    assert "rate limit" in data["detail"].lower()


def test_rate_limiting_skips_health() -> None:
    """Test that rate limiting bypasses health check endpoints."""
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=2,  # Very low limit
        requests_per_hour=10
    )
    
    @app.get("/health")
    async def health() -> dict:
        return {"status": "healthy"}
    
    client = TestClient(app)
    
    # Health endpoint should never be rate limited
    for _ in range(10):
        response = client.get("/health")
        assert response.status_code == 200


def test_logging_middleware(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Test that requests are logged with appropriate information."""
    import logging
    
    with caplog.at_level(logging.INFO):
        response = client.get("/")
        assert response.status_code == 200
    
    # Check that log messages were created
    # Note: Exact log format may vary based on logger configuration
    log_texts = [record.message for record in caplog.records]
    assert any("Request started" in text or "Request completed" in text for text in log_texts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
