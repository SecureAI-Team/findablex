"""Webhook model for API open platform."""
import uuid
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Webhook(Base):
    """
    Webhook subscription model.
    
    Allows users to register URLs to receive event notifications.
    Supported events:
    - run.completed: When a GEO checkup run finishes
    - crawl_task.completed: When a research task finishes
    - drift.detected: When metric drift is detected
    - report.generated: When a report is generated
    """
    
    __tablename__ = "webhooks"
    
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
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable name for the webhook",
    )
    url: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        comment="The webhook endpoint URL",
    )
    secret: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=lambda: secrets.token_hex(32),
        comment="HMAC secret for verifying webhook payloads",
    )
    
    # Events to subscribe to (JSON array of event types)
    events: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of subscribed event types",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Delivery stats
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_status_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="HTTP status code from last delivery",
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message from last delivery failure",
    )
    failure_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Consecutive failure count (reset on success)",
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
        Index("ix_webhooks_workspace_active", "workspace_id", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<Webhook {self.name} ({self.url})>"


class WebhookDelivery(Base):
    """
    Webhook delivery log.
    
    Records each delivery attempt for debugging and audit.
    """
    
    __tablename__ = "webhook_deliveries"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    payload: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    status_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    response_body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    __table_args__ = (
        Index("ix_webhook_deliveries_webhook_created", "webhook_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<WebhookDelivery {self.event_type} status={self.status_code}>"
