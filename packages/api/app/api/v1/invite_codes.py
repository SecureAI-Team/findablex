"""Invite code management routes."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.invite_code import InviteCode, WorkspaceInvite

router = APIRouter()


# ========== Schemas ==========

class InviteCodeCreate(BaseModel):
    """Schema for creating an invite code."""
    code: Optional[str] = Field(None, description="自定义邀请码，留空自动生成")
    description: Optional[str] = None
    max_uses: int = Field(default=1, ge=-1, description="最大使用次数，-1为无限")
    expires_in_days: Optional[int] = Field(default=30, ge=0, description="有效天数，0为永不过期")
    bonus_runs: int = Field(default=0, ge=0, description="赠送体检次数")
    plan_override: Optional[str] = Field(None, description="覆盖套餐: free, pro, enterprise")


class InviteCodeUpdate(BaseModel):
    """Schema for updating an invite code."""
    description: Optional[str] = None
    max_uses: Optional[int] = Field(None, ge=-1)
    is_active: Optional[bool] = None
    bonus_runs: Optional[int] = Field(None, ge=0)
    plan_override: Optional[str] = None


class InviteCodeResponse(BaseModel):
    """Schema for invite code response."""
    id: UUID
    code: str
    description: Optional[str]
    max_uses: int
    used_count: int
    expires_at: Optional[datetime]
    bonus_runs: int
    plan_override: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class InviteCodeStats(BaseModel):
    """Schema for invite code statistics."""
    total_codes: int
    active_codes: int
    total_uses: int
    codes_by_status: dict


# ========== Endpoints ==========

def generate_code(length: int = 8) -> str:
    """Generate a random invite code."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Excluded I, O, 1, 0 to avoid confusion
    return ''.join(secrets.choice(chars) for _ in range(length))


