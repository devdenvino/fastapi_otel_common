"""Core data models for the application."""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user model with OIDC claims.
    
    Attributes:
        id: Unique user identifier from OIDC provider
        email: User's email address
        given_name: User's first/given name
        family_name: User's last/family name (optional)
        is_admin: Whether user has admin privileges
        roles: Dictionary mapping client IDs to lists of roles
    """
    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User's email address")
    given_name: str = Field(..., description="User's given name")
    family_name: Optional[str] = Field(None, description="User's family name")
    is_admin: bool = Field(False, description="Admin privilege flag")
    roles: Dict[str, List[str]] = Field(default_factory=dict, description="Client ID to roles mapping")
    
    def has_role(self, role: str, client_id: str = None) -> bool:
        """Check if user has a specific role for a client.
        
        Args:
            role: Role name to check
            client_id: Client ID (defaults to OIDC_CLIENT_ID from config if not provided)
            
        Returns:
            True if user has the role
        """
        from .config import OIDC_CLIENT_ID
        client = client_id or OIDC_CLIENT_ID
        return role in self.roles.get(client, [])
    
    def has_any_role(self, roles: List[str], client_id: str = None) -> bool:
        """Check if user has any of the specified roles.
        
        Args:
            roles: List of role names
            client_id: Client ID (defaults to OIDC_CLIENT_ID from config if not provided)
            
        Returns:
            True if user has at least one of the roles
        """
        from .config import OIDC_CLIENT_ID
        client = client_id or OIDC_CLIENT_ID
        user_roles = self.roles.get(client, [])
        return any(role in user_roles for role in roles)
    
    def has_all_roles(self, roles: List[str], client_id: str = None) -> bool:
        """Check if user has all of the specified roles.
        
        Args:
            roles: List of role names
            client_id: Client ID (defaults to OIDC_CLIENT_ID from config if not provided)
            
        Returns:
            True if user has all of the roles
        """
        from .config import OIDC_CLIENT_ID
        client = client_id or OIDC_CLIENT_ID
        user_roles = self.roles.get(client, [])
        return all(role in user_roles for role in roles)
    
    def get_roles(self, client_id: str = None) -> List[str]:
        """Get user's roles for a specific client.
        
        Args:
            client_id: Client ID (defaults to OIDC_CLIENT_ID from config if not provided)
            
        Returns:
            List of role names
        """
        from .config import OIDC_CLIENT_ID
        client = client_id or OIDC_CLIENT_ID
        return self.roles.get(client, [])
    
    def get_all_roles_flat(self) -> List[str]:
        """Get all roles from all clients as a flat list.
        
        Returns:
            List of all role names (may contain duplicates if role exists in multiple clients)
        """
        all_roles = []
        for client_roles in self.roles.values():
            all_roles.extend(client_roles)
        return all_roles