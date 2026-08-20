"""initial_normalized_schema

Revision ID: 001_initial_normalized_schema
Revises: 
Create Date: 2026-08-17 12:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_normalized_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Campaigns
    op.create_table(
        'campaigns',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('objective', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=64), server_default='ACTIVE', nullable=False),
        sa.Column('target_geography', sa.String(length=255), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_campaigns_name', 'campaigns', ['name'])
    op.create_index('idx_campaigns_status', 'campaigns', ['status'])
    op.create_index('idx_campaigns_created_at', 'campaigns', ['created_at'])

    # 2. ICPs
    op.create_table(
        'icps',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('campaign_id', sa.String(length=128), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=64), server_default='PENDING_REVIEW', nullable=False),
        sa.Column('current_version', sa.String(length=32), server_default='1.0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_icps_campaign_id', 'icps', ['campaign_id'])
    op.create_index('idx_icps_name', 'icps', ['name'])
    op.create_index('idx_icps_status', 'icps', ['status'])
    op.create_index('idx_icps_campaign_status', 'icps', ['campaign_id', 'status'])

    # 3. ICP Versions
    op.create_table(
        'icp_versions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('icp_id', sa.String(length=128), sa.ForeignKey('icps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('config_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_icp_versions_icp_ver', 'icp_versions', ['icp_id', 'version'], unique=True)

    # 4. ICP Approvals
    op.create_table(
        'icp_approvals',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('icp_id', sa.String(length=128), sa.ForeignKey('icps.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('version', sa.String(length=32), server_default='1.0.0', nullable=False),
        sa.Column('status', sa.String(length=64), server_default='PENDING_REVIEW', nullable=False),
        sa.Column('original_claude_icp', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('effective_icp', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('blocked_reason', sa.Text(), nullable=True),
        sa.Column('deepline_eligible', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deepline_run_ids', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('edit_history', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('audit_trail', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_icp_approvals_icp_id', 'icp_approvals', ['icp_id'])
    op.create_index('idx_icp_approvals_status', 'icp_approvals', ['status'])
    op.create_index('idx_icp_approvals_eligible', 'icp_approvals', ['deepline_eligible'])

    # 5. Leads
    op.create_table(
        'leads',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('campaign_id', sa.String(length=128), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('icp_id', sa.String(length=128), sa.ForeignKey('icps.id', ondelete='SET NULL'), nullable=True),
        sa.Column('icp_version', sa.String(length=32), server_default='1.0.0', nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('company_domain', sa.String(length=255), nullable=False),
        sa.Column('contact_name', sa.String(length=255), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('email_status', sa.String(length=64), server_default='PATTERN_CONFIRMED', nullable=False),
        sa.Column('linkedin_url', sa.String(length=512), nullable=True),
        sa.Column('company_size', sa.String(length=128), nullable=True),
        sa.Column('industry', sa.String(length=128), nullable=True),
        sa.Column('source', sa.String(length=64), server_default='DEEPLINE_DISCOVERY', nullable=False),
        sa.Column('opportunity_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('accessibility_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('outreach_priority_index', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('priority_level', sa.String(length=32), server_default='P3', nullable=False),
        sa.Column('qualification_status', sa.String(length=64), server_default='QUALIFIED', nullable=False),
        sa.Column('disqualification_reason', sa.Text(), nullable=True),
        sa.Column('personalization_status', sa.String(length=64), server_default='SIGNAL_VERIFIED', nullable=False),
        sa.Column('personalization_note', sa.Text(), nullable=True),
        sa.Column('voc_angle', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_leads_campaign_id', 'leads', ['campaign_id'])
    op.create_index('idx_leads_icp_id', 'leads', ['icp_id'])
    op.create_index('idx_leads_email', 'leads', ['email'])
    op.create_index('idx_leads_priority', 'leads', ['priority_level'])
    op.create_index('idx_leads_qual', 'leads', ['qualification_status'])
    op.create_index('idx_leads_opi', 'leads', ['outreach_priority_index'])
    op.create_index('idx_leads_company_name', 'leads', ['company_name'])
    op.create_index('idx_leads_created_at', 'leads', ['created_at'])

    # 6. Lead Research
    op.create_table(
        'lead_research',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.String(length=128), sa.ForeignKey('leads.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('raw_research', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('pain_point', sa.Text(), nullable=True),
        sa.Column('relevant_signal', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_lead_research_lead_id', 'lead_research', ['lead_id'])

    # 7. Lead Evidence
    op.create_table(
        'lead_evidence',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.String(length=128), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('claim_type', sa.String(length=64), nullable=False),
        sa.Column('evidence_level', sa.String(length=32), server_default='VERIFIED', nullable=False),
        sa.Column('source_reference', sa.Text(), nullable=True),
        sa.Column('verified', sa.Boolean(), server_default='true', nullable=False),
    )
    op.create_index('idx_lead_evidence_lead_id', 'lead_evidence', ['lead_id'])

    # 8. VoC Context
    op.create_table(
        'voc_context',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.String(length=128), sa.ForeignKey('leads.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('voc_angle', sa.String(length=255), nullable=False),
        sa.Column('pain_point', sa.Text(), nullable=False),
        sa.Column('messaging_angle', sa.Text(), nullable=False),
        sa.Column('aedrix_value_prop', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_voc_context_lead_id', 'voc_context', ['lead_id'])

    # 9. Email Drafts
    op.create_table(
        'email_drafts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.String(length=128), sa.ForeignKey('leads.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('ai_original_email_1', sa.Text(), nullable=False),
        sa.Column('ai_original_followup_a', sa.Text(), nullable=False),
        sa.Column('ai_original_followup_b', sa.Text(), nullable=False),
        sa.Column('edited_email_1', sa.Text(), nullable=True),
        sa.Column('edited_followup_a', sa.Text(), nullable=True),
        sa.Column('edited_followup_b', sa.Text(), nullable=True),
        sa.Column('qa_status', sa.String(length=32), server_default='PASS', nullable=False),
        sa.Column('qa_reasons', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_email_drafts_lead_id', 'email_drafts', ['lead_id'])
    op.create_index('idx_email_drafts_qa_status', 'email_drafts', ['qa_status'])

    # 10. Email Approvals
    op.create_table(
        'email_approvals',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.String(length=128), sa.ForeignKey('leads.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('approval_status', sa.String(length=64), server_default='PENDING_REVIEW', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('smartlead_eligible', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('blocked_reason', sa.Text(), nullable=True),
        sa.Column('flag_no_strong_signal', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_email_approvals_lead_id', 'email_approvals', ['lead_id'])
    op.create_index('idx_email_approvals_status', 'email_approvals', ['approval_status'])
    op.create_index('idx_email_approvals_status_eligible', 'email_approvals', ['approval_status', 'smartlead_eligible'])

    # 11. Deepline Runs
    op.create_table(
        'deepline_runs',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('icp_id', sa.String(length=128), sa.ForeignKey('icps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('campaign_id', sa.String(length=128), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requested_count', sa.Integer(), server_default='100', nullable=False),
        sa.Column('discovered_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('valid_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('qualified_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('hard_disqualified_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('campaign_excluded_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('p1_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('p2_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('p3_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('mode', sa.String(length=64), server_default='DRY_RUN_SIMULATION', nullable=False),
        sa.Column('artifacts_path', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_deepline_runs_icp_id', 'deepline_runs', ['icp_id'])
    op.create_index('idx_deepline_runs_campaign_id', 'deepline_runs', ['campaign_id'])
    op.create_index('idx_deepline_runs_created_at', 'deepline_runs', ['created_at'])

    # 12. Deepline Run Leads
    op.create_table(
        'deepline_run_leads',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=128), sa.ForeignKey('deepline_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_id', sa.String(length=128), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=64), server_default='QUALIFIED', nullable=False),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    )
    op.create_index('idx_deepline_run_leads_run', 'deepline_run_leads', ['run_id'])
    op.create_index('idx_deepline_run_leads_lead', 'deepline_run_leads', ['lead_id'])

    # 13. Smartlead Campaigns
    op.create_table(
        'smartlead_campaigns',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('campaign_id', sa.String(length=128), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('smartlead_campaign_id', sa.String(length=128), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=64), server_default='DRAFT', nullable=False),
        sa.Column('track_settings', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_smartlead_campaigns_camp_id', 'smartlead_campaigns', ['campaign_id'])

    # 14. Smartlead Leads
    op.create_table(
        'smartlead_leads',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('smartlead_campaign_id', sa.Integer(), sa.ForeignKey('smartlead_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_id', sa.String(length=128), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_index', sa.Integer(), server_default='1', nullable=False),
        sa.Column('status', sa.String(length=64), server_default='STAGED', nullable=False),
        sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('staged_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_smartlead_leads_campaign', 'smartlead_leads', ['smartlead_campaign_id'])
    op.create_index('idx_smartlead_leads_lead', 'smartlead_leads', ['lead_id'])

    # 15. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=128), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('actor', sa.String(length=128), server_default='SYSTEM', nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_audit_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_created_at', 'audit_logs', ['created_at'])

    # 16. Outreach Events
    op.create_table(
        'outreach_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.String(length=128), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('campaign_id', sa.String(length=128), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_outreach_events_lead_time', 'outreach_events', ['lead_id', 'occurred_at'])
    op.create_index('idx_outreach_events_type', 'outreach_events', ['event_type'])


def downgrade() -> None:
    op.drop_table('outreach_events')
    op.drop_table('audit_logs')
    op.drop_table('smartlead_leads')
    op.drop_table('smartlead_campaigns')
    op.drop_table('deepline_run_leads')
    op.drop_table('deepline_runs')
    op.drop_table('email_approvals')
    op.drop_table('email_drafts')
    op.drop_table('voc_context')
    op.drop_table('lead_evidence')
    op.drop_table('lead_research')
    op.drop_table('leads')
    op.drop_table('icp_approvals')
    op.drop_table('icp_versions')
    op.drop_table('icps')
    op.drop_table('campaigns')
