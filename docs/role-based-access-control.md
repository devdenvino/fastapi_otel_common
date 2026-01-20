# Role-Based Access Control (RBAC)

## Overview

The RBAC system provides role-based access control for FastAPI endpoints using client-specific roles from JWT tokens. It supports:
- **Default client ID** configuration (no need to repeat client_id in every route)
- **OR logic** (`RequireRoles`) - user needs at least one role
- **AND logic** (`RequireAllRoles`) - user needs all roles
- **Helper methods** on UserBase for custom role checking logic
- Multiple client contexts within the same application

## How It Works

### JWT Token Structure

The system extracts roles from JWT tokens following the Keycloak format:

```json
{
  "sub": "user-id",
  "email": "user@example.com",
  "resource_access": {
    "my-client-id": {
      "roles": ["admin", "editor", "viewer"]
    },
    "another-client": {
      "roles": ["user"]
    }
  },
  "realm_access": {
    "roles": ["realm-admin", "user"]
  }
}
```

### Role Storage

Roles are stored in the `UserBase` model as a dictionary mapping client IDs to role lists:

```python
user.roles = {
    "my-client-id": ["admin", "editor", "viewer"],
    "another-client": ["user"],
    "realm": ["realm-admin", "user"]
}
```

## Configuration

### Default Client ID

Set the `OIDC_CLIENT_ID` environment variable to your default client ID:

```bash
OIDC_CLIENT_ID=my-client-id
```

This allows you to use `RequireRoles` without specifying the client ID repeatedly:

```python
# Instead of RequireRoles("my-client-id", ["admin"])
# You can use:
RequireRoles(["admin"])
```

For a client ID like `my-client-id`, roles are extracted from `resource_access.my-client-id.roles` in the JWT token.

## Usage Patterns

### Pattern 1: Default Client ID (Recommended)

Protect an endpoint using the default client ID from configuration:

```python
from fastapi import Depends, FastAPI
from fastapi_otel_common.security.auth import RequireRoles

app = FastAPI()

@app.get(
    "/admin/dashboard",
    dependencies=[Depends(RequireRoles(["admin", "manager"]))]
)
async def admin_dashboard():
    """Accessible if user has 'admin' OR 'manager' role (OR logic)"""
    return {"message": "Welcome to admin dashboard"}
```

### Pattern 2: Getting User Object

If you need the user object for additional logic:

```python
from fastapi_otel_common.core.models import UserBase
from fastapi_otel_common.security.auth import RequireRoles

@app.get("/admin/settings")
async def admin_settings(user: UserBase = Depends(RequireRoles(["admin"]))):
    """Access the user object after role verification"""
    return {
        "message": f"Settings for {user.email}",
        "user_roles": user.get_roles()  # Get roles for default client
    }
```

### Pattern 3: Specific Client ID

Check roles for a specific client ID (when different from default):

```python
@app.get("/client-a/data")
async def client_a_data(
    user: UserBase = Depends(RequireRoles(["viewer", "editor"], "client-a"))
):
    return {"data": "Client A data"}

@app.get("/realm/settings")
async def realm_settings(
    user: UserBase = Depends(RequireRoles(["realm-admin"], "realm"))
):
    """Check realm-level roles"""
    return {"settings": {}}
```

### Pattern 4: Require ALL Roles (AND Logic)

Use `RequireAllRoles` when user must have ALL specified roles:

```python
from fastapi_otel_common.security.auth import RequireAllRoles

@app.delete("/admin/audit-logs")
async def delete_audit_logs(
    user: UserBase = Depends(RequireAllRoles(["admin", "auditor"]))
):
    """User must have BOTH 'admin' AND 'auditor' roles"""
    return {"message": "Audit logs deleted"}
```

### Pattern 5: Custom Role Logic with Helper Methods

For complex role checking, use UserBase helper methods:

