"""Improved RBAC examples demonstrating best practices.

This shows the enhanced RBAC features including:
- Default client ID support (no need to specify for every endpoint)
- Helper methods on UserBase for role checking
- AND/OR logic for roles
- Cleaner syntax
"""
from fastapi import Depends, FastAPI

from fastapi_otel_common.core.models import UserBase
from fastapi_otel_common.security.auth import (
    RequireAllRoles,
    RequireRoles,
    get_current_user,
)

app = FastAPI(title="Improved RBAC Example")


# ==============================================================================
# PATTERN 1: Using default client ID (from OIDC_CLIENT_ID env var)
# ==============================================================================
# For example, if OIDC_CLIENT_ID=my-client-id, it will check resource_access.my-client-id.roles

@app.get(
    "/admin/reports",
    dependencies=[Depends(RequireRoles(["admin", "report-viewer"]))],
)
async def get_reports():
    """Endpoint accessible to users with 'admin' OR 'report-viewer' role.
    
    Uses default client ID from OIDC_CLIENT_ID config (e.g., 'my-client-id').
    No need to specify client_id in every route!
    """
    return {"message": "Admin reports data", "reports": []}


@app.get("/admin/users")
async def get_users(user: UserBase = Depends(RequireRoles(["admin", "user-manager"]))):
    """Endpoint with user object and default client ID.
    
    Cleaner syntax - roles list comes first, client_id is optional.
    """
    return {
        "message": f"User list accessed by {user.given_name}",
        "accessed_by": user.email,
        "users": [],
    }


# ==============================================================================
# PATTERN 2: Using UserBase helper methods for complex role logic
# ==============================================================================

@app.get("/dashboard")
async def get_dashboard(current_user: UserBase = Depends(get_current_user)):
    """Endpoint with custom role checking logic using helper methods.
    
    Shows how to use has_role(), has_any_role(), has_all_roles() methods.
    """
    # Check for specific role using default client
    is_admin = current_user.has_role("admin")
    
    # Check for any of multiple roles
    can_view = current_user.has_any_role(["viewer", "editor", "admin"])
    
    # Check for all roles (AND logic)
    is_power_user = current_user.has_all_roles(["admin", "auditor"])
    
    # Get all roles for default client
    user_roles = current_user.get_roles()
    
    return {
        "user_id": current_user.id,
        "is_admin": is_admin,
        "can_view": can_view,
        "is_power_user": is_power_user,
        "roles": user_roles,
    }


@app.post("/resources")
async def create_resource(current_user: UserBase = Depends(get_current_user)):
    """Custom business logic based on roles.
    
    Instead of using RequireRoles dependency, handle complex logic manually.
    """
    # Example: Different behavior based on roles
    if current_user.has_role("admin"):
        # Admins can create any resource
        return {"message": "Resource created (admin)", "created_by": current_user.id}
    elif current_user.has_role("editor"):
        # Editors have limited permissions
        return {"message": "Resource created (limited)", "created_by": current_user.id}
    else:
        # No permission
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create resources"
        )


# ==============================================================================
# PATTERN 3: Require ALL roles (AND logic)
# ==============================================================================

@app.delete("/admin/audit-logs")
async def delete_audit_logs(
    user: UserBase = Depends(RequireAllRoles(["admin", "auditor"]))
):
    """Endpoint requiring BOTH admin AND auditor roles.
    
    User must have all specified roles (AND logic).
    """
    return {
        "message": "Audit logs deleted",
        "executed_by": user.email,
    }


@app.post("/admin/system/reset")
async def system_reset(
    user: UserBase = Depends(RequireAllRoles(["super-admin", "system-operator"]))
):
    """Critical operation requiring multiple roles."""
    return {
        "message": "System reset initiated",
        "executed_by": user.id,
    }


# ==============================================================================
# PATTERN 4: Specific client ID (when needed)
# ==============================================================================

@app.get("/client-a/resources")
async def get_client_a_resources(
    user: UserBase = Depends(RequireRoles(["viewer", "admin"], "client-a"))
):
    """Endpoint for a specific client ID (not the default).
    
    Useful when you have multiple clients and need to check roles for a specific one.
    """
    # You can also check roles for other clients
    client_a_roles = user.get_roles("client-a")
    client_b_roles = user.get_roles("client-b")
    
    return {
        "message": "Client A resources",
        "client_a_roles": client_a_roles,
        "client_b_roles": client_b_roles,
    }


@app.get("/realm/settings")
async def get_realm_settings(user: UserBase = Depends(RequireRoles(["realm-admin"], "realm"))):
    """Endpoint for realm-level roles (not client-specific).
    
    Realm roles are extracted from 'realm_access' in the JWT token.
    """
    return {
        "message": "Realm settings",
        "settings": {},
    }


# ==============================================================================
# PATTERN 5: Inspecting all user roles
# ==============================================================================

@app.get("/profile")
async def get_profile(current_user: UserBase = Depends(get_current_user)):
    """Shows all user information and roles from all clients."""
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "name": f"{current_user.given_name} {current_user.family_name}",
        "all_roles_by_client": current_user.roles,  # Dict[client_id, List[roles]]
        "all_roles_flat": current_user.get_all_roles_flat(),  # Flattened list
        "default_client_roles": current_user.get_roles(),  # Roles for default client
    }


# ==============================================================================
# PATTERN 6: Combined requirements (multiple dependencies)
# ==============================================================================

@app.post("/admin/critical-action")
async def critical_action(
    user: UserBase = Depends(RequireAllRoles(["admin", "auditor"])),
):
    """Endpoint with multiple role requirements.
    
    This uses RequireAllRoles to ensure user has ALL required roles.
    You could also stack multiple dependencies if needed.
    """
    return {
        "message": "Critical action performed",
        "user": user.email,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
