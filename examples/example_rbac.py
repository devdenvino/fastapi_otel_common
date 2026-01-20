"""Example demonstrating role-based access control (RBAC) with client IDs.

This example shows how to use the RequireRoles dependency to protect endpoints
based on client-specific roles from JWT tokens.
"""
from fastapi import Depends, FastAPI

from fastapi_otel_common.core.models import UserBase
from fastapi_otel_common.security.auth import RequireRoles, get_current_user

app = FastAPI(title="RBAC Example")


# Example 1: Protect endpoint with role check (no user object needed)
@app.get(
    "/admin/reports",
    dependencies=[Depends(RequireRoles("my-client-id", ["admin", "report-viewer"]))],
)
async def get_reports():
    """Endpoint accessible to users with 'admin' OR 'report-viewer' role for 'my-client-id'.
    
    At least one of the specified roles must be present.
    """
    return {"message": "Admin reports data", "reports": []}


# Example 2: Protect endpoint and get user object
@app.get("/admin/users")
async def get_users(
    user: UserBase = Depends(RequireRoles("my-client-id", ["admin", "user-manager"]))
):
    """Endpoint accessible to users with 'admin' OR 'user-manager' role.
    
    The user object is available for additional logic.
    """
    return {
        "message": f"User list accessed by {user.given_name}",
        "accessed_by": user.email,
        "users": [],
    }


# Example 3: Multiple role checks for different client IDs
@app.post("/resources")
async def create_resource(
    user: UserBase = Depends(RequireRoles("client-a", ["editor", "admin"]))
):
    """Endpoint accessible to users with specific roles for 'client-a'."""
    return {
        "message": "Resource created",
        "created_by": user.id,
    }


# Example 4: Realm-level roles (not client-specific)
@app.get("/realm/settings")
async def get_realm_settings(
    user: UserBase = Depends(RequireRoles("realm", ["realm-admin"]))
):
    """Endpoint accessible to users with realm-level admin role.
    
    Realm roles are extracted from 'realm_access' in the JWT token.
    """
    return {
        "message": "Realm settings",
        "settings": {},
    }


# Example 5: Combining with standard authentication
@app.get("/profile")
async def get_profile(current_user: UserBase = Depends(get_current_user)):
    """Standard endpoint that just requires authentication (no specific roles).
    
    This shows the user's roles from all clients.
    """
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "name": f"{current_user.given_name} {current_user.family_name}",
        "roles": current_user.roles,  # Shows all client-to-roles mappings
    }


# Example 6: Strict single role requirement
@app.delete("/admin/system")
async def dangerous_operation(
    user: UserBase = Depends(RequireRoles("my-client-id", ["super-admin"]))
):
    """Endpoint requiring a very specific role."""
    return {
        "message": "Dangerous operation executed",
        "executed_by": user.email,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