```python
from fastapi_otel_common.security.auth import get_current_user

@app.post("/resources")
async def create_resource(current_user: UserBase = Depends(get_current_user)):
    """Custom business logic based on roles"""
    
    # Check for specific role
    if current_user.has_role("admin"):
        # Admin logic
        pass
    
    # Check for any of multiple roles (OR logic)
    elif current_user.has_any_role(["editor", "contributor"]):
        # Limited permissions
        pass
    
    # Check for all roles (AND logic)
    elif current_user.has_all_roles(["reviewer", "publisher"]):
        # Multiple roles required
        pass
    
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return {"message": "Resource created"}
```

### Pattern 6: Inspecting User Roles

Access and display user roles:

```python
@app.get("/profile")
async def get_profile(current_user: UserBase = Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        # All roles organized by client
        "all_roles_by_client": current_user.roles,
        # Flattened list of all roles
        "all_roles_flat": current_user.get_all_roles_flat(),
        # Roles for default client only
        "default_client_roles": current_user.get_roles(),
        # Roles for specific client
        "client_a_roles": current_user.get_roles("client-a")
    }
```

### Pattern 7: Complex AND/OR Conditions (Industry Standard)

For advanced authorization scenarios requiring complex boolean logic:

```python
from fastapi_otel_common.security.auth import (
    RequireRolesComplex,
    AnyRole,
    AllRoles,
    AnyCondition,
    AllConditions
)

# Example 1: (admin AND auditor) OR superadmin
@app.delete("/critical-data")
async def delete_critical_data(
    user: UserBase = Depends(RequireRolesComplex(
        AnyCondition(
            AllRoles(["admin", "auditor"]),  # Must have both admin AND auditor
            AnyRole(["superadmin"])           # OR just superadmin
        )
    ))
):
    """User needs either (admin AND auditor) OR superadmin"""
    return {"message": "Critical data deleted"}

# Example 2: (admin OR manager) AND (editor OR publisher)
@app.post("/content/publish")
async def publish_content(
    user: UserBase = Depends(RequireRolesComplex(
        AllConditions(
            AnyRole(["admin", "manager"]),     # Must have admin OR manager
            AnyRole(["editor", "publisher"])   # AND editor OR publisher
        )
    ))
):
    """User must have (admin OR manager) AND (editor OR publisher)"""
    return {"message": "Content published"}

# Example 3: Complex nested conditions
@app.put("/system/config")
async def update_system_config(
    user: UserBase = Depends(RequireRolesComplex(
        AnyCondition(
            AllRoles(["admin", "system-operator"]),
            AllRoles(["manager", "tech-lead"]),
            AnyRole(["superadmin"])
        )
    ))
):
    """User needs one of:
    - admin AND system-operator
    - manager AND tech-lead
    - superadmin (alone)
    """
    return {"message": "System config updated"}
```

**Available Conditions:**
- `AnyRole(["role1", "role2"])` - OR logic: user has at least one role
- `AllRoles(["role1", "role2"])` - AND logic: user has all roles
- `AnyCondition(cond1, cond2)` - OR logic: at least one condition satisfied
- `AllConditions(cond1, cond2)` - AND logic: all conditions satisfied

**Why Use Complex Conditions?**
This is an **industry standard** approach used in enterprise systems for:
- Regulatory compliance (finance, healthcare, government)
- Multi-tier authorization (approval workflows)
- Separation of duties (SOX, PCI-DSS compliance)
- Role-based access control with multiple dimensions

See [example_rbac_complex.py](../examples/example_rbac_complex.py) for 10+ real-world patterns.

### Realm-Level Roles

Check for realm-level roles (not client-specific):

```python
@app.get("/system/config")
async def system_config(
    user: UserBase = Depends(RequireRoles(["realm-admin"], "realm"))
):
    """Accessible to realm administrators"""
    return {"config": "system configuration"}
```

### Single Required Role

Require a specific single role:

```python
@app.delete("/system/reset")
async def system_reset(
    user: UserBase = Depends(RequireRoles(["super-admin"]))
):
    """Only super-admin can access this"""
    return {"message": "System reset initiated"}
```

## API Reference

### RequireRoles Class

```python
class RequireRoles:
    def __init__(self, required_roles: List[str], client_id: str = None)
```