@router.post("", response_model=InviteCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_invite_code(
    data: InviteCodeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InviteCode:
    """Create a new invite code (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create invite codes",
        )
    
    # Generate code if not provided
    code = data.code or generate_code()
    
    # Check if code already exists
    existing = await db.execute(
        select(InviteCode).where(InviteCode.code == code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite code already exists",
        )
    
    # Calculate expiration
    expires_at = None
    if data.expires_in_days and data.expires_in_days > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
    
    invite_code = InviteCode(
        code=code.upper(),
        description=data.description,
        max_uses=data.max_uses,
        expires_at=expires_at,
        bonus_runs=data.bonus_runs,
        plan_override=data.plan_override,
        created_by=current_user.id,
    )
    
    db.add(invite_code)
    await db.commit()
    await db.refresh(invite_code)
    
    return invite_code


@router.get("", response_model=List[InviteCodeResponse])
async def list_invite_codes(
    skip: int = 0,
    limit: int = 50,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[InviteCode]:
    """List all invite codes (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view invite codes",
        )
    
    query = select(InviteCode).order_by(InviteCode.created_at.desc())
    
    if is_active is not None:
        query = query.where(InviteCode.is_active == is_active)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/stats", response_model=InviteCodeStats)
async def get_invite_code_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InviteCodeStats:
    """Get invite code statistics (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view statistics",
        )
    
    # Total codes
    total_result = await db.execute(select(func.count(InviteCode.id)))
    total_codes = total_result.scalar() or 0
    
    # Active codes
    active_result = await db.execute(
        select(func.count(InviteCode.id)).where(InviteCode.is_active == True)
    )
    active_codes = active_result.scalar() or 0
    
    # Total uses
    uses_result = await db.execute(select(func.sum(InviteCode.used_count)))
    total_uses = uses_result.scalar() or 0
    
    return InviteCodeStats(
        total_codes=total_codes,
        active_codes=active_codes,
        total_uses=total_uses,
        codes_by_status={
            "active": active_codes,
            "inactive": total_codes - active_codes,
        },
    )


@router.get("/validate/{code}")
async def validate_invite_code(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate an invite code (public endpoint)."""
    result = await db.execute(
        select(InviteCode).where(InviteCode.code == code.upper())
    )
    invite_code = result.scalar_one_or_none()
    
    if not invite_code:
        return {"valid": False, "reason": "无效的邀请码"}
    
    if not invite_code.is_valid():
        if not invite_code.is_active:
            return {"valid": False, "reason": "邀请码已禁用"}
        if invite_code.max_uses > 0 and invite_code.used_count >= invite_code.max_uses:
            return {"valid": False, "reason": "邀请码已用尽"}
        if invite_code.expires_at:
            return {"valid": False, "reason": "邀请码已过期"}
        return {"valid": False, "reason": "邀请码无效"}
    
    return {
        "valid": True,
        "bonus_runs": invite_code.bonus_runs,
        "plan_override": invite_code.plan_override,
    }


@router.get("/{code_id}", response_model=InviteCodeResponse)
async def get_invite_code(
    code_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InviteCode:
    """Get an invite code by ID (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view invite codes",
        )
    
    result = await db.execute(
        select(InviteCode).where(InviteCode.id == code_id)
    )
    invite_code = result.scalar_one_or_none()
    
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite code not found",
        )
    
    return invite_code


@router.put("/{code_id}", response_model=InviteCodeResponse)
async def update_invite_code(
    code_id: UUID,
    data: InviteCodeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InviteCode:
    """Update an invite code (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update invite codes",
        )
    
    result = await db.execute(
        select(InviteCode).where(InviteCode.id == code_id)
    )
    invite_code = result.scalar_one_or_none()
    
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite code not found",
        )
    
    if data.description is not None:
        invite_code.description = data.description
    if data.max_uses is not None:
        invite_code.max_uses = data.max_uses
    if data.is_active is not None:
        invite_code.is_active = data.is_active
    if data.bonus_runs is not None:
        invite_code.bonus_runs = data.bonus_runs
    if data.plan_override is not None:
        invite_code.plan_override = data.plan_override
    
    await db.commit()
    await db.refresh(invite_code)
    
    return invite_code


@router.delete("/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invite_code(
    code_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an invite code (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete invite codes",
        )
    
    result = await db.execute(
        select(InviteCode).where(InviteCode.id == code_id)
    )
    invite_code = result.scalar_one_or_none()
    
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite code not found",
        )
    
    await db.delete(invite_code)
    await db.commit()


# ========== Workspace Invite Validation (Public) ==========

class WorkspaceInviteValidation(BaseModel):
    """Schema for workspace invite validation response."""
    valid: bool
    workspace_name: Optional[str] = None
    role: Optional[str] = None
    reason: Optional[str] = None


@router.get("/workspace/{code}", response_model=WorkspaceInviteValidation)
async def validate_workspace_invite(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceInviteValidation:
    """
    Validate a workspace invite code (public endpoint).
    
    This endpoint is used by the registration page to verify an invite link
    before allowing the user to register and join the workspace.
    """
    result = await db.execute(
        select(WorkspaceInvite)
        .options(joinedload(WorkspaceInvite.workspace))
        .where(WorkspaceInvite.code == code)
    )
    invite = result.scalar_one_or_none()
    
    if not invite:
        return WorkspaceInviteValidation(
            valid=False,
            reason="无效的邀请链接"
        )
    
    if not invite.is_valid():
        if not invite.is_active:
            return WorkspaceInviteValidation(
                valid=False,
                reason="邀请链接已被撤销"
            )
        if invite.max_uses > 0 and invite.used_count >= invite.max_uses:
            return WorkspaceInviteValidation(
                valid=False,
                reason="邀请链接已达到使用上限"
            )
        if invite.expires_at:
            return WorkspaceInviteValidation(
                valid=False,
                reason="邀请链接已过期"
            )
        return WorkspaceInviteValidation(
            valid=False,
            reason="邀请链接无效"
        )
    
    workspace_name = invite.workspace.name if invite.workspace else None
    
    return WorkspaceInviteValidation(
        valid=True,
        workspace_name=workspace_name,
        role=invite.role,
    )
