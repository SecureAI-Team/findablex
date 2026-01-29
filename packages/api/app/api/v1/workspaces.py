"""Workspace routes."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.project import Project
from app.models.run import Run
from app.schemas.workspace import (
    MembershipCreate,
    MembershipResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


class WorkspaceStatsResponse(BaseModel):
    """Response schema for workspace statistics."""
    projects_count: int
    runs_count: int
    completed_runs_count: int
    avg_health_score: Optional[float]


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[WorkspaceResponse]:
    """List all workspaces for current user."""
    workspace_service = WorkspaceService(db)
    workspaces = await workspace_service.get_user_workspaces(current_user.id)
    return workspaces


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """Create a new workspace."""
    workspace_service = WorkspaceService(db)
    
    # Check if slug already exists
    existing = await workspace_service.get_by_slug(data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace slug already exists",
        )
    
    workspace = await workspace_service.create(data, current_user)
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """Get workspace by ID."""
    workspace_service = WorkspaceService(db)
    
    workspace = await workspace_service.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    return workspace


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    data: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """Update workspace."""
    workspace_service = WorkspaceService(db)
    
    workspace = await workspace_service.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    # Check admin membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update workspace",
            )
    
    workspace = await workspace_service.update(workspace, data)
    return workspace


@router.get("/{workspace_id}/members", response_model=List[MembershipResponse])
async def list_members(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MembershipResponse]:
    """List workspace members."""
    workspace_service = WorkspaceService(db)
    
    # Check membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    members = await workspace_service.get_members(workspace_id)
    
    # Add user info to response
    result = []
    for m in members:
        resp = MembershipResponse(
            id=m.id,
            user_id=m.user_id,
            workspace_id=m.workspace_id,
            role=m.role,
            created_at=m.created_at,
            user_email=m.user.email if m.user else None,
            user_name=m.user.full_name if m.user else None,
        )
        result.append(resp)
    
    return result


@router.post("/{workspace_id}/invite", response_model=MembershipResponse)
async def invite_member(
    workspace_id: UUID,
    data: MembershipCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MembershipResponse:
    """Invite a member to workspace."""
    workspace_service = WorkspaceService(db)
    user_service = UserService(db)
    
    # Check admin membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can invite members",
            )
    
    # Get workspace
    workspace = await workspace_service.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    # Get or create user
    user = await user_service.get_by_email(data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. They must register first.",
        )
    
    # Check if already a member
    existing = await workspace_service.get_membership(workspace_id, user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member",
        )
    
    membership = await workspace_service.add_member(
        workspace, user, data.role, current_user.id
    )
    
    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        workspace_id=membership.workspace_id,
        role=membership.role,
        created_at=membership.created_at,
        user_email=user.email,
        user_name=user.full_name,
    )


class MembershipUpdate(BaseModel):
    """Schema for updating a membership."""
    role: str


@router.put("/{workspace_id}/members/{member_id}", response_model=MembershipResponse)
async def update_member_role(
    workspace_id: UUID,
    member_id: UUID,
    data: MembershipUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MembershipResponse:
    """Update a member's role in the workspace."""
    workspace_service = WorkspaceService(db)
    
    # Check admin membership
    current_membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not current_membership or current_membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update member roles",
            )
    
    # Get the membership to update
    result = await db.execute(
        select(WorkspaceMembership)
        .options(joinedload(WorkspaceMembership.user))
        .where(
            WorkspaceMembership.id == member_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )
    
    # Prevent demoting self
    if membership.user_id == current_user.id and data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )
    
    # Update role
    membership.role = data.role
    await db.commit()
    await db.refresh(membership)
    
    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        workspace_id=membership.workspace_id,
        role=membership.role,
        created_at=membership.created_at,
        user_email=membership.user.email if membership.user else None,
        user_name=membership.user.full_name if membership.user else None,
    )


@router.delete("/{workspace_id}/members/{member_id}")
async def remove_member(
    workspace_id: UUID,
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a member from the workspace."""
    workspace_service = WorkspaceService(db)
    
    # Check admin membership
    current_membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not current_membership or current_membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can remove members",
            )
    
    # Get the membership to remove
    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.id == member_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )
    
    # Prevent removing self
    if membership.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the workspace",
        )
    
    # Delete membership
    await db.delete(membership)
    await db.commit()
    
    return {"message": "Member removed successfully"}


@router.get("/{workspace_id}/stats", response_model=WorkspaceStatsResponse)
async def get_workspace_stats(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceStatsResponse:
    """Get aggregated statistics for a workspace."""
    workspace_service = WorkspaceService(db)
    
    # Check membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Count projects
    projects_result = await db.execute(
        select(func.count(Project.id)).where(Project.workspace_id == workspace_id)
    )
    projects_count = projects_result.scalar() or 0
    
    # Get project IDs for this workspace
    project_ids_result = await db.execute(
        select(Project.id).where(Project.workspace_id == workspace_id)
    )
    project_ids = [row[0] for row in project_ids_result.fetchall()]
    
    if not project_ids:
        return WorkspaceStatsResponse(
            projects_count=0,
            runs_count=0,
            completed_runs_count=0,
            avg_health_score=None,
        )
    
    # Count runs
    runs_result = await db.execute(
        select(func.count(Run.id)).where(Run.project_id.in_(project_ids))
    )
    runs_count = runs_result.scalar() or 0
    
    # Count completed runs
    completed_result = await db.execute(
        select(func.count(Run.id)).where(
            Run.project_id.in_(project_ids),
            Run.status == "completed"
        )
    )
    completed_runs_count = completed_result.scalar() or 0
    
    # Average health score of completed runs
    avg_result = await db.execute(
        select(func.avg(Run.health_score)).where(
            Run.project_id.in_(project_ids),
            Run.status == "completed",
            Run.health_score.isnot(None)
        )
    )
    avg_health_score = avg_result.scalar()
    
    return WorkspaceStatsResponse(
        projects_count=projects_count,
        runs_count=runs_count,
        completed_runs_count=completed_runs_count,
        avg_health_score=round(avg_health_score, 1) if avg_health_score else None,
    )
