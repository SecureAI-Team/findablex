"""Pydantic schemas for system settings."""
from datetime import datetime
from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SystemSettingBase(BaseModel):
    """Base schema for system settings."""
    key: str = Field(..., description="Configuration key, e.g., ai.qwen_model")
    category: str = Field(..., description="Configuration category")
    value: Any = Field(None, description="Configuration value")
    value_type: Literal["string", "number", "boolean", "json"] = Field(
        "string", description="Value type"
    )
    is_secret: bool = Field(False, description="Whether this is a sensitive value")
    description: Optional[str] = Field(None, description="Setting description")


class SystemSettingCreate(SystemSettingBase):
    """Schema for creating a system setting."""
    pass


class SystemSettingUpdate(BaseModel):
    """Schema for updating a system setting."""
    value: Any = Field(..., description="New configuration value")


class SystemSettingResponse(SystemSettingBase):
    """Schema for system setting response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    updated_at: datetime
    updated_by: Optional[UUID] = None
    
    # For secret values, mask the actual value
    @classmethod
    def from_orm_with_mask(cls, obj, mask_secrets: bool = True):
        """Create response with optional secret masking."""
        data = {
            "id": obj.id,
            "key": obj.key,
            "category": obj.category,
            "value": "******" if (obj.is_secret and mask_secrets and obj.value) else obj.value,
            "value_type": obj.value_type,
            "is_secret": obj.is_secret,
            "description": obj.description,
            "updated_at": obj.updated_at,
            "updated_by": obj.updated_by,
        }
        return cls(**data)


class SystemSettingAuditResponse(BaseModel):
    """Schema for system setting audit log response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    setting_id: UUID
    key: str
    old_value: Any
    new_value: Any
    changed_by: Optional[UUID] = None
    changed_at: datetime


class SettingsByCategoryResponse(BaseModel):
    """Schema for settings grouped by category."""
    category: str
    settings: List[SystemSettingResponse]


class AllSettingsResponse(BaseModel):
    """Schema for all settings response."""
    categories: List[SettingsByCategoryResponse]
    total: int


class BulkSettingUpdate(BaseModel):
    """Schema for bulk setting updates."""
    key: str
    value: Any


class BulkUpdateRequest(BaseModel):
    """Schema for bulk update request."""
    settings: List[BulkSettingUpdate]


class SettingUpdateResult(BaseModel):
    """Schema for setting update result."""
    key: str
    success: bool
    error: Optional[str] = None


class BulkUpdateResponse(BaseModel):
    """Schema for bulk update response."""
    results: List[SettingUpdateResult]
    success_count: int
    error_count: int
