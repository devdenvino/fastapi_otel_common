"""Authentication and authorization utilities using OIDC/OAuth2.

Provides JWT token validation and user extraction from OIDC providers.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import InvalidTokenError
from jwt import PyJWKClient
from jwt import decode as jwt_decode

from ..core.config import (
    OIDC_AUDIENCE,
    OIDC_AUTH_URL,
    OIDC_ISSUER,
    OIDC_JWKS_URI,
    OIDC_TOKEN_URL,
    OIDC_USER_ID_CLAIM,
    OIDC_USER_NAME_CLAIM,
    SCOPES,
    TOKEN_ALGORITHMS,
)
from ..core.models import UserBase
from ..logging.logger import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=OIDC_AUTH_URL,
    tokenUrl=OIDC_TOKEN_URL,
    scopes=SCOPES,
    scheme_name="OIDC",
    auto_error=False,
)


async def validate_token_and_get_user(
    token: str, optional: bool = False
) -> Optional[UserBase]:
    """Validate JWT token and extract user information.
    
    Args:
        token: JWT token string to validate
        optional: If True, returns None on validation failure instead of raising exception
        
    Returns:
        UserBase object with user information or None if optional=True and validation fails
        
    Raises:
        HTTPException: 401 Unauthorized if token is invalid and optional=False
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        jwks_client = PyJWKClient(OIDC_JWKS_URI)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt_decode(
            token,
            signing_key.key,
            algorithms=TOKEN_ALGORITHMS,
            audience=OIDC_AUDIENCE,
            issuer=OIDC_ISSUER,
        )

        username: str = payload.get(OIDC_USER_NAME_CLAIM, "")
        if not username and not optional:
            raise credentials_exception
        userid: str = payload.get(OIDC_USER_ID_CLAIM, "")
        user = UserBase(id=userid, email=payload.get("email", ""),
                        given_name=payload.get("given_name", payload.get("name", "")),
                        family_name=payload.get("family_name", payload.get("name", "")))
        return user

    except InvalidTokenError as e:
        logger.error(f"Invalid Token: {e}")
        if not optional:
            raise credentials_exception
    except Exception as e:
        logger.error(f"Exception: {e}")
        if not optional:
            raise credentials_exception
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserBase:
    """FastAPI dependency to get authenticated user (strict mode).
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        UserBase: Authenticated user information
        
    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await validate_token_and_get_user(token)


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[UserBase]:
    """FastAPI dependency to get user if authenticated (lenient mode).
    
    Args:
        token: JWT token from Authorization header (optional)
        
    Returns:
        UserBase if token is valid, None otherwise
    """
    if not token:
        return None
    return await validate_token_and_get_user(token, optional=True)
