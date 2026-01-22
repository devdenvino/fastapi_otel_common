---
layout: default
title: Security
nav_order: 5
---

# Security Guide
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The security module provides OIDC/OAuth2 authentication and authorization utilities for FastAPI applications.

## OIDC Authentication

### Configuration

Configure your OIDC provider using environment variables:

```bash
# SSL Certificate Verification (default: True)
SSL_VERIFY=True  # Set to False for self-signed certificates in development

# Automatic configuration (recommended)
OIDC_DISCOVERY_URL=https://auth.example.com/.well-known/openid-configuration

# Manual configuration
OIDC_ISSUER=https://auth.example.com/realms/organization
OIDC_JWKS_URI=https://auth.example.com/realms/organization/protocol/openid-connect/certs
OIDC_TOKEN_URL=https://auth.example.com/realms/organization/protocol/openid-connect/token
OIDC_AUTH_URL=https://auth.example.com/realms/organization/protocol/openid-connect/auth

# Client configuration
OIDC_CLIENT_ID=my-client-id
OIDC_AUDIENCE=account
SWAGGER_CLIENT_ID=my-swagger-client-id

# Token configuration
TOKEN_ALGORITHMS=RS256
OIDC_USER_NAME_CLAIM=preferred_username
OIDC_USER_ID_CLAIM=sub
```

### Using Authentication Dependencies

#### Strict Authentication

Requires valid JWT token, returns 401 if missing or invalid:

```python
from fastapi import Depends, FastAPI
from fastapi_otel_common.security import get_current_user
from fastapi_otel_common.core.models import UserBase

app = FastAPI()

@app.get("/protected")
async def protected_route(user: UserBase = Depends(get_current_user)):
    return {
        "message": "Access granted",
        "user_id": user.id,
        "email": user.email,
        "name": f"{user.given_name} {user.family_name}"
    }
```

#### Optional Authentication

Returns None if token is missing or invalid:

```python
from typing import Optional
from fastapi import Depends
from fastapi_otel_common.security import get_current_user_optional
from fastapi_otel_common.core.models import UserBase

@app.get("/public")
async def public_route(user: Optional[UserBase] = Depends(get_current_user_optional)):
    if user:
        return {"message": f"Hello, {user.given_name}!"}
    return {"message": "Hello, anonymous!"}
```

## Security Headers

The security headers middleware adds OWASP-recommended headers to all responses:

```python
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

### Customizing Security Headers

To customize security headers, you can modify the middleware or override specific endpoints:

```python
from fastapi import Response

@app.get("/custom")
async def custom_headers(response: Response):
    response.headers["X-Custom-Header"] = "value"
    return {"message": "Custom headers"}
```

## User Model

The `UserBase` model represents authenticated user information:

```python
from fastapi_otel_common.core.models import UserBase

class UserBase(BaseModel):
    id: str                    # User ID from OIDC provider
    email: str                 # User email
    given_name: str           # First name
    family_name: Optional[str] # Last name
    is_admin: bool = False    # Admin flag
```

## JWT Token Validation

The library automatically validates JWT tokens:

1. Fetches JWKS from the OIDC provider
2. Validates token signature
3. Checks issuer and audience
4. Extracts user claims
5. Returns structured user information

### Supported OIDC Providers

- Keycloak
- Auth0
- Okta
- Azure AD
- Any standard OIDC-compliant provider

## Swagger UI Integration

The `create_app()` function automatically configures Swagger UI for OIDC:

```python
from fastapi_otel_common import create_app

app = create_app(
    title="My API",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": "my-swagger-client-id",
        "scopes": "openid profile email api:read api:write"
    }
)
```

Access Swagger UI at `/docs` and authenticate using the "Authorize" button.

## Rate Limiting

Protect your API from abuse with rate limiting:

```bash
ENABLE_RATE_LIMIT_MIDDLEWARE=True
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

Rate limiting is applied per IP address. Health check endpoints (`/health`, `/docs`) are excluded.

### Custom Rate Limits

Apply custom limits to specific routes:

```python
from fastapi_otel_common import create_app

app = create_app()
limiter = app.state.limiter

@app.get("/expensive")
@limiter.limit("5/minute")
async def expensive_endpoint(request: Request):
    # Heavy operation
    return {"status": "ok"}
```

## Best Practices

1. **Use HTTPS in production** - Never send tokens over HTTP
2. **Always verify SSL certificates** - Keep `SSL_VERIFY=True` in production
3. **Rotate secrets regularly** - Update client secrets periodically
3. **Limit token scope** - Request only necessary scopes
4. **Enable rate limiting** - Protect against abuse
5. **Monitor authentication** - Track failed login attempts
6. **Use short-lived tokens** - Configure appropriate token lifetimes
7. **Validate audience** - Ensure tokens are intended for your service

## Example: Complete Secure Application

```python
from fastapi import Depends, FastAPI
from fastapi_otel_common import create_app
from fastapi_otel_common.security import get_current_user
from fastapi_otel_common.core.models import UserBase

# Create app with security and automatic OpenTelemetry instrumentation
app = create_app(
    title="Secure API",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Public endpoint"}

@app.get("/profile")
async def get_profile(user: UserBase = Depends(get_current_user)):
    return {
        "user_id": user.id,
        "email": user.email,
        "name": f"{user.given_name} {user.family_name}"
    }

@app.get("/admin")
async def admin_only(user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"message": "Admin access granted"}
```

## Troubleshooting

### Token Validation Fails

1. Check OIDC discovery URL is accessible
2. Verify `OIDC_AUDIENCE` matches your client
3. Ensure `TOKEN_ALGORITHMS` is correct (usually RS256)
4. Check token hasn't expired

### Swagger UI Authorization Not Working

1. Verify `SWAGGER_CLIENT_ID` is set correctly
2. Check redirect URL is allowed in OIDC provider
3. Ensure scopes are configured properly

## Next Steps

- [Database Guide](database) - Set up database integration
- [Examples](examples) - See complete examples
- [API Reference](api) - Full API documentation
