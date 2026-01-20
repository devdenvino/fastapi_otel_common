"""Authentication and authorization utilities using OIDC/OAuth2.

Provides JWT token validation and user extraction from OIDC providers.
"""
from typing import Callable, Dict, List, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import InvalidTokenError
from jwt import PyJWKClient
from jwt import decode as jwt_decode

from ..core.config import (
    OIDC_AUDIENCE,
    OIDC_AUTH_URL,
    OIDC_CLIENT_ID,
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
        
        # Extract roles from resource_access claim (Keycloak format)
        # Structure: {"client-id": {"roles": ["role1", "role2"]}}
        roles: Dict[str, List[str]] = {}
        resource_access = payload.get("resource_access", {})
        if isinstance(resource_access, dict):
            for client_id, client_data in resource_access.items():
                if isinstance(client_data, dict) and "roles" in client_data:
                    roles[client_id] = client_data["roles"]
        
        # Also check realm_access for realm-level roles
        realm_access = payload.get("realm_access", {})
        if isinstance(realm_access, dict) and "roles" in realm_access:
            roles["realm"] = realm_access["roles"]
        
        user = UserBase(
            id=userid,
            email=payload.get("email", ""),
            given_name=payload.get("given_name", payload.get("name", "")),
            family_name=payload.get("family_name", payload.get("name", "")),
            roles=roles
        )
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


class RequireRoles:
    """FastAPI dependency to check if user has required roles under a client ID.
    
    Usage:
        # Using default client ID from OIDC_CLIENT_ID config
        @app.get("/admin", dependencies=[Depends(RequireRoles(["admin", "manager"]))])
        async def admin_endpoint():
            return {"message": "Admin access"}
        
        # Using specific client ID
        @app.get("/admin", dependencies=[Depends(RequireRoles(["admin"], "my-client-id"))])
        async def admin_endpoint():
            return {"message": "Admin access"}
        
        # Or to get the user object:
        @app.get("/admin")
        async def admin_endpoint(user: UserBase = Depends(RequireRoles(["admin"]))):
            return {"message": f"Welcome {user.given_name}"}
    
    Attributes:
        required_roles: List of roles, user must have at least one of these roles
        client_id: The client ID to check roles for (defaults to OIDC_CLIENT_ID from config)
    """
    
    def __init__(self, required_roles: List[str], client_id: str = None):
        """Initialize the role checker.
        
        Args:
            required_roles: List of role names (user needs at least one)
            client_id: The client ID to check roles for (defaults to OIDC_CLIENT_ID if not provided)
        """
        self.required_roles = required_roles
        self.client_id = client_id or OIDC_CLIENT_ID
        
        # Validate that client_id is a string, not a list
        if isinstance(self.client_id, list):
            raise TypeError(
                f"client_id must be a string, not a list. "
                f"Got: {self.client_id}. "
                f"Usage: RequireRoles(['role1', 'role2'], 'client_id')"
            )
    
    async def __call__(self, current_user: UserBase = Depends(get_current_user)) -> UserBase:
        """Verify user has required roles.
        
        Args:
            current_user: Authenticated user from dependency injection
            
        Returns:
            UserBase: The authenticated user with verified roles
            
        Raises:
            HTTPException: 403 Forbidden if user doesn't have required roles
        """
        user_roles = current_user.roles.get(self.client_id, [])
        
        # Check if user has at least one of the required roles
        has_role = any(role in user_roles for role in self.required_roles)
        
        if not has_role:
            logger.warning(
                f"User {current_user.id} attempted to access resource requiring roles "
                f"{list(self.required_roles)} for client {self.client_id}, but has roles: {list(user_roles)}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {list(self.required_roles)} for client: {self.client_id}",
            )
        
        return current_user


class RequireAllRoles:
    """FastAPI dependency to check if user has ALL required roles (AND logic).
    
    Usage:
        # Using default client ID - user must have BOTH admin AND manager roles
        @app.get("/superadmin", dependencies=[Depends(RequireAllRoles(["admin", "manager"]))])
        async def superadmin_endpoint():
            return {"message": "Super admin access"}
        
        # Using specific client ID
        @app.get("/superadmin")
        async def superadmin_endpoint(user: UserBase = Depends(RequireAllRoles(["admin", "auditor"], "my-client-id"))):
            return {"message": f"Welcome {user.given_name}"}
    
    Attributes:
        required_roles: List of roles, user must have ALL of these roles
        client_id: The client ID to check roles for (defaults to OIDC_CLIENT_ID from config)
    """
    
    def __init__(self, required_roles: List[str], client_id: str = None):
        """Initialize the role checker.
        
        Args:
            required_roles: List of role names (user needs all of them)
            client_id: The client ID to check roles for (defaults to OIDC_CLIENT_ID if not provided)
        """
        self.required_roles = required_roles
        self.client_id = client_id or OIDC_CLIENT_ID        
        # Validate that client_id is a string, not a list
        if isinstance(self.client_id, list):
            raise TypeError(
                f"client_id must be a string, not a list. "
                f"Got: {self.client_id}. "
                f"Usage: RequireAllRoles(['role1', 'role2'], 'client_id')"
            )    
    async def __call__(self, current_user: UserBase = Depends(get_current_user)) -> UserBase:
        """Verify user has ALL required roles.
        
        Args:
            current_user: Authenticated user from dependency injection
            
        Returns:
            UserBase: The authenticated user with verified roles
            
        Raises:
            HTTPException: 403 Forbidden if user doesn't have all required roles
        """
        user_roles = current_user.roles.get(self.client_id, [])
        
        # Check if user has ALL of the required roles
        has_all_roles = all(role in user_roles for role in self.required_roles)
        
        if not has_all_roles:
            missing_roles = [role for role in self.required_roles if role not in user_roles]
            logger.warning(
                f"User {current_user.id} attempted to access resource requiring ALL roles "
                f"{list(self.required_roles)} for client {self.client_id}, but is missing: {missing_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required ALL roles: {list(self.required_roles)} for client: {self.client_id}",
            )
        
        return current_user


class RoleCondition:
    """Base class for role checking conditions.
    
    Allows building complex AND/OR logic for role requirements.
    Industry standard approach used in enterprise RBAC systems.
    """
    
    def check(self, user_roles: List[str]) -> bool:
        """Check if the condition is satisfied.
        
        Args:
            user_roles: List of roles the user has
            
        Returns:
            True if condition is satisfied, False otherwise
        """
        raise NotImplementedError


class AnyRole(RoleCondition):
    """OR condition: User must have at least one of the specified roles."""
    
    def __init__(self, roles: List[str]):
        self.roles = roles
    
    def check(self, user_roles: List[str]) -> bool:
        return any(role in user_roles for role in self.roles)
    
    def __repr__(self):
        return f"AnyRole({self.roles})"


class AllRoles(RoleCondition):
    """AND condition: User must have all of the specified roles."""
    
    def __init__(self, roles: List[str]):
        self.roles = roles
    
    def check(self, user_roles: List[str]) -> bool:
        return all(role in user_roles for role in self.roles)
    
    def __repr__(self):
        return f"AllRoles({self.roles})"


class AnyCondition(RoleCondition):
    """OR condition for nested conditions: At least one condition must be satisfied."""
    
    def __init__(self, *conditions: RoleCondition):
        self.conditions = conditions
    
    def check(self, user_roles: List[str]) -> bool:
        return any(condition.check(user_roles) for condition in self.conditions)
    
    def __repr__(self):
        return f"AnyCondition({', '.join(str(c) for c in self.conditions)})"


class AllConditions(RoleCondition):
    """AND condition for nested conditions: All conditions must be satisfied."""
    
    def __init__(self, *conditions: RoleCondition):
        self.conditions = conditions
    
    def check(self, user_roles: List[str]) -> bool:
        return all(condition.check(user_roles) for condition in self.conditions)
    
    def __repr__(self):
        return f"AllConditions({', '.join(str(c) for c in self.conditions)})"


class RequireRolesComplex:
    """FastAPI dependency for complex role checking with AND/OR logic.
    
    Industry standard approach supporting complex authorization scenarios:
    - (admin AND auditor) OR superadmin
    - (editor OR contributor) AND (publisher OR reviewer)
    - Any combination of AND/OR conditions
    
    Usage:
        # Simple: (admin AND auditor) OR superadmin
        @app.delete("/critical")
        async def critical_op(
            user: UserBase = Depends(RequireRolesComplex(
                AnyCondition(
                    AllRoles(["admin", "auditor"]),
                    AnyRole(["superadmin"])
                )
            ))
        ):
            return {"message": "Critical operation"}
        
        # Complex: (admin OR manager) AND (editor OR publisher)
        @app.post("/publish")
        async def publish_content(
            user: UserBase = Depends(RequireRolesComplex(
                AllConditions(
                    AnyRole(["admin", "manager"]),
                    AnyRole(["editor", "publisher"])
                )
            ))
        ):
            return {"message": "Content published"}
    
    Attributes:
        condition: The role condition to evaluate
        client_id: The client ID to check roles for (defaults to OIDC_CLIENT_ID)
    """
    
    def __init__(self, condition: RoleCondition, client_id: str = None):
        """Initialize complex role checker.
        
        Args:
            condition: RoleCondition instance defining the logic
            client_id: The client ID to check roles for (defaults to OIDC_CLIENT_ID if not provided)
        """
        self.condition = condition
        self.client_id = client_id or OIDC_CLIENT_ID
        
        # Validate that client_id is a string, not a list
        if isinstance(self.client_id, list):
            raise TypeError(
                f"client_id must be a string, not a list. "
                f"Got: {self.client_id}. "
                f"Usage: RequireRolesComplex(condition, 'client_id')"
            )
    
    async def __call__(self, current_user: UserBase = Depends(get_current_user)) -> UserBase:
        """Verify user satisfies the role condition.
        
        Args:
            current_user: Authenticated user from dependency injection
            
        Returns:
            UserBase: The authenticated user with verified roles
            
        Raises:
            HTTPException: 403 Forbidden if user doesn't satisfy the role condition
        """
        user_roles = current_user.roles.get(self.client_id, [])
        
        if not self.condition.check(user_roles):
            logger.warning(
                f"User {current_user.id} attempted to access resource with condition {self.condition} "
                f"for client {self.client_id}, but has roles: {list(user_roles)}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required condition: {self.condition} for client: {self.client_id}",
            )
        
        return current_user
