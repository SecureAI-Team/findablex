"""Collaboration models: Comments, Mentions, and Activity Feed."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Comment(Base):
    """
    Comment model for project-level discussions.
    
    Supports threaded comments (parent_id) and @mentions.
    Can be attached to a project, a run, or a specific crawl result.
    """
    
    __tablename__ = "comments"
    
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Optional parent for threaded replies
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    # Content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # Optional attachment context (run, crawl result, etc.)
    target_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Optional target: project, run, crawl_result, drift_event",
    )
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID of the target entity",
    )
    
    # Mentions stored as JSON array of user_ids
    mentions: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of mentioned user IDs",
    )
    
    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
    
    __table_args__ = (
        Index("ix_comments_project_created", "project_id", "created_at"),
        Index("ix_comments_target", "target_type", "target_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Comment {self.id} by user {self.user_id}>"


class ActivityEvent(Base):
    """
    Activity feed event model.
    
    Records project-level activities for a timeline/feed view.
    Types include: project_created, run_started, run_completed,
    checkup_triggered, drift_detected, comment_added, member_joined, etc.
    """
    
    __tablename__ = "activity_events"
    
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
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who triggered the event (null for system events)",
    )
    
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Event type: run_started, run_completed, checkup_triggered, comment_added, etc.",
    )
    
    summary: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Human-readable summary of the event",
    )
    
    # Extra structured data
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional event data (engine, score, etc.)",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    __table_args__ = (
        Index("ix_activity_project_created", "project_id", "created_at"),
        Index("ix_activity_workspace_created", "workspace_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ActivityEvent {self.event_type} in project {self.project_id}>"