**Parameters:**
- `required_roles` (List[str]): List of role names - user must have at least ONE of these roles (OR logic)
- `client_id` (str, optional): The client ID to check roles for. Defaults to `OIDC_CLIENT_ID` from environment

**Returns:**
- `UserBase`: The authenticated user object with verified roles

**Raises:**
- `HTTPException 401`: If user is not authenticated
- `HTTPException 403`: If user doesn't have any of the required roles

### RequireAllRoles Class

```python
class RequireAllRoles:
    def __init__(self, required_roles: List[str], client_id: str = None)
```

**Parameters:**
- `required_roles` (List[str]): List of role names - user must have ALL of these roles (AND logic)
- `client_id` (str, optional): The client ID to check roles for. Defaults to `OIDC_CLIENT_ID` from environment

**Returns:**
- `UserBase`: The authenticated user object with verified roles

**Raises:**
- `HTTPException 401`: If user is not authenticated
- `HTTPException 403`: If user doesn't have all of the required roles

### RequireRolesComplex Class (Industry Standard)

```python
class RequireRolesComplex:
    def __init__(self, condition: RoleCondition, client_id: str = None)
```

**Parameters:**
- `condition` (RoleCondition): Complex role condition using boolean logic
- `client_id` (str, optional): The client ID to check roles for. Defaults to `OIDC_CLIENT_ID` from environment

**Returns:**
- `UserBase`: The authenticated user object with verified roles

**Raises:**
- `HTTPException 401`: If user is not authenticated
- `HTTPException 403`: If user doesn't satisfy the role condition

#### Role Condition Classes

```python
# Basic conditions
AnyRole(["role1", "role2"])        # OR: has at least one role
AllRoles(["role1", "role2"])       # AND: has all roles

# Nested conditions
AnyCondition(cond1, cond2, ...)    # OR: at least one condition satisfied
AllConditions(cond1, cond2, ...)   # AND: all conditions satisfied
```

**Example Combinations:**
```python
# (admin AND auditor) OR superadmin
AnyCondition(
    AllRoles(["admin", "auditor"]),
    AnyRole(["superadmin"])
)

# (admin OR manager) AND (editor OR publisher)
AllConditions(
    AnyRole(["admin", "manager"]),
    AnyRole(["editor", "publisher"])
)
```

### UserBase Model

```python
class UserBase(BaseModel):
    id: str                              # User ID
    email: str                           # User email
    given_name: str                      # First name
    family_name: Optional[str]           # Last name
    is_admin: bool = False              # Admin flag
    roles: Dict[str, List[str]] = {}    # Client ID to roles mapping
```

#### UserBase Helper Methods

```python
def has_role(self, role: str, client_id: str = None) -> bool:
    """Check if user has a specific role for a client."""

def has_any_role(self, roles: List[str], client_id: str = None) -> bool:
    """Check if user has any of the specified roles (OR logic)."""

def has_all_roles(self, roles: List[str], client_id: str = None) -> bool:
    """Check if user has all of the specified roles (AND logic)."""

def get_roles(self, client_id: str = None) -> List[str]:
    """Get user's roles for a specific client."""

def get_all_roles_flat(self) -> List[str]:
    """Get all roles from all clients as a flat list."""
```

All methods default to using `OIDC_CLIENT_ID` from environment if `client_id` is not provided.

## Error Responses

### 401 Unauthorized
User is not authenticated (no valid JWT token):
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
User doesn't have required roles:
```json
{
  "detail": "Insufficient permissions. Required roles: ['admin', 'manager'] for client: my-client-id"
}
```

## Advanced Patterns

### Combining Multiple Dependencies

```python
from fastapi import Depends, FastAPI
from fastapi_otel_common.security.auth import RequireRoles, get_current_user

@app.post("/projects/{project_id}/data")
async def update_project(
    project_id: str,
    user: UserBase = Depends(RequireRoles(["editor", "admin"]))  # Uses default client
):
    """User needs editor or admin role AND can access user info"""
    # Additional authorization logic based on project_id
    if not user_can_access_project(user.id, project_id):
        raise HTTPException(403, "Cannot access this project")
    
    return {"message": "Project updated"}
```

