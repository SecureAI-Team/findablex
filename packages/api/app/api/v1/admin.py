"""Admin routes (super_admin only)."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_superuser, get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.models.workspace import Tenant, Workspace

router = APIRouter()


class TenantResponse(BaseModel):
    """Schema for tenant response."""
    id: UUID
    name: str
    plan: str
    workspace_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    id: UUID
    workspace_id: Optional[UUID]
    user_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PlatformStats(BaseModel):
    """Schema for platform statistics."""
    total_users: int
    active_users_7d: int
    total_workspaces: int
    total_projects: int
    total_runs: int
    runs_last_7d: int


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> List[TenantResponse]:
    """List all tenants."""
    result = await db.execute(
        select(
            Tenant,
            func.count(Workspace.id).label("workspace_count"),
        )
        .outerjoin(Workspace)
        .group_by(Tenant.id)
        .order_by(Tenant.created_at.desc())
    )
    
    tenants = []
    for row in result:
        tenant = row[0]
        workspace_count = row[1]
        tenants.append(
            TenantResponse(
                id=tenant.id,
                name=tenant.name,
                plan=tenant.plan,
                workspace_count=workspace_count,
                created_at=tenant.created_at,
            )
        )
    
    return tenants


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    workspace_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> List[AuditLogResponse]:
    """List audit logs with filtering."""
    query = select(AuditLog)
    
    if workspace_id:
        query = query.where(AuditLog.workspace_id == workspace_id)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [
        AuditLogResponse(
            id=log.id,
            workspace_id=log.workspace_id,
            user_id=log.user_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/stats", response_model=PlatformStats)
async def get_stats(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> PlatformStats:
    """Get platform statistics."""
    from app.models.project import Project
    from app.models.run import Run
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Total users
    total_users = await db.execute(select(func.count(User.id)))
    
    # Active users (logged in last 7 days - approximated by updated_at)
    active_users = await db.execute(
        select(func.count(User.id)).where(User.updated_at >= seven_days_ago)
    )
    
    # Total workspaces
    total_workspaces = await db.execute(select(func.count(Workspace.id)))
    
    # Total projects
    total_projects = await db.execute(select(func.count(Project.id)))
    
    # Total runs
    total_runs = await db.execute(select(func.count(Run.id)))
    
    # Runs in last 7 days
    recent_runs = await db.execute(
        select(func.count(Run.id)).where(Run.created_at >= seven_days_ago)
    )
    
    return PlatformStats(
        total_users=total_users.scalar() or 0,
        active_users_7d=active_users.scalar() or 0,
        total_workspaces=total_workspaces.scalar() or 0,
        total_projects=total_projects.scalar() or 0,
        total_runs=total_runs.scalar() or 0,
        runs_last_7d=recent_runs.scalar() or 0,
    )
