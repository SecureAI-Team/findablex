"""System settings models for dynamic configuration."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB  # Use JSON for SQLite compatibility
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class SystemSetting(Base):
    """System setting model for platform-wide configuration."""
    
    __tablename__ = "system_settings"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    value: Mapped[Any] = mapped_column(
        JSONB,
        nullable=True,
    )
    value_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="string",
    )  # string, number, boolean, json
    is_secret: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
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
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    updated_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by],
    )
    
    def __repr__(self) -> str:
        return f"<SystemSetting {self.key}>"


class SystemSettingAudit(Base):
    """Audit log for system setting changes."""
    
    __tablename__ = "system_settings_audit"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    setting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("system_settings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    old_value: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True,
    )
    new_value: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True,
    )
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    
    # Relationships
    setting: Mapped["SystemSetting"] = relationship(
        "SystemSetting",
        foreign_keys=[setting_id],
    )
    changed_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[changed_by],
    )
    
    def __repr__(self) -> str:
        return f"<SystemSettingAudit {self.key} at {self.changed_at}>"


# Default settings configuration
DEFAULT_SETTINGS = [
    # Platform basics
    {
        "key": "platform.name",
        "category": "platform",
        "value": "FindableX",
        "value_type": "string",
        "is_secret": False,
        "description": "平台名称",
    },
    {
        "key": "platform.logo_url",
        "category": "platform",
        "value": None,
        "value_type": "string",
        "is_secret": False,
        "description": "平台 Logo URL",
    },
    {
        "key": "platform.support_email",
        "category": "platform",
        "value": None,
        "value_type": "string",
        "is_secret": False,
        "description": "支持邮箱",
    },
    
    # Auth settings
    {
        "key": "auth.registration_enabled",
        "category": "auth",
        "value": True,
        "value_type": "boolean",
        "is_secret": False,
        "description": "是否开放注册",
    },
    {
        "key": "auth.invite_code_required",
        "category": "auth",
        "value": False,
        "value_type": "boolean",
        "is_secret": False,
        "description": "是否需要邀请码",
    },
    {
        "key": "auth.default_invite_code",
        "category": "auth",
        "value": None,
        "value_type": "string",
        "is_secret": True,
        "description": "默认邀请码",
    },
    {
        "key": "auth.jwt_expire_minutes",
        "category": "auth",
        "value": 1440,
        "value_type": "number",
        "is_secret": False,
        "description": "JWT Token 过期时间（分钟）",
    },
    
    # AI settings
    {
        "key": "ai.qwen_api_key",
        "category": "ai",
        "value": None,
        "value_type": "string",
        "is_secret": True,
        "description": "通义千问 API Key",
    },
    {
        "key": "ai.qwen_model",
        "category": "ai",
        "value": "qwen-max",
        "value_type": "string",
        "is_secret": False,
        "description": "通义千问默认模型",
    },
    {
        "key": "ai.openai_api_key",
        "category": "ai",
        "value": None,
        "value_type": "string",
        "is_secret": True,
        "description": "OpenAI API Key",
    },
    {
        "key": "ai.openai_model",
        "category": "ai",
        "value": "gpt-4-turbo",
        "value_type": "string",
        "is_secret": False,
        "description": "OpenAI 默认模型",
    },
    {
        "key": "ai.deepseek_api_key",
        "category": "ai",
        "value": None,
        "value_type": "string",
        "is_secret": True,
        "description": "DeepSeek API Key",
    },
    {
        "key": "ai.kimi_api_key",
        "category": "ai",
        "value": None,
        "value_type": "string",
        "is_secret": True,
        "description": "Kimi (Moonshot) API Key",
    },
    {
        "key": "ai.perplexity_api_key",
        "category": "ai",
        "value": None,
        "value_type": "string",
        "is_secret": True,
        "description": "Perplexity API Key",
    },
    {
        "key": "ai.user_can_provide_key",
        "category": "ai",
        "value": True,
        "value_type": "boolean",
        "is_secret": False,
        "description": "允许用户自带 API Key",
    },
    
    # Crawler settings
    {
        "key": "crawler.enabled",
        "category": "crawler",
        "value": False,
        "value_type": "boolean",
        "is_secret": False,
        "description": "是否启用爬虫功能",
    },
    {
        "key": "crawler.rate_limit",
        "category": "crawler",
        "value": 0.2,
        "value_type": "number",
        "is_secret": False,
        "description": "爬虫速率限制（请求/秒）",
    },
    {
        "key": "crawler.daily_limit",
        "category": "crawler",
        "value": 500,
        "value_type": "number",
        "is_secret": False,
        "description": "每日爬取限额",
    },
    {
        "key": "crawler.proxy_pool_url",
        "category": "crawler",
        "value": None,
        "value_type": "string",
        "is_secret": True,
        "description": "代理池 URL",
    },
    {
        "key": "crawler.api_mode_enabled",
        "category": "crawler",
        "value": True,
        "value_type": "boolean",
        "is_secret": False,
        "description": "优先使用 API 模式（无需浏览器）",
    },
    {
        "key": "crawler.api_mode_engines",
        "category": "crawler",
        "value": ["deepseek", "qwen", "kimi", "perplexity", "chatgpt"],
        "value_type": "json",
        "is_secret": False,
        "description": "支持 API 模式的引擎列表",
    },
    
    # Limits settings
    {
        "key": "limits.max_upload_size_mb",
        "category": "limits",
        "value": 10,
        "value_type": "number",
        "is_secret": False,
        "description": "最大上传文件大小（MB）",
    },
    {
        "key": "limits.rate_limit_per_minute",
        "category": "limits",
        "value": 100,
        "value_type": "number",
        "is_secret": False,
        "description": "API 速率限制（请求/分钟）",
    },
    {
        "key": "limits.free_projects_limit",
        "category": "limits",
        "value": 3,
        "value_type": "number",
        "is_secret": False,
        "description": "免费用户项目数量限制",
    },
    {
        "key": "limits.free_runs_per_month",
        "category": "limits",
        "value": 10,
        "value_type": "number",
        "is_secret": False,
        "description": "免费用户每月运行次数限制",
    },
    
    # Email settings
    {
        "key": "email.smtp_host",
        "category": "email",
        "value": None,
        "value_type": "string",
        "is_secret": False,
        "description": "SMTP 服务器地址",
    },
    {
        "key": "email.smtp_port",
        "category": "email",
        "value": 587,
        "value_type": "number",
        "is_secret": False,
        "description": "SMTP 端口",
    },
    {
        "key": "email.smtp_user",
        "category": "email",
        "value": None,
        "value_type": "string",
        "is_secret": False,
        "description": "SMTP 用户名",
    },
    {
        "key": "email.smtp_password",
        "category": "email",
        "value": None,
        "value_type": "string",
        "is_secret": True,
        "description": "SMTP 密码",
    },
    {
        "key": "email.from_address",
        "category": "email",
        "value": None,
        "value_type": "string",
        "is_secret": False,
        "description": "发件人地址",
    },
    
    # Feature flags
    {
        "key": "features.research_mode",
        "category": "features",
        "value": True,
        "value_type": "boolean",
        "is_secret": False,
        "description": "启用科研模式",
    },
    {
        "key": "features.crawler_for_researchers",
        "category": "features",
        "value": False,
        "value_type": "boolean",
        "is_secret": False,
        "description": "允许研究员使用爬虫",
    },
    {
        "key": "features.export_enabled",
        "category": "features",
        "value": True,
        "value_type": "boolean",
        "is_secret": False,
        "description": "启用数据导出",
    },
]
