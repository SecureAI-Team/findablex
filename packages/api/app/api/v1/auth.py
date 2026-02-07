"""Authentication routes."""
from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import settings, dynamic
from app.core.security import create_access_token, create_refresh_token, create_password_reset_token, verify_password_reset_token, verify_refresh_token, verify_password
from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.invite_code import InviteCode, WorkspaceInvite
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse, UserUpdate
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


class UserResponseWithWorkspace(UserResponse):
    """User response with default workspace."""
    default_workspace_id: Optional[UUID] = None


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot password."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for reset password."""
    token: str
    password: str


class RefreshTokenRequest(BaseModel):
    """Request body for token refresh."""
    refresh_token: str


@router.post("/register", response_model=UserResponseWithWorkspace, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Register a new user.
    
    The invite_code can be either:
    1. A platform invite code (InviteCode) - user gets a personal workspace
    2. A workspace invite code (WorkspaceInvite) - user joins the specified workspace with a specific role
    """
    user_service = UserService(db)
    workspace_service = WorkspaceService(db)
    
    # Check if email already exists
    existing = await user_service.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Validate invite code if provided or required
    invite_code_obj = None
    workspace_invite = None
    
    if data.invite_code:
        # First, try to find a workspace invite (longer format)
        result = await db.execute(
            select(WorkspaceInvite)
            .options(joinedload(WorkspaceInvite.workspace))
            .where(WorkspaceInvite.code == data.invite_code)
        )
        workspace_invite = result.scalar_one_or_none()
        
        if workspace_invite:
            # Validate workspace invite
            if not workspace_invite.is_valid():
                if not workspace_invite.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="邀请链接已被撤销",
                    )
                if workspace_invite.max_uses > 0 and workspace_invite.used_count >= workspace_invite.max_uses:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="邀请链接已达到使用上限",
                    )
                if workspace_invite.expires_at:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="邀请链接已过期",
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邀请链接无效",
                )
        else:
            # Try platform invite code (shorter format, uppercase)
            result = await db.execute(
                select(InviteCode).where(InviteCode.code == data.invite_code.upper())
            )
            invite_code_obj = result.scalar_one_or_none()
            
            if not invite_code_obj:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的邀请码",
                )
            
            if not invite_code_obj.is_valid():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邀请码已过期或已用尽",
                )
    
    # Check if invite code is required (from settings)
    # Support dynamic setting override for open registration
    invite_required = settings.invite_code_required
    try:
        dynamic_invite_required = await dynamic.get("auth.invite_code_required")
        if dynamic_invite_required is not None:
            invite_required = dynamic_invite_required in (True, "true", "True", "1")
    except Exception:
        pass
    
    if invite_required and not invite_code_obj and not workspace_invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="注册需要邀请码",
        )
    
    # Create user
    user = await user_service.create(data)
    
    # Handle invite code usage and workspace assignment
    default_workspace = None
    
    if workspace_invite:
        # Mark workspace invite as used
        workspace_invite.use()
        
        # Add user to the workspace with the specified role
        await workspace_service.add_member(
            workspace_invite.workspace,
            user,
            workspace_invite.role,
            invited_by=workspace_invite.created_by,
        )
        default_workspace = workspace_invite.workspace
        await db.commit()
        
    elif invite_code_obj:
        # Mark platform invite code as used
        invite_code_obj.use()
        await db.commit()
        
        # Create default personal workspace for user
        default_workspace = await workspace_service.create_default_workspace(user)
    else:
        # No invite code - create default personal workspace
        default_workspace = await workspace_service.create_default_workspace(user)
    
    # Send welcome email in background
    try:
        from app.services.email_service import email_service
        background_tasks.add_task(
            email_service.send_welcome_email,
            user.email,
            user.full_name,
        )
    except Exception:
        pass  # Non-critical
    
    # Track registration event
    try:
        from app.services.analytics_service import AnalyticsService
        analytics = AnalyticsService(db)
        await analytics.track_event(
            "user_registered",
            user_id=user.id,
            workspace_id=default_workspace.id if default_workspace else None,
            properties={"invite_type": "workspace" if workspace_invite else "code" if invite_code_obj else "open"},
        )
    except Exception:
        pass  # Non-critical
    
    # Return user with workspace_id
    return {
        **user.__dict__,
        "default_workspace_id": default_workspace.id if default_workspace else None,
    }


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Login with email and password."""
    import traceback
    print(f"[LOGIN] Attempting login for: {data.email}")
    try:
        user_service = UserService(db)
        print(f"[LOGIN] UserService created")
        
        user = await user_service.authenticate(data.email, data.password)
        print(f"[LOGIN] Authentication result: {user is not None}")
    except Exception as e:
        print(f"[LOGIN ERROR] {traceback.format_exc()}")
        raise
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    refresh_token = create_refresh_token(str(user.id))
    
    return Token(
        access_token=access_token,
        expires_in=settings.jwt_expire_minutes * 60,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Refresh access token using refresh token."""
    # Verify refresh token
    user_id = verify_refresh_token(data.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    # Get user to verify they still exist and are active
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )
    
    # Generate new access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    
    # Generate new refresh token (rotate refresh tokens for security)
    new_refresh_token = create_refresh_token(str(user.id))
    
    return Token(
        access_token=access_token,
        expires_in=settings.jwt_expire_minutes * 60,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponseWithWorkspace)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current user info with default workspace."""
    workspace_service = WorkspaceService(db)
    
    # Get user's default workspace (first workspace they have access to)
    default_workspace = await workspace_service.get_default_workspace(current_user.id)
    
    return {
        **current_user.__dict__,
        "default_workspace_id": default_workspace.id if default_workspace else None,
    }


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update current user info."""
    user_service = UserService(db)
    
    # If password is being changed, verify current password first
    if data.password:
        if not data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to change password",
            )
        if not verify_password(data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
    
    user = await user_service.update(current_user, data)
    return user


@router.post("/logout")
async def logout() -> dict:
    """Logout user (client should discard tokens)."""
    return {"message": "Successfully logged out"}


class NotificationPreferences(BaseModel):
    """Notification preference settings."""
    drift_warning: bool = True
    retest_reminder: bool = True
    weekly_digest: bool = False
    quota_warning: bool = True
    renewal_reminder: bool = True
    checkup_completed: bool = True
    marketing: bool = False


@router.get("/me/notifications")
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get current user's notification preferences."""
    # Default preferences - in full implementation, stored per-user
    return {
        "drift_warning": True,
        "retest_reminder": True,
        "weekly_digest": False,
        "quota_warning": True,
        "renewal_reminder": True,
        "checkup_completed": True,
        "marketing": False,
    }


@router.put("/me/notifications")
async def update_notification_preferences(
    data: NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update current user's notification preferences."""
    # In full implementation, persist to database
    return {
        "drift_warning": data.drift_warning,
        "retest_reminder": data.retest_reminder,
        "weekly_digest": data.weekly_digest,
        "quota_warning": data.quota_warning,
        "renewal_reminder": data.renewal_reminder,
        "checkup_completed": data.checkup_completed,
        "marketing": data.marketing,
        "updated": True,
    }


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Request password reset.
    
    Sends an email with password reset link if email exists.
    Always returns success to prevent email enumeration.
    """
    from app.services.email_service import email_service
    
    user_service = UserService(db)
    user = await user_service.get_by_email(data.email)
    
    if user and user.is_active:
        # Generate reset token
        reset_token = create_password_reset_token(str(user.id))
        
        # Send email with reset link in background
        background_tasks.add_task(
            email_service.send_password_reset_email,
            user.email,
            reset_token,
            user.full_name,
        )
    
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reset password using token.
    
    Validates the reset token and updates the user's password.
    """
    user_id = verify_password_reset_token(data.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )
    
    # Update password
    await user_service.update_password(user, data.password)
    
    return {"message": "Password has been reset successfully"}
