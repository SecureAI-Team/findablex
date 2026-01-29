"""Add system_settings tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-16

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default settings to insert
DEFAULT_SETTINGS = [
    # Platform basics
    {"key": "platform.name", "category": "platform", "value": "FindableX", "value_type": "string", "is_secret": False, "description": "平台名称"},
    {"key": "platform.logo_url", "category": "platform", "value": None, "value_type": "string", "is_secret": False, "description": "平台 Logo URL"},
    {"key": "platform.support_email", "category": "platform", "value": None, "value_type": "string", "is_secret": False, "description": "支持邮箱"},
    
    # Auth settings
    {"key": "auth.registration_enabled", "category": "auth", "value": True, "value_type": "boolean", "is_secret": False, "description": "是否开放注册"},
    {"key": "auth.invite_code_required", "category": "auth", "value": False, "value_type": "boolean", "is_secret": False, "description": "是否需要邀请码"},
    {"key": "auth.default_invite_code", "category": "auth", "value": None, "value_type": "string", "is_secret": True, "description": "默认邀请码"},
    {"key": "auth.jwt_expire_minutes", "category": "auth", "value": 1440, "value_type": "number", "is_secret": False, "description": "JWT Token 过期时间（分钟）"},
    
    # AI settings
    {"key": "ai.qwen_api_key", "category": "ai", "value": None, "value_type": "string", "is_secret": True, "description": "通义千问 API Key"},
    {"key": "ai.qwen_model", "category": "ai", "value": "qwen-max", "value_type": "string", "is_secret": False, "description": "通义千问默认模型"},
    {"key": "ai.openai_api_key", "category": "ai", "value": None, "value_type": "string", "is_secret": True, "description": "OpenAI API Key"},
    {"key": "ai.openai_model", "category": "ai", "value": "gpt-4-turbo", "value_type": "string", "is_secret": False, "description": "OpenAI 默认模型"},
    {"key": "ai.user_can_provide_key", "category": "ai", "value": True, "value_type": "boolean", "is_secret": False, "description": "允许用户自带 API Key"},
    
    # Crawler settings
    {"key": "crawler.enabled", "category": "crawler", "value": False, "value_type": "boolean", "is_secret": False, "description": "是否启用爬虫功能"},
    {"key": "crawler.rate_limit", "category": "crawler", "value": 0.2, "value_type": "number", "is_secret": False, "description": "爬虫速率限制（请求/秒）"},
    {"key": "crawler.daily_limit", "category": "crawler", "value": 500, "value_type": "number", "is_secret": False, "description": "每日爬取限额"},
    {"key": "crawler.proxy_pool_url", "category": "crawler", "value": None, "value_type": "string", "is_secret": True, "description": "代理池 URL"},
    
    # Limits settings
    {"key": "limits.max_upload_size_mb", "category": "limits", "value": 10, "value_type": "number", "is_secret": False, "description": "最大上传文件大小（MB）"},
    {"key": "limits.rate_limit_per_minute", "category": "limits", "value": 100, "value_type": "number", "is_secret": False, "description": "API 速率限制（请求/分钟）"},
    {"key": "limits.free_projects_limit", "category": "limits", "value": 3, "value_type": "number", "is_secret": False, "description": "免费用户项目数量限制"},
    {"key": "limits.free_runs_per_month", "category": "limits", "value": 10, "value_type": "number", "is_secret": False, "description": "免费用户每月运行次数限制"},
    
    # Email settings
    {"key": "email.smtp_host", "category": "email", "value": None, "value_type": "string", "is_secret": False, "description": "SMTP 服务器地址"},
    {"key": "email.smtp_port", "category": "email", "value": 587, "value_type": "number", "is_secret": False, "description": "SMTP 端口"},
    {"key": "email.smtp_user", "category": "email", "value": None, "value_type": "string", "is_secret": False, "description": "SMTP 用户名"},
    {"key": "email.smtp_password", "category": "email", "value": None, "value_type": "string", "is_secret": True, "description": "SMTP 密码"},
    {"key": "email.from_address", "category": "email", "value": None, "value_type": "string", "is_secret": False, "description": "发件人地址"},
    
    # Feature flags
    {"key": "features.research_mode", "category": "features", "value": True, "value_type": "boolean", "is_secret": False, "description": "启用科研模式"},
    {"key": "features.crawler_for_researchers", "category": "features", "value": False, "value_type": "boolean", "is_secret": False, "description": "允许研究员使用爬虫"},
    {"key": "features.export_enabled", "category": "features", "value": True, "value_type": "boolean", "is_secret": False, "description": "启用数据导出"},
]


def upgrade() -> None:
    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('key', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('value', postgresql.JSONB(), nullable=True),
        sa.Column('value_type', sa.String(20), nullable=False, server_default='string'),
        sa.Column('is_secret', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create system_settings_audit table
    op.create_table(
        'system_settings_audit',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('setting_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('system_settings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('key', sa.String(100), nullable=False, index=True),
        sa.Column('old_value', postgresql.JSONB(), nullable=True),
        sa.Column('new_value', postgresql.JSONB(), nullable=True),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )
    
    # Insert default settings using raw SQL for JSONB values
    conn = op.get_bind()
    for setting in DEFAULT_SETTINGS:
        value_json = json.dumps(setting["value"]) if setting["value"] is not None else "null"
        conn.execute(
            sa.text("""
                INSERT INTO system_settings (key, category, value, value_type, is_secret, description)
                VALUES (:key, :category, :value::jsonb, :value_type, :is_secret, :description)
            """),
            {
                "key": setting["key"],
                "category": setting["category"],
                "value": value_json,
                "value_type": setting["value_type"],
                "is_secret": setting["is_secret"],
                "description": setting["description"],
            }
        )


def downgrade() -> None:
    op.drop_table('system_settings_audit')
    op.drop_table('system_settings')
