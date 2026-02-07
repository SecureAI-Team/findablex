"""Bot integration model for Feishu / WeCom notifications."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BotIntegration(Base):
    """
    Bot integration settings for a workspace.

    Stores Feishu / WeCom webhook URLs and subscribed event types.
    Each workspace may have at most one config row per platform.
    """

    __tablename__ = "bot_integrations"

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

    # "feishu" or "wecom"
    platform: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Bot platform: feishu | wecom",
    )
    webhook_url: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        comment="Webhook URL for the bot",
    )

    # Subscribed events (JSON array)
    events: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: ["checkup_complete", "drift_detected", "weekly_digest"],
        comment="Array of subscribed event types",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
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
        Index("ix_bot_integrations_ws_platform", "workspace_id", "platform", unique=True),
    )

    def __repr__(self) -> str:
        return f"<BotIntegration {self.platform} ws={self.workspace_id}>"
