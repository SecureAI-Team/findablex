"""
API Key management routes.

Provides endpoints for managing user-level and workspace-level API keys.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.services.credential_service import CredentialService
from app.services.user_credential_service import UserCredentialService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ========== Schemas ==========

class CredentialCreate(BaseModel):
    """Schema for creating a credential."""
    engine: str = Field(..., description="AI engine: deepseek, qwen, kimi, perplexity, chatgpt")
    api_key: str = Field(..., min_length=10, description="API key value")
    label: Optional[str] = Field(None, max_length=100, description="Optional label")


class CredentialUpdate(BaseModel):
    """Schema for updating a credential."""
    api_key: Optional[str] = Field(None, min_length=10, description="New API key value")
    label: Optional[str] = Field(None, max_length=100, description="New label")
    is_active: Optional[bool] = None


class CredentialResponse(BaseModel):
    """Schema for credential response (without decrypted value)."""
    id: str
    engine: str
    credential_type: str
    label: Optional[str]
    is_active: bool
    last_used_at: Optional[str]
    last_error: Optional[str]
    created_at: str
    updated_at: Optional[str] = None


# Valid engines for API keys
VALID_ENGINES = ["deepseek", "qwen", "kimi", "perplexity", "chatgpt"]


def validate_engine(engine: str) -> str:
    """Validate and normalize engine name."""
    engine_lower = engine.lower()
    if engine_lower not in VALID_ENGINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid engine. Must be one of: {', '.join(VALID_ENGINES)}",
        )
    return engine_lower


# ========== User-Level Credentials (My API Keys) ==========

@router.get("/me/credentials", response_model=List[CredentialResponse])
async def list_my_credentials(
    engine: Optional[str] = Query(None, description="Filter by engine"),
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CredentialResponse]:
    """List my API keys."""
    service = UserCredentialService(db)
    credentials = await service.list_for_user(
        current_user.id,
        include_inactive=include_inactive,
    )
    
    # Filter by engine if specified
    if engine:
        engine = validate_engine(engine)
        credentials = [c for c in credentials if c["engine"] == engine]
    
    return [
        CredentialResponse(
            id=c["id"],
            engine=c["engine"],
            credential_type=c["credential_type"],
            label=c["label"],
            is_active=c["is_active"],
            last_used_at=c["last_used_at"],
            last_error=c["last_error"],
            created_at=c["created_at"],
            updated_at=c.get("updated_at"),
        )
        for c in credentials
    ]


@router.post("/me/credentials", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_my_credential(
    data: CredentialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CredentialResponse:
    """Add a new API key."""
    engine = validate_engine(data.engine)
    
    service = UserCredentialService(db)
    
    # Check if user already has an active key for this engine
    existing = await service.get_for_user(current_user.id, engine, active_only=True)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have an active API key for {engine}. Deactivate it first or update it.",
        )
    
    credential = await service.create(
        user_id=current_user.id,
        engine=engine,
        value=data.api_key,
        label=data.label,
    )
    
    return CredentialResponse(
        id=str(credential.id),
        engine=credential.engine,
        credential_type=credential.credential_type,
        label=credential.label,
        is_active=credential.is_active,
        last_used_at=credential.last_used_at.isoformat() if credential.last_used_at else None,
        last_error=credential.last_error,
        created_at=credential.created_at.isoformat(),
        updated_at=credential.updated_at.isoformat() if credential.updated_at else None,
    )


@router.put("/me/credentials/{credential_id}", response_model=CredentialResponse)
async def update_my_credential(
    credential_id: UUID,
    data: CredentialUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CredentialResponse:
    """Update my API key."""
    service = UserCredentialService(db)
    
    # Verify ownership
    if not await service.verify_ownership(credential_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    
    # Update fields
    if data.api_key:
        await service.update_value(credential_id, data.api_key)
    
    if data.label is not None:
        await service.update_label(credential_id, data.label)
    
    if data.is_active is not None:
        if data.is_active:
            await service.activate(credential_id)
        else:
            await service.deactivate(credential_id)
    
    # Refresh and return
    credential = await service.get_by_id(credential_id)
    
    return CredentialResponse(
        id=str(credential.id),
        engine=credential.engine,
        credential_type=credential.credential_type,
        label=credential.label,
        is_active=credential.is_active,
        last_used_at=credential.last_used_at.isoformat() if credential.last_used_at else None,
        last_error=credential.last_error,
        created_at=credential.created_at.isoformat(),
        updated_at=credential.updated_at.isoformat() if credential.updated_at else None,
    )


@router.delete("/me/credentials/{credential_id}")
async def delete_my_credential(
    credential_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete my API key."""
    service = UserCredentialService(db)
    
    # Verify ownership
    if not await service.verify_ownership(credential_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    
    await service.delete(credential_id)
    return {"message": "Credential deleted"}


# ========== Workspace-Level Credentials ==========

class WorkspaceCredentialCreate(CredentialCreate):
    """Schema for creating a workspace credential."""
    account_id: Optional[str] = Field(default="default", description="Account identifier")


@router.get("/workspaces/{workspace_id}/credentials", response_model=List[CredentialResponse])
async def list_workspace_credentials(
    workspace_id: UUID,
    engine: Optional[str] = Query(None, description="Filter by engine"),
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CredentialResponse]:
    """List workspace API keys (admin only)."""
    workspace_service = WorkspaceService(db)
    
    # Check admin membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace admins can manage credentials",
            )
    
    service = CredentialService(db)
    credentials = await service.list_for_workspace(
        workspace_id,
        include_inactive=include_inactive,
    )
    
    # Filter by engine if specified
    if engine:
        engine = validate_engine(engine)
        credentials = [c for c in credentials if c["engine"] == engine]
    
    return [
        CredentialResponse(
            id=c["id"],
            engine=c["engine"],
            credential_type=c["credential_type"],
            label=c["label"],
            is_active=c["is_active"],
            last_used_at=c["last_used_at"],
            last_error=c["last_error"],
            created_at=c["created_at"],
        )
        for c in credentials
    ]


