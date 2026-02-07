"""Payment order model for tracking upgrade requests."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Order(Base):
    """Payment order model.
    
    Tracks subscription upgrade requests and manual payment confirmations.
    Flow:
    1. User clicks 'upgrade' → order created with status 'pending'
    2. User scans QR code and pays → clicks 'I paid' → status 'paid_unverified'
    3. Admin verifies payment → activates subscription → status 'activated'
    """
    
    __tablename__ = "orders"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    order_no: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="订单号 e.g. FX20260206ABCD1234",
    )
    
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Plan details
    plan_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="目标套餐: pro, enterprise",
    )
    billing_cycle: Mapped[str] = mapped_column(
        String(20),
        default="monthly",
        nullable=False,
        comment="计费周期: monthly, yearly",
    )
    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="订单金额 (CNY)",
    )
    
    # Payment
    payment_method: Mapped[str] = mapped_column(
        String(30),
        default="wechat",
        nullable=False,
        comment="支付方式: wechat, alipay, bank_transfer",
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
        index=True,
        comment="pending, paid_unverified, activated, cancelled, expired",
    )
    
    # User's payment confirmation note
    user_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="用户付款备注（如转账截图说明）",
    )
    
    # Admin note
    admin_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="管理员备注",
    )
    
    # Extra data
    extra: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    
    # Timestamps
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="用户标记已付款时间",
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="管理员激活时间",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="订单过期时间（超时未支付）",
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
    
    def __repr__(self) -> str:
        return f"<Order {self.order_no} [{self.status}]>"
