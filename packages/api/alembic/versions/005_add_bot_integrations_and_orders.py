"""Add bot_integrations and orders tables

Revision ID: 005
Revises: 004
Create Date: 2026-02-06

This migration adds support for:
1. BotIntegration - Feishu / WeCom webhook configuration per workspace
2. Order - manual payment order tracking

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create bot_integrations table
    op.create_table(
        'bot_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('platform', sa.String(20), nullable=False, comment='Bot platform: feishu | wecom'),
        sa.Column('webhook_url', sa.String(2000), nullable=False, comment='Webhook URL for the bot'),
        sa.Column('events', postgresql.JSONB, nullable=False, server_default='["checkup_complete","drift_detected","weekly_digest"]', comment='Array of subscribed event types'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_bot_integrations_ws_platform',
        'bot_integrations',
        ['workspace_id', 'platform'],
        unique=True,
    )

    # Create orders table (for manual payment tracking)
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('order_no', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', sa.String(50), nullable=False),
        sa.Column('amount', sa.Integer, nullable=False, comment='Amount in cents'),
        sa.Column('payment_method', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('user_note', sa.Text, nullable=True),
        sa.Column('admin_note', sa.Text, nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('orders')
    op.drop_index('ix_bot_integrations_ws_platform', table_name='bot_integrations')
    op.drop_table('bot_integrations')
