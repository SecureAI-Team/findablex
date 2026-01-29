"""Project schemas."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    workspace_id: UUID
    industry_template: Optional[str] = None
    target_domains: List[str] = []


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    target_domains: Optional[List[str]] = None
    settings: Optional[dict] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: UUID
    workspace_id: UUID
    industry_template: Optional[str]
    target_domains: List[str]
    settings: dict
    status: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    # Computed fields for dashboard
    health_score: Optional[int] = None
    run_count: int = 0
    last_run_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class QueryItemBase(BaseModel):
    """Base query item schema."""
    query_text: str = Field(..., min_length=1)
    query_type: Optional[str] = None
    intent_category: Optional[str] = None
    # 查询标签
    stage: Optional[str] = Field(None, description="买方旅程阶段: awareness, consideration, decision, retention")
    risk_level: Optional[str] = Field(None, description="风险等级: low, medium, high, critical")
    target_role: Optional[str] = Field(None, description="目标角色: marketing, sales, compliance, technical, management")


class QueryItemCreate(QueryItemBase):
    """Schema for creating a query item."""
    expected_citations: Optional[List[str]] = None
    metadata: dict = {}


class QueryItemResponse(QueryItemBase):
    """Schema for query item response."""
    id: UUID
    project_id: UUID
    expected_citations: Optional[List[dict]] = None
    extra_data: dict = Field(default_factory=dict)
    position: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class QueryItemBulkCreate(BaseModel):
    """Schema for bulk creating query items."""
    queries: List[QueryItemCreate]


# 体检模板相关
class CheckupTemplateQuery(BaseModel):
    """Schema for a single query in a template."""
    text: str
    stage: Optional[str] = None
    type: Optional[str] = None
    risk: Optional[str] = None
    role: Optional[str] = None


class CheckupTemplateResponse(BaseModel):
    """Schema for checkup template response."""
    id: str
    name: str
    industry: str
    description: str
    query_count: int
    free_preview: int
    queries: List[CheckupTemplateQuery]
