"""add_environment_isolation

Revision ID: 002_add_environment_isolation
Revises: 001_initial_normalized_schema
Create Date: 2026-08-17 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_environment_isolation'
down_revision: Union[str, None] = '001_initial_normalized_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add environment column to campaigns
    op.add_column('campaigns', sa.Column('environment', sa.String(length=32), server_default='PRODUCTION', nullable=False))
    op.create_index('idx_campaigns_environment', 'campaigns', ['environment'])

    # 2. Add environment column to icps
    op.add_column('icps', sa.Column('environment', sa.String(length=32), server_default='PRODUCTION', nullable=False))
    op.create_index('idx_icps_environment', 'icps', ['environment'])

    # 3. Add environment column to leads
    op.add_column('leads', sa.Column('environment', sa.String(length=32), server_default='PRODUCTION', nullable=False))
    op.create_index('idx_leads_environment', 'leads', ['environment'])

    # 4. Add environment column to audit_logs
    op.add_column('audit_logs', sa.Column('environment', sa.String(length=32), server_default='PRODUCTION', nullable=False))
    op.create_index('idx_audit_logs_environment', 'audit_logs', ['environment'])


def downgrade() -> None:
    op.drop_index('idx_audit_logs_environment', table_name='audit_logs')
    op.drop_column('audit_logs', 'environment')

    op.drop_index('idx_leads_environment', table_name='leads')
    op.drop_column('leads', 'environment')

    op.drop_index('idx_icps_environment', table_name='icps')
    op.drop_column('icps', 'environment')

    op.drop_index('idx_campaigns_environment', table_name='campaigns')
    op.drop_column('campaigns', 'environment')