@router.post("/workspaces/{workspace_id}/credentials", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace_credential(
    workspace_id: UUID,
    data: WorkspaceCredentialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CredentialResponse:
    """Add a workspace API key (admin only)."""
    workspace_service = WorkspaceService(db)
    
    # Check admin membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace admins can add credentials",
            )
    
    engine = validate_engine(data.engine)
    
    service = CredentialService(db)
    
    # Check if workspace already has an active key for this engine
    existing = await service.get_for_engine(workspace_id, engine, active_only=True)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace already has an active API key for {engine}. Deactivate it first or update it.",
        )
    
    credential = await service.create(
        workspace_id=workspace_id,
        engine=engine,
        credential_type="api_key",
        value=data.api_key,
        created_by=current_user.id,
        account_id=data.account_id,
        label=data.label,
    )
    
    return CredentialResponse(
        id=str(credential.id),
        engine=credential.engine,
        credential_type=credential.credential_type,
        label=credential.label,
        is_active=credential.is_active,
        last_used_at=credential.last_used_at.isoformat() if credential.last_used_at else None,
        last_error=credential.last_error,
        created_at=credential.created_at.isoformat(),
    )


@router.put("/workspaces/{workspace_id}/credentials/{credential_id}", response_model=CredentialResponse)
async def update_workspace_credential(
    workspace_id: UUID,
    credential_id: UUID,
    data: CredentialUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CredentialResponse:
    """Update a workspace API key (admin only)."""
    workspace_service = WorkspaceService(db)
    
    # Check admin membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace admins can update credentials",
            )
    
    service = CredentialService(db)
    credential = await service.get_by_id(credential_id)
    
    if not credential or credential.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    
    # Update fields
    if data.api_key:
        await service.update_value(credential_id, data.api_key)
    
    if data.label is not None:
        credential.label = data.label
        await db.commit()
    
    if data.is_active is not None:
        if data.is_active:
            credential.is_active = True
        else:
            await service.deactivate(credential_id)
        await db.commit()
    
    # Refresh
    await db.refresh(credential)
    
    return CredentialResponse(
        id=str(credential.id),
        engine=credential.engine,
        credential_type=credential.credential_type,
        label=credential.label,
        is_active=credential.is_active,
        last_used_at=credential.last_used_at.isoformat() if credential.last_used_at else None,
        last_error=credential.last_error,
        created_at=credential.created_at.isoformat(),
    )


@router.delete("/workspaces/{workspace_id}/credentials/{credential_id}")
async def delete_workspace_credential(
    workspace_id: UUID,
    credential_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a workspace API key (admin only)."""
    workspace_service = WorkspaceService(db)
    
    # Check admin membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace admins can delete credentials",
            )
    
    service = CredentialService(db)
    credential = await service.get_by_id(credential_id)
    
    if not credential or credential.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    
    await service.delete(credential_id)
    return {"message": "Credential deleted"}
