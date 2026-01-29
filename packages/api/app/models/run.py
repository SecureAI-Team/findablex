"""Run, Citation, and Metric models."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB  # Use JSON for SQLite compatibility
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project import Project, QueryItem
    from app.models.user import User
    from app.models.report import Report


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
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="runs",
    )
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
    
    def __repr__(self) -> str:
        return f"<Run {self.id} #{self.run_number}>"


class Citation(Base):
    """Citation model for extracted citations from AI responses."""
    
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
    
    # Citation information
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
    
    # Analysis
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
    
    # Raw data
    raw_response: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="citations",
    )
    
    def __repr__(self) -> str:
        return f"<Citation {self.source_domain} pos={self.position}>"


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
    
    # Relationships
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="metrics",
    )
    
    def __repr__(self) -> str:
        return f"<Metric {self.metric_type}={self.metric_value}>"
