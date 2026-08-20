"""add_icp_source

Revision ID: 003_add_icp_source
Revises: 002_add_environment_isolation
Create Date: 2026-08-17 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_add_icp_source'
down_revision: Union[str, None] = '002_add_environment_isolation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add source column to icps
    op.add_column('icps', sa.Column('source', sa.String(length=32), server_default='CLAUDE_GENERATED', nullable=False))
    op.create_index('idx_icps_source', 'icps', ['source'])

    # 2. Add source column to icp_approvals
    op.add_column('icp_approvals', sa.Column('source', sa.String(length=32), server_default='CLAUDE_GENERATED', nullable=False))
    op.create_index('idx_icp_approvals_source', 'icp_approvals', ['source'])

    # 3. Make original_claude_icp nullable on icp_approvals
    op.alter_column('icp_approvals', 'original_claude_icp', existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=True)


def downgrade() -> None:
    op.alter_column('icp_approvals', 'original_claude_icp', existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=False)
    op.drop_index('idx_icp_approvals_source', table_name='icp_approvals')
    op.drop_column('icp_approvals', 'source')

    op.drop_index('idx_icps_source', table_name='icps')
    op.drop_column('icps', 'source')
