"""Core data models for the application."""
from typing import Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user model with OIDC claims.
    
    Attributes:
        id: Unique user identifier from OIDC provider
        email: User's email address
        given_name: User's first/given name
        family_name: User's last/family name (optional)
        is_admin: Whether user has admin privileges
    """
    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User's email address")
    given_name: str = Field(..., description="User's given name")
    family_name: Optional[str] = Field(None, description="User's family name")
    is_admin: bool = Field(False, description="Admin privilege flag")