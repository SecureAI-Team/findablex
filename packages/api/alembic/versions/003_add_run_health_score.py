"""Add health_score column to runs table

Revision ID: 003
Revises: 002
Create Date: 2024-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add health_score column to runs table
    op.add_column(
        'runs',
        sa.Column('health_score', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    # Remove health_score column from runs table
    op.drop_column('runs', 'health_score')
