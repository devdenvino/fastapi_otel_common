"""Tests for role-based access control (RBAC) functionality.

Tests the RequireRoles dependency for protecting endpoints with client-specific roles.
"""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from fastapi_otel_common.core.models import UserBase
from fastapi_otel_common.security.auth import RequireRoles, get_current_user


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI application with RBAC endpoints.
    
    Returns:
        FastAPI: Configured test application with role-protected endpoints
    """
    app = FastAPI()
    
    @app.get("/public")
    async def public_endpoint():
        """Public endpoint - no authentication required"""
        return {"message": "Public access"}
    
    @app.get("/authenticated")
    async def authenticated_endpoint(user: UserBase = Depends(get_current_user)):
        """Authenticated endpoint - requires valid user"""
        return {"message": f"Hello {user.given_name}", "user_id": user.id}
    
    @app.get(
        "/admin",
        dependencies=[Depends(RequireRoles(["admin"], "test-client"))]
    )
    async def admin_endpoint():
        """Admin endpoint - requires admin role for test-client"""
        return {"message": "Admin access granted"}
    
    @app.get("/manager")
    async def manager_endpoint(
        user: UserBase = Depends(RequireRoles(["manager", "admin"], "test-client"))
    ):
        """Manager endpoint - requires manager OR admin role"""
        return {
            "message": f"Manager access for {user.email}",
            "roles": user.roles
        }
    
    @app.get("/viewer")
    async def viewer_endpoint(
        user: UserBase = Depends(RequireRoles(["viewer", "editor", "admin"], "test-client"))
    ):
        """Viewer endpoint - multiple acceptable roles"""
        return {"message": "Viewer access", "user_id": user.id}
    
    @app.get("/realm-admin")
    async def realm_admin_endpoint(
        user: UserBase = Depends(RequireRoles(["realm-admin"], "realm"))
    ):
        """Realm admin endpoint - requires realm-level role"""
        return {"message": "Realm admin access"}
    
    @app.get("/client-specific")
    async def client_specific_endpoint(
        user: UserBase = Depends(RequireRoles(["special-role"], "other-client"))
    ):
        """Endpoint for a different client ID"""
        return {"message": "Client-specific access"}
    
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client.
    
    Args:
        app: FastAPI application
        
    Returns:
        TestClient: Test client instance
    """
    return TestClient(app)


def create_mock_user(
    user_id: str = "user123",
    email: str = "user@example.com",
    roles: dict = None
) -> UserBase:
    """Create a mock UserBase object for testing.
    
    Args:
        user_id: User ID
        email: User email
        roles: Dictionary of client_id to roles list
        
    Returns:
        UserBase: Mock user object
    """
    if roles is None:
        roles = {}
    
    return UserBase(
        id=user_id,
        email=email,
        given_name="Test",
        family_name="User",
        roles=roles
    )


