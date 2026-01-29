"""Project and QueryItem models."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB  # Use JSON for SQLite compatibility
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User
    from app.models.run import Run


class Project(Base):
    """Project model for GEO checkup projects."""
    
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
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    industry_template: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
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
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
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
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="projects",
    )
    query_items: Mapped[List["QueryItem"]] = relationship(
        "QueryItem",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Project {self.name}>"


class QueryItem(Base):
    """QueryItem model for storing query sets."""
    
    __tablename__ = "query_items"
    
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
    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    query_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="查询类型: definition, comparison, recommendation, evaluation, howto, case_study, compliance, technical",
    )
    intent_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    # 查询标签字段
    stage: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="买方旅程阶段: awareness, consideration, decision, retention",
    )
    risk_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="风险等级: low, medium, high, critical",
    )
    target_role: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="目标角色: marketing, sales, compliance, technical, management",
    )
    expected_citations: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="query_items",
    )
    
    def __repr__(self) -> str:
        return f"<QueryItem {self.query_text[:50]}>"
