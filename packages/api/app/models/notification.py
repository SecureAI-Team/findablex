"""Notification model for in-app message center."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Notification(Base):
    """
    In-app notification model.
    
    Stores notifications for users across multiple channels:
    - checkup_completed: GEO checkup finished
    - drift_warning: Metric drift detected
    - retest_reminder: Scheduled retest reminder
    - quota_warning: Usage approaching limit
    - renewal_reminder: Subscription expiring
    - system: System announcements
    """
    
    __tablename__ = "notifications"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Notification type: checkup_completed, drift_warning, quota_warning, etc.",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    link: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional link to navigate to when clicked",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded extra metadata",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Notification {self.type} for user {self.user_id}>"
