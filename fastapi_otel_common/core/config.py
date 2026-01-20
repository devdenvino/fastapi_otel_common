"""Configuration module for FastAPI OTEL Common.

Loads configuration from environment variables with sensible defaults.
"""
import logging
import os
from typing import Any, Dict, List

import httpx

# Basic application configuration
APP_TITLE = os.getenv(
    "APP_TITLE", "Change Title using APP_TITLE environment variable"
)
APP_VERSION = os.getenv("APP_VERSION", "1.0")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# OIDC Configuration
# Fetch OIDC configuration from discovery URL
OIDC_DISCOVERY_URL = os.getenv("OIDC_DISCOVERY_URL")
if not OIDC_DISCOVERY_URL:
    OIDC_ISSUER_URL = os.getenv(
        "OIDC_ISSUER", "http://auth.com/realms/organization"
    ).rstrip("/")
    OIDC_DISCOVERY_URL = f"{OIDC_ISSUER_URL}/.well-known/openid-configuration"

oidc_config: Dict[str, Any] = {}
try:
    with httpx.Client(timeout=10.0) as client:
        discovery_response = client.get(OIDC_DISCOVERY_URL)
        discovery_response.raise_for_status()
        oidc_config = discovery_response.json()
except (httpx.RequestError, httpx.HTTPStatusError) as e:
    # Use logging instead of print for production readiness
    logging.warning(
        f"Failed to fetch OIDC discovery document from {OIDC_DISCOVERY_URL}: {e}. "
        "Using default OIDC configuration."
    )
    oidc_config = {}

OIDC_ISSUER = oidc_config.get(
    "issuer", os.getenv("OIDC_ISSUER", "http://auth.com/realms/organization")
)
OIDC_JWKS_URI = oidc_config.get(
    "jwks_uri", f"{OIDC_ISSUER}/protocol/openid-connect/certs"
)
OIDC_TOKEN_URL = oidc_config.get(
    "token_endpoint", f"{OIDC_ISSUER}/protocol/openid-connect/token"
)
OIDC_AUTH_URL = oidc_config.get(
    "authorization_endpoint", f"{OIDC_ISSUER}/protocol/openid-connect/auth"
)

OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "client_id")
OIDC_AUDIENCE = os.getenv("OIDC_AUDIENCE", "account")
SWAGGER_CLIENT_ID = os.getenv("SWAGGER_CLIENT_ID", OIDC_CLIENT_ID)
ALLOWED_ORIGINS = [o.strip()
                   for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]
TOKEN_ALGORITHMS = [
    a.strip() for a in os.getenv("TOKEN_ALGORITHMS", "RS256").split(",")
]

# Define API scopes you will require from tokens
SCOPES: Dict[str, str] = {
    "openid": "Request OpenID scope",
    "profile": "Request basic profile",
    "email": "Request email",
    "api:read": "Read access to the API",
    "api:write": "Write access to the API",
}
OIDC_USER_NAME_CLAIM = os.getenv("OIDC_USER_NAME_CLAIM", "preferred_username")
OIDC_USER_ID_CLAIM = os.getenv("OIDC_USER_ID_CLAIM", "company")

# Database configuration
# DB_TYPE can be 'postgresql' or 'sqlite' (default: postgresql)
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "public")
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

# SQLite configuration (used when DB_TYPE=sqlite)
# Default: ./data/app.db (relative to project root)
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/app.db")

# --- Connection Pool Settings ---
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # In seconds
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # In seconds

ECHO_SQL = os.getenv("ECHO_SQL", "False").lower() in ("true", "1", "t")

# --- Middleware Configuration ---
# Enable/disable individual middleware components
ENABLE_REQUEST_ID_MIDDLEWARE = os.getenv("ENABLE_REQUEST_ID_MIDDLEWARE", "True").lower() in ("true", "1", "t")
ENABLE_SECURITY_HEADERS_MIDDLEWARE = os.getenv("ENABLE_SECURITY_HEADERS_MIDDLEWARE", "True").lower() in ("true", "1", "t")
ENABLE_LOGGING_MIDDLEWARE = os.getenv("ENABLE_LOGGING_MIDDLEWARE", "True").lower() in ("true", "1", "t")
ENABLE_RATE_LIMIT_MIDDLEWARE = os.getenv("ENABLE_RATE_LIMIT_MIDDLEWARE", "False").lower() in ("true", "1", "t")
ENABLE_OTEL_INSTRUMENTATION = os.getenv("ENABLE_OTEL_INSTRUMENTATION", "True").lower() in ("true", "1", "t")

# Rate limiting configuration (using slowapi)
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

# Rate limiter backend: 'memory' or 'redis'
RATE_LIMITER_BACKEND = os.getenv("RATE_LIMITER_BACKEND", "memory").lower()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# --- OpenTelemetry Metrics Configuration ---
ENABLE_OTEL_METRICS = os.getenv("ENABLE_OTEL_METRICS", "True").lower() in ("true", "1", "t")
OTEL_METRIC_EXPORT_INTERVAL = int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL", "60000"))  # In milliseconds
