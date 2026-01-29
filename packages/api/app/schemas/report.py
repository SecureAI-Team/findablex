"""Report schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """Schema for creating a report."""
    run_id: UUID
    report_type: str = "checkup"
    title: str = Field(..., min_length=1, max_length=200)


class ReportResponse(BaseModel):
    """Schema for report response."""
    id: UUID
    run_id: UUID
    report_type: str
    title: str
    content_html: Optional[str]
    content_json: dict
    generated_at: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    """Schema for report list item with project info."""
    id: UUID
    run_id: UUID
    report_type: str
    title: str
    project_id: UUID
    project_name: str
    health_score: Optional[int]
    generated_at: datetime
    
    class Config:
        from_attributes = True


class ShareLinkCreate(BaseModel):
    """Schema for creating a share link."""
    password: Optional[str] = None
    max_views: Optional[int] = None
    expires_in_days: Optional[int] = None


class ShareLinkResponse(BaseModel):
    """Schema for share link response."""
    id: UUID
    report_id: UUID
    token: str
    view_count: int
    max_views: Optional[int]
    expires_at: Optional[datetime]
    created_at: datetime
    share_url: str
    
    class Config:
        from_attributes = True


class PublicReportResponse(BaseModel):
    """Schema for public report access."""
    title: str
    report_type: str
    content_html: Optional[str]
    content_json: dict
    generated_at: datetime
    
    class Config:
        from_attributes = True
