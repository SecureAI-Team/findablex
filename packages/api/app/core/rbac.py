"""Role-Based Access Control (RBAC) implementation."""
from enum import Enum
from typing import List, Set

from fastapi import HTTPException, status


class Role(str, Enum):
    """User roles in the system."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class Permission(str, Enum):
    """System permissions."""
    # Platform
    PLATFORM_MANAGE = "platform:manage"
    
    # Tenant
    TENANT_CREATE = "tenant:create"
    TENANT_DELETE = "tenant:delete"
    
    # Workspace
    WORKSPACE_MANAGE = "workspace:manage"
    WORKSPACE_VIEW = "workspace:view"
    WORKSPACE_SETTINGS = "workspace:settings"
    
    # Members
    MEMBER_INVITE = "member:invite"
    MEMBER_REMOVE = "member:remove"
    MEMBER_CHANGE_ROLE = "member:change_role"
    
    # Projects
    PROJECT_CREATE = "project:create"
    PROJECT_VIEW = "project:view"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"
    
    # Runs
    RUN_CREATE = "run:create"
    RUN_VIEW = "run:view"
    
    # Reports
    REPORT_VIEW = "report:view"
    REPORT_SHARE = "report:share"
    
    # Export
    EXPORT_OWN = "export:own"
    EXPORT_ANONYMIZED = "export:anonymized"
    
    # Crawler
    CRAWLER_TRIGGER = "crawler:trigger"
    CRAWLER_MANAGE = "crawler:manage"
    
    # Audit
    AUDIT_VIEW = "audit:view"
    AUDIT_VIEW_ALL = "audit:view_all"
    
    # Settings
    SETTINGS_MANAGE = "settings:manage"
    SETTINGS_VIEW = "settings:view"


# Role-Permission mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: {
        Permission.PLATFORM_MANAGE,
        Permission.TENANT_CREATE,
        Permission.TENANT_DELETE,
        Permission.WORKSPACE_MANAGE,
        Permission.WORKSPACE_VIEW,
        Permission.WORKSPACE_SETTINGS,
        Permission.MEMBER_INVITE,
        Permission.MEMBER_REMOVE,
        Permission.MEMBER_CHANGE_ROLE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_DELETE,
        Permission.RUN_CREATE,
        Permission.RUN_VIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_SHARE,
        Permission.EXPORT_OWN,
        Permission.EXPORT_ANONYMIZED,
        Permission.CRAWLER_TRIGGER,
        Permission.CRAWLER_MANAGE,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_VIEW_ALL,
        Permission.SETTINGS_MANAGE,
        Permission.SETTINGS_VIEW,
    },
    Role.ADMIN: {
        Permission.WORKSPACE_MANAGE,
        Permission.WORKSPACE_VIEW,
        Permission.WORKSPACE_SETTINGS,
        Permission.MEMBER_INVITE,
        Permission.MEMBER_REMOVE,
        Permission.MEMBER_CHANGE_ROLE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_DELETE,
        Permission.RUN_CREATE,
        Permission.RUN_VIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_SHARE,
        Permission.EXPORT_OWN,
        Permission.AUDIT_VIEW,
    },
    Role.ANALYST: {
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_EDIT,
        Permission.RUN_CREATE,
        Permission.RUN_VIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_SHARE,
        Permission.EXPORT_OWN,
    },
    Role.RESEARCHER: {
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.RUN_VIEW,
        Permission.REPORT_VIEW,
        Permission.EXPORT_ANONYMIZED,
        Permission.CRAWLER_TRIGGER,
    },
    Role.VIEWER: {
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.RUN_VIEW,
        Permission.REPORT_VIEW,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_role_permissions(role)


def check_permission(role: Role, permission: Permission) -> None:
    """Check permission and raise HTTPException if not authorized."""
    if not has_permission(role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission.value}",
        )


def require_permissions(permissions: List[Permission]):
    """Decorator factory for permission-based route protection."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                )
            
            # Check permissions based on user's role
            user_role = Role(current_user.role) if hasattr(current_user, "role") else Role.VIEWER
            
            for permission in permissions:
                if not has_permission(user_role, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission.value}",
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(permission: Permission):
    """
    Dependency for permission-based route protection.
    
    Usage:
        @router.get("/")
        async def get_items(
            current_user: User = Depends(require_permission(Permission.ITEM_VIEW))
        ):
            ...
    """
    from fastapi import Depends
    from app.deps import get_current_user
    
    async def permission_checker(
        current_user = Depends(get_current_user),
    ):
        # Super admin has all permissions
        if current_user.is_superuser:
            return current_user
        
        # Check permission based on user's workspace role
        # For now, check if user is superuser for settings management
        if permission == Permission.SETTINGS_MANAGE and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        
        return current_user
    
    return permission_checker
