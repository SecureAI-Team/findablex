"""Workspace schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkspaceBase(BaseModel):
    """Base workspace schema."""
    name: str = Field(..., min_length=1, max_length=100)


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a workspace."""
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    research_opt_in: bool = False


class WorkspaceUpdate(BaseModel):
    """Schema for updating a workspace."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    settings: Optional[dict] = None
    research_opt_in: Optional[bool] = None


class WorkspaceResponse(WorkspaceBase):
    """Schema for workspace response."""
    id: UUID
    tenant_id: UUID
    slug: str
    settings: dict
    research_opt_in: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MembershipCreate(BaseModel):
    """Schema for creating a membership."""
    email: str
    role: str = Field(..., pattern=r"^(admin|analyst|researcher|viewer)$")


class MembershipResponse(BaseModel):
    """Schema for membership response."""
    id: UUID
    user_id: UUID
    workspace_id: UUID
    role: str
    created_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    
    class Config:
        from_attributes = True
