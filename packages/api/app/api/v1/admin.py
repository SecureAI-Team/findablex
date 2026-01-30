"""Admin routes (super_admin only)."""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.deps import get_current_superuser, get_db
from app.models.audit import AuditLog
from app.models.user import User, INDUSTRIES, BUSINESS_ROLES, REGIONS
from app.models.workspace import Tenant, Workspace, Membership

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


# ========== User Management Schemas ==========

class UserListResponse(BaseModel):
    """Schema for user in list response."""
    id: UUID
    email: str
    full_name: Optional[str]
    company_name: Optional[str]
    industry: Optional[str]
    business_role: Optional[str]
    is_active: bool
    is_superuser: bool
    email_verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    workspace_count: int = 0
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserListResponse):
    """Schema for user detail response with memberships."""
    memberships: List[dict] = []


class UserUpdateRequest(BaseModel):
    """Schema for updating user."""
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    business_role: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserListPaginated(BaseModel):
    """Paginated user list response."""
    items: List[UserListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ResetPasswordResponse(BaseModel):
    """Response for password reset."""
    message: str
    temporary_password: str


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


# ========== User Management Endpoints ==========

@router.get("/users", response_model=UserListPaginated)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_superuser: Optional[bool] = None,
    industry: Optional[str] = None,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> UserListPaginated:
    """List all users with pagination and filtering."""
    # Base query
    query = select(User)
    count_query = select(func.count(User.id))
    
    # Apply filters
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%"),
            User.company_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    if is_superuser is not None:
        query = query.where(User.is_superuser == is_superuser)
        count_query = count_query.where(User.is_superuser == is_superuser)
    
    if industry:
        query = query.where(User.industry == industry)
        count_query = count_query.where(User.industry == industry)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get workspace counts for each user
    user_list = []
    for user in users:
        # Count memberships
        membership_count = await db.execute(
            select(func.count(Membership.id)).where(Membership.user_id == user.id)
        )
        ws_count = membership_count.scalar() or 0
        
        user_list.append(UserListResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            industry=user.industry,
            business_role=user.business_role,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            email_verified_at=user.email_verified_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            workspace_count=ws_count,
        ))
    
    total_pages = (total + page_size - 1) // page_size
    
    return UserListPaginated(
        items=user_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """Get user details by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get memberships with workspace info
    membership_result = await db.execute(
        select(Membership, Workspace)
        .join(Workspace, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user_id)
    )
    
    memberships = []
    for row in membership_result:
        membership = row[0]
        workspace = row[1]
        memberships.append({
            "workspace_id": str(workspace.id),
            "workspace_name": workspace.name,
            "role": membership.role,
            "joined_at": membership.created_at.isoformat() if membership.created_at else None,
        })
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        industry=user.industry,
        business_role=user.business_role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        email_verified_at=user.email_verified_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        workspace_count=len(memberships),
        memberships=memberships,
    )


@router.put("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """Update user details."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prevent self-demotion from superuser
    if user_id == current_user.id and data.is_superuser is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own superuser status",
        )
    
    # Prevent self-deactivation
    if user_id == current_user.id and data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )
    
    # Update fields
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.company_name is not None:
        user.company_name = data.company_name
    if data.industry is not None:
        user.industry = data.industry
    if data.business_role is not None:
        user.business_role = data.business_role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_superuser is not None:
        user.is_superuser = data.is_superuser
    
    await db.commit()
    await db.refresh(user)
    
    # Return updated user with memberships
    return await get_user(user_id, current_user, db)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a user."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Delete the user (memberships will cascade)
    await db.delete(user)
    await db.commit()
    
    return {"message": f"User {user.email} has been deleted"}


@router.post("/users/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_user_password(
    user_id: UUID,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> ResetPasswordResponse:
    """Reset user password to a random temporary password."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Generate a random temporary password
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    # Hash and save the new password
    user.hashed_password = hash_password(temp_password)
    await db.commit()
    
    return ResetPasswordResponse(
        message=f"Password has been reset for {user.email}",
        temporary_password=temp_password,
    )
