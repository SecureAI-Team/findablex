"""
Database models for worker tasks.

These models mirror the API models and connect to the same database.
We define them separately to avoid import dependencies on the API package.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base

Base = declarative_base()


class Run(Base):
    """Run model for engine execution runs."""
    
    __tablename__ = "runs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    run_type: Mapped[str] = mapped_column(
        String(20),
        default="checkup",
        nullable=False,
    )
    input_method: Mapped[str] = mapped_column(
        String(20),
        default="import",
        nullable=False,
    )
    
    # Reproducibility fields
    template_version: Mapped[str] = mapped_column(
        String(20),
        default="1.0.0",
        nullable=False,
    )
    engine_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    parameters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    language: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    
    # Status and timing
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Statistics
    total_queries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    processed_queries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    health_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    summary_metrics: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    
    # Relationships
    citations: Mapped[List["Citation"]] = relationship(
        "Citation",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    metrics: Mapped[List["Metric"]] = relationship(
        "Metric",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class Project(Base):
    """Project model (simplified for worker)."""
    
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    target_domains: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )


class QueryItem(Base):
    """QueryItem model for storing query-response pairs."""
    
    __tablename__ = "query_items"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    response_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    engine: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Citation(Base):
    """Citation model for extracted citations."""
    
    __tablename__ = "citations"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("query_items.id"),
        nullable=False,
        index=True,
    )
    
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    source_domain: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    source_title: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    snippet: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    is_target_domain: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    relevance_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    authority_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    
    raw_response: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="citations",
    )


class Metric(Base):
    """Metric model for calculated metrics."""
    
    __tablename__ = "metrics"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("query_items.id"),
        nullable=True,
    )
    
    metric_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    metric_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
    )
    metric_details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="metrics",
    )


class Report(Base):
    """Report model for generated reports."""
    
    __tablename__ = "reports"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    report_type: Mapped[str] = mapped_column(
        String(30),
        default="checkup",
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    content_html: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    content_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="reports",
    )


class DriftEvent(Base):
    """DriftEvent model for tracking metric drift."""
    
    __tablename__ = "drift_events"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    baseline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id"),
        nullable=False,
    )
    compare_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id"),
        nullable=False,
    )
    
    drift_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    baseline_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
    )
    current_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
    )
    change_percent: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
    )
    
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
