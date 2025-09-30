from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import PyJWKClient, decode as jwt_decode, InvalidTokenError
from typing import Optional

from ..core.models import UserBase
from ..logging.logger import get_logger
from ..core.config import (
    OIDC_JWKS_URI,
    TOKEN_ALGORITHMS,
    OIDC_AUDIENCE,
    OIDC_ISSUER,
    OIDC_AUTH_URL,
    OIDC_TOKEN_URL,
    SCOPES,
    OIDC_USER_NAME_CLAIM,
    OIDC_USER_ID_CLAIM,
)

logger = get_logger(__name__)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=OIDC_AUTH_URL,
    tokenUrl=OIDC_TOKEN_URL,
    scopes=SCOPES,
    scheme_name="OIDC",
    auto_error=False,
)


async def validate_token_and_get_user(token: str, optional: bool = False):
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


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Strict dependency → 401 if no valid token.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await validate_token_and_get_user(token)


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)):
    """
    Lenient dependency → returns None if no token or invalid token.
    """
    if not token:
        return None
    return await validate_token_and_get_user(token, optional=True)