### Dynamic Role Checking

For runtime role checking (not at endpoint level):

```python
@app.get("/resources/{resource_id}")
async def get_resource(
    resource_id: str,
    user: UserBase = Depends(get_current_user)
):
    """Check roles dynamically based on resource"""
    resource = get_resource_by_id(resource_id)
    required_client = resource.client_id
    
    # Use helper method for clean checking
    if not user.has_any_role(["viewer", "admin"], required_client):
        raise HTTPException(403, "Insufficient permissions for this resource")
    
    return {"resource": resource}
```

### Conditional Logic Based on Roles

```python
@app.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    user: UserBase = Depends(get_current_user)
):
    """Different behavior based on user roles"""
    document = get_document_by_id(doc_id)
    
    if user.has_role("admin"):
        # Admin sees everything
        return {"document": document, "full_access": True}
    elif user.has_role("editor"):
        # Editors see most things but not metadata
        return {"document": document, "full_access": False}
    elif user.has_role("viewer"):
        # Viewers see limited info
        return {"document": {"id": doc_id, "title": document.title}}
    else:
        raise HTTPException(403, "Insufficient permissions")
```

### Logging and Auditing

The role checker logs warnings when access is denied:

```
WARNING: User abc-123 attempted to access resource requiring roles ['admin'] 
for client my-client-id, but has roles: ['viewer', 'editor']
```

## Best Practices

1. **Use Default Client ID**: Set `OIDC_CLIENT_ID` environment variable and omit `client_id` parameter in most routes for cleaner code

2. **Minimal Roles**: Only specify the minimum roles needed for access

3. **OR vs AND Logic**: 
   - Use `RequireRoles` for "any of these roles" (most common)
   - Use `RequireAllRoles` for "all of these roles" (stricter)

4. **Helper Methods for Complex Logic**: Use `UserBase` helper methods (`has_role`, `has_any_role`, `has_all_roles`) for conditional business logic

5. **Combine with Business Logic**: Use role checks as the first line of defense, then add resource-specific authorization

6. **Document Required Roles**: Add clear docstrings to your endpoints about which roles are needed

7. **Test Different Scenarios**: Test with users having various role combinations

## Migration from Old Syntax

If you're upgrading from the old syntax where `client_id` was the first parameter:

**Old syntax:**
```python
RequireRoles("my-client-id", ["admin", "manager"])
```

**New syntax:**
```python
# With default client ID from config
RequireRoles(["admin", "manager"])

# Or with specific client ID
RequireRoles(["admin", "manager"], "my-client-id")
```

## Testing

Create test tokens with different roles:

```python
import pytest
from fastapi.testclient import TestClient

def test_admin_access_with_admin_role(client: TestClient):
    """User with admin role can access admin endpoint"""
    token = create_test_token(roles={"my-client-id": ["admin"]})  # Use your client ID
    response = client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

def test_admin_access_without_role(client: TestClient):
    """User without admin role cannot access admin endpoint"""
    token = create_test_token(roles={"my-client-id": ["viewer"]})
    response = client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
```

## Troubleshooting

### Roles Not Being Extracted

1. Check your JWT token structure matches the expected format
2. Verify `resource_access` contains your client ID
3. Check the `roles` array exists under your client ID
4. Enable debug logging to see token payload

### 403 Forbidden for Valid Users

1. Verify the client ID matches exactly (case-sensitive)
2. Check role names match exactly (case-sensitive)
3. Review the warning logs for actual vs. required roles
4. Confirm JWT token contains the expected roles

### Custom Token Structure

If your OAuth2 provider uses a different structure, modify the role extraction in `validate_token_and_get_user`:

```python
# Custom structure: {"permissions": {"client": ["role1", "role2"]}}
permissions = payload.get("permissions", {})
if isinstance(permissions, dict):
    for client_id, role_list in permissions.items():
        roles[client_id] = role_list
```
