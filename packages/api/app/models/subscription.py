"""Subscription and Plan models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# 套餐定义
PLANS = {
    "free": {
        "name": "免费版",
        "description": "适合个人用户体验",
        "price_monthly": 0,
        "price_yearly": 0,
        "limits": {
            "projects": 1,
            "queries_per_project": 10,
            "runs_per_month": 5,
            "compare_reports": False,
            "export_formats": ["json"],
            "api_access": False,
            "team_members": 1,
            "support_level": "community",
        },
    },
    "pro": {
        "name": "专业版",
        "description": "适合中小企业使用",
        "price_monthly": 299,
        "price_yearly": 2990,
        "limits": {
            "projects": 10,
            "queries_per_project": 100,
            "runs_per_month": 50,
            "compare_reports": True,
            "export_formats": ["json", "html", "pdf"],
            "api_access": True,
            "team_members": 5,
            "support_level": "email",
        },
    },
    "enterprise": {
        "name": "企业版",
        "description": "适合大型企业和团队",
        "price_monthly": 999,
        "price_yearly": 9990,
        "limits": {
            "projects": -1,  # unlimited
            "queries_per_project": -1,
            "runs_per_month": -1,
            "compare_reports": True,
            "export_formats": ["json", "html", "pdf", "csv"],
            "api_access": True,
            "team_members": -1,
            "support_level": "dedicated",
        },
    },
}


class Plan(Base):
    """Plan model for subscription plans."""
    
    __tablename__ = "plans"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="套餐代码: free, pro, enterprise",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # 价格
    price_monthly: Mapped[float] = mapped_column(
        Float,
        default=0,
        nullable=False,
    )
    price_yearly: Mapped[float] = mapped_column(
        Float,
        default=0,
        nullable=False,
    )
    
    # 功能限制 (JSON)
    limits: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    
    # 特性列表 (用于展示)
    features: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<Plan {self.code}>"


class Subscription(Base):
    """Subscription model for workspace subscriptions."""
    
    __tablename__ = "subscriptions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    plan_code: Mapped[str] = mapped_column(
        String(50),
        default="free",
        nullable=False,
        comment="当前套餐代码",
    )
    
    # 订阅状态
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        comment="状态: active, cancelled, expired, trial",
    )
    
    # 订阅周期
    billing_cycle: Mapped[str] = mapped_column(
        String(20),
        default="monthly",
        nullable=False,
        comment="计费周期: monthly, yearly",
    )
    
    # 日期
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="到期时间",
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # 用量统计 (当月)
    usage: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {
            "runs_this_month": 0,
            "queries_created": 0,
            "reports_generated": 0,
            "last_reset_at": None,
        },
        nullable=False,
    )
    
    # 额外配额 (可通过促销等增加)
    bonus_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="额外赠送的运行次数",
    )
    
    # 支付信息 (简化版)
    payment_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="支付方式: manual, stripe, wechat, alipay",
    )
    last_payment_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    
    def get_limits(self) -> dict:
        """获取当前套餐的限制"""
        return PLANS.get(self.plan_code, PLANS["free"])["limits"]
    
    def is_feature_enabled(self, feature: str) -> bool:
        """检查功能是否可用"""
        limits = self.get_limits()
        return limits.get(feature, False) is True or limits.get(feature, 0) != 0
    
    def get_remaining_runs(self) -> int:
        """获取本月剩余运行次数"""
        limits = self.get_limits()
        max_runs = limits.get("runs_per_month", 0)
        if max_runs == -1:  # unlimited
            return -1
        
        used = self.usage.get("runs_this_month", 0)
        bonus = self.bonus_runs
        
        return max(0, max_runs + bonus - used)
    
    def can_run(self) -> bool:
        """检查是否可以运行"""
        if self.status not in ["active", "trial"]:
            return False
        
        remaining = self.get_remaining_runs()
        return remaining == -1 or remaining > 0
    
    def increment_usage(self, field: str, amount: int = 1) -> None:
        """增加用量计数"""
        if self.usage is None:
            self.usage = {}
        self.usage[field] = self.usage.get(field, 0) + amount
    
    def __repr__(self) -> str:
        return f"<Subscription {self.workspace_id} - {self.plan_code}>"
