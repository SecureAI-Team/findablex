"""Invite code model."""
import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class InviteCode(Base):
    """Invite code model for controlling registration."""
    
    __tablename__ = "invite_codes"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="邀请码",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="描述/备注",
    )
    
    # 使用限制
    max_uses: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="最大使用次数, -1表示无限",
    )
    used_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="已使用次数",
    )
    
    # 时间限制
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="过期时间",
    )
    
    # 权益配置
    bonus_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="额外赠送的体检次数",
    )
    plan_override: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="覆盖的套餐类型: free, pro, enterprise",
    )
    
    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用",
    )
    
    # 创建者
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="创建者用户ID",
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
    
    def is_valid(self) -> bool:
        """Check if the invite code is valid for use."""
        if not self.is_active:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        if self.expires_at and datetime.now(self.expires_at.tzinfo) > self.expires_at:
            return False
        return True
    
    def use(self) -> None:
        """Mark the invite code as used (increment counter)."""
        self.used_count += 1
    
    def __repr__(self) -> str:
        return f"<InviteCode {self.code}>"


class WorkspaceInvite(Base):
    """
    Workspace invitation model for inviting users to join a workspace.
    
    Users can register with an invite code and automatically join the workspace
    with the specified role.
    """
    
    __tablename__ = "workspace_invites"
    
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
    code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique invite code",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="viewer",
        nullable=False,
        comment="Role to assign: admin, analyst, researcher, viewer",
    )
    
    # Usage limits
    max_uses: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Maximum uses, 0 = unlimited",
    )
    used_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Times this invite has been used",
    )
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expiration time, null = never expires",
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Audit
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        foreign_keys=[workspace_id],
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
    )
    
    @classmethod
    def generate_code(cls) -> str:
        """Generate a unique invite code."""
        return secrets.token_urlsafe(16)[:24]
    
    def is_valid(self) -> bool:
        """Check if the invite is valid for use."""
        if not self.is_active:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        if self.expires_at:
            from datetime import timezone as tz
            if datetime.now(tz.utc) > self.expires_at:
                return False
        return True
    
    def use(self) -> None:
        """Increment usage counter."""
        self.used_count += 1
    
    def __repr__(self) -> str:
        return f"<WorkspaceInvite {self.code} -> {self.workspace_id}>"
