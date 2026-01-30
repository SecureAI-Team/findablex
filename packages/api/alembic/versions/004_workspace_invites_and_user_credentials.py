"""Add workspace_invites and user_credentials tables

Revision ID: 004
Revises: 003
Create Date: 2026-01-30

This migration adds support for:
1. WorkspaceInvite - invite links for users to join workspaces
2. UserCredential - user-level API keys for AI services

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workspace_invites table
    op.create_table(
        'workspace_invites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('code', sa.String(32), nullable=False, unique=True, index=True),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer', comment='Role to assign: admin, analyst, researcher, viewer'),
        sa.Column('max_uses', sa.Integer(), nullable=False, server_default='0', comment='Maximum uses, 0 = unlimited'),
        sa.Column('used_count', sa.Integer(), nullable=False, server_default='0', comment='Times this invite has been used'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Expiration time, null = never expires'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create user_credentials table
    op.create_table(
        'user_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('engine', sa.String(50), nullable=False, comment='AI engine: deepseek, qwen, kimi, perplexity, chatgpt'),
        sa.Column('credential_type', sa.String(20), nullable=False, server_default='api_key', comment='Credential type: api_key'),
        sa.Column('encrypted_value', sa.Text(), nullable=False, comment='Fernet encrypted credential value'),
        sa.Column('label', sa.String(100), nullable=True, comment='User-readable label'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True, comment='Last error message if any'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Add index for user_credentials to optimize lookups by user and engine
    op.create_index(
        'ix_user_credentials_user_engine',
        'user_credentials',
        ['user_id', 'engine'],
    )
    
    # Add new system settings for API mode crawler
    conn = op.get_bind()
    
    new_settings = [
        {
            "key": "ai.deepseek_api_key",
            "category": "ai",
            "value": "null",
            "value_type": "string",
            "is_secret": True,
            "description": "DeepSeek API Key",
        },
        {
            "key": "ai.kimi_api_key",
            "category": "ai",
            "value": "null",
            "value_type": "string",
            "is_secret": True,
            "description": "Kimi (Moonshot) API Key",
        },
        {
            "key": "ai.perplexity_api_key",
            "category": "ai",
            "value": "null",
            "value_type": "string",
            "is_secret": True,
            "description": "Perplexity API Key",
        },
        {
            "key": "crawler.api_mode_enabled",
            "category": "crawler",
            "value": "true",
            "value_type": "boolean",
            "is_secret": False,
            "description": "优先使用 API 模式（无需浏览器）",
        },
        {
            "key": "crawler.api_mode_engines",
            "category": "crawler",
            "value": '["deepseek", "qwen", "kimi", "perplexity", "chatgpt"]',
            "value_type": "json",
            "is_secret": False,
            "description": "支持 API 模式的引擎列表",
        },
    ]
    
    for setting in new_settings:
        # Check if setting already exists
        result = conn.execute(
            sa.text("SELECT id FROM system_settings WHERE key = :key"),
            {"key": setting["key"]}
        )
        if result.fetchone() is None:
            conn.execute(
                sa.text("""
                    INSERT INTO system_settings (key, category, value, value_type, is_secret, description)
                    VALUES (:key, :category, CAST(:value AS jsonb), :value_type, :is_secret, :description)
                """),
                setting
            )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_user_credentials_user_engine', table_name='user_credentials')
    
    # Drop tables
    op.drop_table('user_credentials')
    op.drop_table('workspace_invites')
    
    # Remove added system settings
    conn = op.get_bind()
    keys_to_remove = [
        'ai.deepseek_api_key',
        'ai.kimi_api_key',
        'ai.perplexity_api_key',
        'crawler.api_mode_enabled',
        'crawler.api_mode_engines',
    ]
    for key in keys_to_remove:
        conn.execute(
            sa.text("DELETE FROM system_settings WHERE key = :key"),
            {"key": key}
        )
