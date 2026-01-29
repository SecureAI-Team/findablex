"""Invite code model."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


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
