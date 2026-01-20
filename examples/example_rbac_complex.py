"""Complex RBAC examples with AND/OR conditions.

Industry-standard approach for complex authorization scenarios.
Demonstrates how to combine multiple role conditions using boolean logic.
"""
from fastapi import Depends, FastAPI

from fastapi_otel_common.core.models import UserBase
from fastapi_otel_common.security.auth import (
    AllConditions,
    AllRoles,
    AnyCondition,
    AnyRole,
    RequireRolesComplex,
    get_current_user,
)

app = FastAPI(title="Complex RBAC Example")


# ==============================================================================
# PATTERN 1: Simple OR - User needs ANY of these roles
# ==============================================================================
# This is equivalent to RequireRoles(["admin", "manager"])

@app.get("/dashboard/view1")
async def simple_or(
    user: UserBase = Depends(RequireRolesComplex(AnyRole(["admin", "manager"])))
):
    """User needs admin OR manager role."""
    return {"message": "Access granted with OR logic"}


# ==============================================================================
# PATTERN 2: Simple AND - User needs ALL of these roles
# ==============================================================================
# This is equivalent to RequireAllRoles(["admin", "auditor"])

@app.delete("/audit-logs/delete1")
async def simple_and(
    user: UserBase = Depends(RequireRolesComplex(AllRoles(["admin", "auditor"])))
):
    """User needs BOTH admin AND auditor roles."""
    return {"message": "Audit logs deleted"}


# ==============================================================================
# PATTERN 3: (Role1 AND Role2) OR Role3
# ==============================================================================
# Common pattern: Either have multiple roles OR be a superadmin

@app.delete("/critical/operation1")
async def and_or_pattern(
    user: UserBase = Depends(RequireRolesComplex(
        AnyCondition(
            AllRoles(["admin", "auditor"]),  # (admin AND auditor)
            AnyRole(["superadmin"])           # OR superadmin
        )
    ))
):
    """User needs either:
    - BOTH admin AND auditor roles
    - OR just superadmin role
    """
    return {
        "message": "Critical operation performed",
        "user": user.email,
        "roles": user.get_roles()
    }


# ==============================================================================
# PATTERN 4: (Role1 OR Role2) AND (Role3 OR Role4)
# ==============================================================================
# User must satisfy BOTH conditions

@app.post("/content/publish")
async def or_and_or_pattern(
    user: UserBase = Depends(RequireRolesComplex(
        AllConditions(
            AnyRole(["admin", "manager"]),     # (admin OR manager)
            AnyRole(["editor", "publisher"])   # AND (editor OR publisher)
        )
    ))
):
    """User must have:
    - (admin OR manager) AND (editor OR publisher)
    
    Valid combinations:
    - admin + editor
    - admin + publisher
    - manager + editor
    - manager + publisher
    """
    return {
        "message": "Content published",
        "publisher": user.email
    }


# ==============================================================================
# PATTERN 5: Complex nested conditions
# ==============================================================================
# (Role1 AND Role2) OR (Role3 AND Role4) OR Role5

@app.put("/system/config")
async def complex_nested(
    user: UserBase = Depends(RequireRolesComplex(
        AnyCondition(
            AllRoles(["admin", "system-operator"]),  # (admin AND system-operator)
            AllRoles(["manager", "tech-lead"]),      # OR (manager AND tech-lead)
            AnyRole(["superadmin"])                   # OR superadmin
        )
    ))
):
    """User needs one of these combinations:
    - admin AND system-operator
    - manager AND tech-lead
    - superadmin (alone)
    """
    return {"message": "System configuration updated"}


# ==============================================================================
# PATTERN 6: Three-level nesting
# ==============================================================================
# ((Role1 OR Role2) AND Role3) OR Role4

