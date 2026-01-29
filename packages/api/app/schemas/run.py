"""Run schemas."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    """Schema for creating a run."""
    project_id: UUID
    run_type: str = "checkup"
    input_method: str = "import"
    parameters: dict = {}
    region: Optional[str] = None
    language: Optional[str] = None


class RunImport(BaseModel):
    """Schema for importing run data."""
    project_id: UUID
    input_data: str  # CSV, JSON, or paste content
    input_format: str = Field(..., pattern=r"^(csv|json|paste)$")


class RunResponse(BaseModel):
    """Schema for run response."""
    id: UUID
    project_id: UUID
    run_number: int
    run_type: str
    input_method: str
    template_version: str
    engine_version: Optional[str]
    parameters: dict
    region: Optional[str]
    language: Optional[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    total_queries: int
    processed_queries: int
    health_score: Optional[int] = None
    summary_metrics: dict
    created_by: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class CitationResponse(BaseModel):
    """Schema for citation response."""
    id: UUID
    run_id: UUID
    query_item_id: UUID
    position: int
    source_url: Optional[str]
    source_domain: Optional[str]
    source_title: Optional[str]
    snippet: Optional[str]
    is_target_domain: bool
    relevance_score: Optional[Decimal]
    authority_score: Optional[Decimal]
    extracted_at: datetime
    
    class Config:
        from_attributes = True


class MetricResponse(BaseModel):
    """Schema for metric response."""
    id: UUID
    run_id: UUID
    query_item_id: Optional[UUID]
    metric_type: str
    metric_value: Decimal
    metric_details: Optional[dict]
    calculated_at: datetime
    
    class Config:
        from_attributes = True


class RunSummary(BaseModel):
    """Schema for run summary in reports."""
    total_queries: int
    visibility_rate: float
    avg_position: float
    citation_count: int
    top3_rate: float
    health_score: float
