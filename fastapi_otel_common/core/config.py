import os
import httpx
from typing import List, Dict

APP_TITLE = os.getenv(
    "APP_TITLE", "Change Title using APP_TITLE environment variable")
APP_VERSION = os.getenv("APP_VERSION", "1.0")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Fetch OIDC configuration from discovery URL
OIDC_DISCOVERY_URL = os.getenv("OIDC_DISCOVERY_URL")
if not OIDC_DISCOVERY_URL:
    OIDC_ISSUER_URL = os.getenv(
        "OIDC_ISSUER", "http://auth.com/realms/organization"
    ).rstrip("/")
    OIDC_DISCOVERY_URL = f"{OIDC_ISSUER_URL}/.well-known/openid-configuration"

try:
    with httpx.Client() as client:
        discovery_response = client.get(OIDC_DISCOVERY_URL)
        # Raise exception for 4xx/5xx status codes
        discovery_response.raise_for_status()
        oidc_config = discovery_response.json()
except (httpx.RequestError, httpx.HTTPStatusError) as e:
    print(f"Error fetching OIDC discovery document: {e}")
    # Handle error appropriately, e.g., exit or use default values
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

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "public")
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

# --- Connection Pool Settings ---
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # In seconds
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # In seconds

ECHO_SQL = os.getenv("ECHO_SQL", "False").lower() in ("true", "1", "t")