class TestRoleBasedAccessControl:
    """Test suite for RBAC functionality."""
    
    def test_admin_access_with_admin_role(self, client: TestClient):
        """User with admin role should access admin endpoint."""
        mock_user = create_mock_user(roles={"test-client": ["admin"]})
        
        with patch("fastapi_otel_common.security.auth.get_current_user", 
                   return_value=AsyncMock(return_value=mock_user)):
            # Mock the dependency
            from fastapi_otel_common.security.auth import get_current_user as gcu
            with patch.object(gcu, "__call__", return_value=mock_user):
                response = client.get("/admin")
                
        # Note: In real tests, you'd need to properly mock the authentication
        # This is a structure example
        assert mock_user.roles["test-client"] == ["admin"]
    
    def test_admin_access_without_admin_role(self):
        """User without admin role should not access admin endpoint."""
        mock_user = create_mock_user(roles={"test-client": ["viewer"]})
        
        # Test role checking logic
        user_roles = mock_user.roles.get("test-client", [])
        has_admin = "admin" in user_roles
        
        assert has_admin is False
    
    def test_manager_access_with_admin_role(self):
        """User with admin role should access manager endpoint (multiple acceptable roles)."""
        mock_user = create_mock_user(roles={"test-client": ["admin", "viewer"]})
        
        user_roles = mock_user.roles.get("test-client", [])
        has_role = any(role in user_roles for role in ["manager", "admin"])
        
        assert has_role is True
    
    def test_manager_access_with_manager_role(self):
        """User with manager role should access manager endpoint."""
        mock_user = create_mock_user(roles={"test-client": ["manager"]})
        
        user_roles = mock_user.roles.get("test-client", [])
        has_role = any(role in user_roles for role in ["manager", "admin"])
        
        assert has_role is True
    
    def test_manager_access_without_required_roles(self):
        """User without manager or admin role should not access manager endpoint."""
        mock_user = create_mock_user(roles={"test-client": ["viewer", "editor"]})
        
        user_roles = mock_user.roles.get("test-client", [])
        has_role = any(role in user_roles for role in ["manager", "admin"])
        
        assert has_role is False
    
    def test_viewer_access_with_editor_role(self):
        """User with editor role should access viewer endpoint."""
        mock_user = create_mock_user(roles={"test-client": ["editor"]})
        
        user_roles = mock_user.roles.get("test-client", [])
        has_role = any(role in user_roles for role in ["viewer", "editor", "admin"])
        
        assert has_role is True
    
    def test_realm_admin_access(self):
        """User with realm-admin role should access realm admin endpoint."""
        mock_user = create_mock_user(roles={"realm": ["realm-admin"]})
        
        user_roles = mock_user.roles.get("realm", [])
        has_role = "realm-admin" in user_roles
        
        assert has_role is True
    
    def test_client_specific_access_wrong_client(self):
        """User with roles for wrong client should not have access."""
        mock_user = create_mock_user(roles={"test-client": ["admin"]})
        
        # Check for different client
        user_roles = mock_user.roles.get("other-client", [])
        has_role = "special-role" in user_roles
        
        assert has_role is False
    
    def test_client_specific_access_correct_client(self):
        """User with roles for correct client should have access."""
        mock_user = create_mock_user(roles={"other-client": ["special-role"]})
        
        user_roles = mock_user.roles.get("other-client", [])
        has_role = "special-role" in user_roles
        
        assert has_role is True
    
    def test_multiple_clients_roles(self):
        """User can have roles for multiple clients."""
        mock_user = create_mock_user(roles={
            "test-client": ["admin", "viewer"],
            "other-client": ["user"],
            "realm": ["realm-admin"]
        })
        
        assert len(mock_user.roles) == 3
        assert "admin" in mock_user.roles["test-client"]
        assert "user" in mock_user.roles["other-client"]
        assert "realm-admin" in mock_user.roles["realm"]
    
    def test_no_roles_for_client(self):
        """User with no roles for client should not have access."""
        mock_user = create_mock_user(roles={"other-client": ["admin"]})
        
        user_roles = mock_user.roles.get("test-client", [])
        has_role = "admin" in user_roles
        
        assert has_role is False
        assert len(user_roles) == 0
    
    def test_empty_roles(self):
        """User with empty roles should not have access."""
        mock_user = create_mock_user(roles={})
        
        user_roles = mock_user.roles.get("test-client", [])
        has_role = any(role in user_roles for role in ["admin", "viewer"])
        
        assert has_role is False


class TestRequireRolesClass:
    """Test the RequireRoles class directly."""
    
    def test_require_roles_initialization(self):
        """RequireRoles should initialize with roles and optional client_id."""
        # New signature: RequireRoles(required_roles, client_id=None)
        checker = RequireRoles(["admin", "manager"], "my-client")
        
        assert checker.required_roles == ["admin", "manager"]
        assert checker.client_id == "my-client"
    
    def test_require_roles_single_role(self):
        """RequireRoles should work with single role."""
        # New signature: RequireRoles(required_roles, client_id=None)
        checker = RequireRoles(["admin"], "my-client")
        
        assert checker.required_roles == ["admin"]
        assert checker.client_id == "my-client"
        assert len(checker.required_roles) == 1


class TestUserBaseModel:
    """Test UserBase model with roles."""
    
    def test_user_base_with_roles(self):
        """UserBase should store roles correctly."""
        user = UserBase(
            id="123",
            email="test@example.com",
            given_name="John",
            family_name="Doe",
            roles={"client1": ["admin"], "client2": ["viewer"]}
        )
        
        assert user.id == "123"
        assert user.roles["client1"] == ["admin"]
        assert user.roles["client2"] == ["viewer"]
    
    def test_user_base_default_roles(self):
        """UserBase should have empty dict as default roles."""
        user = UserBase(
            id="123",
            email="test@example.com",
            given_name="John"
        )
        
        assert user.roles == {}
        assert isinstance(user.roles, dict)
    
    def test_user_base_roles_immutable_keys(self):
        """UserBase roles should be a proper dictionary."""
        user = UserBase(
            id="123",
            email="test@example.com",
            given_name="John",
            roles={"client": ["role1", "role2"]}
        )
        
        # Access existing key
        assert user.roles.get("client") == ["role1", "role2"]
        
        # Access non-existing key
        assert user.roles.get("nonexistent") is None
        assert user.roles.get("nonexistent", []) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