@app.post("/data/import")
async def three_level_nesting(
    user: UserBase = Depends(RequireRolesComplex(
        AnyCondition(
            AllConditions(
                AnyRole(["data-engineer", "data-scientist"]),  # (data-engineer OR data-scientist)
                AnyRole(["write-access"])                       # AND write-access
            ),
            AnyRole(["data-admin"])  # OR data-admin
        )
    ))
):
    """User needs:
    - ((data-engineer OR data-scientist) AND write-access) OR data-admin
    
    Valid combinations:
    - data-engineer + write-access
    - data-scientist + write-access
    - data-admin (alone)
    """
    return {"message": "Data import initiated"}


# ==============================================================================
# PATTERN 7: Multiple role groups with AND
# ==============================================================================
# User must belong to multiple role groups

@app.post("/compliance/report")
async def multiple_groups(
    user: UserBase = Depends(RequireRolesComplex(
        AllConditions(
            AnyRole(["compliance-officer", "auditor", "legal"]),  # Must have at least one
            AnyRole(["report-viewer", "report-editor"]),          # AND at least one
            AnyRole(["certified", "approved"])                     # AND at least one
        )
    ))
):
    """User must have at least one role from EACH group:
    - One of: compliance-officer, auditor, legal
    - AND one of: report-viewer, report-editor
    - AND one of: certified, approved
    
    Example valid combination:
    - auditor + report-viewer + certified
    """
    return {"message": "Compliance report generated"}


# ==============================================================================
# PATTERN 8: Using with specific client IDs
# ==============================================================================

@app.get("/client-a/data")
async def specific_client(
    user: UserBase = Depends(RequireRolesComplex(
        AnyCondition(
            AllRoles(["admin", "data-viewer"]),
            AnyRole(["superadmin"])
        ),
        client_id="client-a"  # Check roles for specific client
    ))
):
    """Complex condition for specific client ID."""
    return {"message": "Client A data accessed"}


# ==============================================================================
# PATTERN 9: Mixing with regular authentication
# ==============================================================================

@app.get("/profile/advanced")
async def custom_logic(current_user: UserBase = Depends(get_current_user)):
    """Use helper methods for inline complex logic."""
    
    # Check complex conditions inline
    can_view_sensitive = (
        current_user.has_role("admin") or
        (current_user.has_role("manager") and current_user.has_role("auditor"))
    )
    
    can_edit = current_user.has_any_role(["admin", "editor"])
    
    can_delete = current_user.has_all_roles(["admin", "delete-permission"])
    
    return {
        "user": current_user.email,
        "permissions": {
            "can_view_sensitive": can_view_sensitive,
            "can_edit": can_edit,
            "can_delete": can_delete
        }
    }


# ==============================================================================
# PATTERN 10: Real-world example - Document management system
# ==============================================================================

@app.post("/documents/approve")
async def approve_document(
    user: UserBase = Depends(RequireRolesComplex(
        AllConditions(
            # Must be authorized to approve
            AnyRole(["approver", "senior-manager", "director"]),
            # AND must have appropriate clearance
            AnyRole(["clearance-level-2", "clearance-level-3"]),
            # AND must be certified
            AnyRole(["compliance-certified", "admin"])
        )
    ))
):
    """Real-world scenario: Document approval requires:
    - Approval authority (approver OR senior-manager OR director)
    - AND security clearance (level-2 OR level-3)
    - AND compliance certification (certified OR admin bypass)
    
    This is common in regulated industries (finance, healthcare, government).
    """
    return {
        "message": "Document approved",
        "approver": user.email,
        "timestamp": "2026-01-20T10:00:00Z"
    }


@app.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user: UserBase = Depends(RequireRolesComplex(
        AnyCondition(
            # Option 1: Superadmin can delete anything
            AnyRole(["superadmin"]),
            # Option 2: Must be admin AND have delete permission
            AllRoles(["admin", "delete-permission"]),
            # Option 3: Document owner with delete rights
            AllRoles(["document-owner", "delete-own"])
        )
    ))
):
    """Flexible deletion policy with multiple authorization paths."""
    return {
        "message": f"Document {doc_id} deleted",
        "deleted_by": user.email
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
