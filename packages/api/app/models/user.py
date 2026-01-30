"""User model."""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.workspace import Membership


# 业务角色定义
BUSINESS_ROLES = {
    "marketing": "市场负责人",
    "growth": "增长负责人",
    "sales": "销售负责人",
    "brand_pr": "品牌/公关",
    "compliance": "法务合规",
    "security": "安全负责人",
    "presales": "售前/解决方案",
    "product": "产品负责人",
    "other": "其他",
}

# 行业定义
INDUSTRIES = {
    "ot_security": "OT安全/工业控制",
    "cybersecurity": "网络安全",
    "industrial_software": "工业软件",
    "saas": "SaaS/企业服务",
    "fintech": "金融科技",
    "healthcare": "医疗健康",
    "education": "教育培训",
    "ecommerce": "电商零售",
    "manufacturing": "制造业",
    "other": "其他",
}

# 地区语言
REGIONS = {
    "cn": "中国大陆",
    "hk_tw": "港澳台",
    "en_us": "北美",
    "en_eu": "欧洲",
    "apac": "亚太其他",
    "global": "全球",
}


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # 用户画像字段
    company_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="公司名称",
    )
    industry: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="行业: ot_security, cybersecurity, saas, etc.",
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default="cn",
        comment="地区语言: cn, en_us, en_eu, etc.",
    )
    business_role: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="业务角色: marketing, sales, compliance, etc.",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
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
    
    # Relationships
    memberships: Mapped[List["Membership"]] = relationship(
        "Membership",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Membership.user_id",  # Specify FK to avoid ambiguity with invited_by
    )
    credentials: Mapped[List["UserCredential"]] = relationship(
        "UserCredential",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserCredential(Base):
    """
    User-level API Key credentials.
    
    Allows users to store their own API keys for various AI services.
    These have highest priority over workspace and platform-level keys.
    """
    
    __tablename__ = "user_credentials"
    
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
    engine: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="AI engine: deepseek, qwen, kimi, perplexity, chatgpt",
    )
    credential_type: Mapped[str] = mapped_column(
        String(20),
        default="api_key",
        nullable=False,
        comment="Credential type: api_key",
    )
    encrypted_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Fernet encrypted credential value",
    )
    label: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User-readable label",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Last error message if any",
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
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="credentials",
    )
    
    def __repr__(self) -> str:
        return f"<UserCredential {self.engine}/{self.credential_type} for user {self.user_id}>"
