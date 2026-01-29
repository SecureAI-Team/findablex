"""User schemas."""
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# 业务角色类型
BusinessRoleType = Literal[
    "marketing", "growth", "sales", "brand_pr", 
    "compliance", "security", "presales", "product", "other"
]

# 行业类型
IndustryType = Literal[
    "ot_security", "cybersecurity", "industrial_software", "saas",
    "fintech", "healthcare", "education", "ecommerce", "manufacturing", "other"
]

# 地区类型
RegionType = Literal["cn", "hk_tw", "en_us", "en_eu", "apac", "global"]


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=8)
    invite_code: Optional[str] = None
    # 用户画像字段
    company_name: Optional[str] = Field(None, max_length=200)
    industry: Optional[str] = None
    region: Optional[str] = "cn"
    business_role: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    full_name: Optional[str] = None
    current_password: Optional[str] = None  # Required when changing password
    password: Optional[str] = Field(None, min_length=8)
    # 用户画像字段
    company_name: Optional[str] = Field(None, max_length=200)
    industry: Optional[str] = None
    region: Optional[str] = None
    business_role: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    is_active: bool
    is_superuser: bool
    email_verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    default_workspace_id: Optional[UUID] = None
    # 用户画像字段
    company_name: Optional[str] = None
    industry: Optional[str] = None
    region: Optional[str] = None
    business_role: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""
    sub: str
    exp: datetime
    type: str = "access"
