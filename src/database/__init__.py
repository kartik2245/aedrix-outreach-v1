"""
database package for Aedrix Cold Outreach System.
Provides connection pooling, DeclarativeBase, normalized models, and repository interfaces for Supabase PostgreSQL.
"""

from src.database.base import Base, TimestampMixin
from src.database.connection import (
    get_engine,
    get_session_factory,
    get_db_session,
    get_db,
    is_database_enabled,
    check_db_health,
    get_database_url,
)
from src.database.models import (
    Campaign,
    ICP,
    ICPVersion,
    ICPApproval,
    Lead,
    LeadResearch,
    LeadEvidence,
    VoCContext,
    EmailDraft,
    EmailApproval,
    DeeplineRun,
    DeeplineRunLead,
    SmartleadCampaign,
    SmartleadLead,
    AuditLog,
    OutreachEvent,
)
from src.database.repositories import (
    CampaignRepository,
    ICPRepository,
    LeadRepository,
    EmailDraftRepository,
    ApprovalRepository,
    DeeplineRunRepository,
    SmartleadRepository,
    AuditRepository,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "get_db",
    "is_database_enabled",
    "check_db_health",
    "get_database_url",
    "Campaign",
    "ICP",
    "ICPVersion",
    "ICPApproval",
    "Lead",
    "LeadResearch",
    "LeadEvidence",
    "VoCContext",
    "EmailDraft",
    "EmailApproval",
    "DeeplineRun",
    "DeeplineRunLead",
    "SmartleadCampaign",
    "SmartleadLead",
    "AuditLog",
    "OutreachEvent",
    "CampaignRepository",
    "ICPRepository",
    "LeadRepository",
    "EmailDraftRepository",
    "ApprovalRepository",
    "DeeplineRunRepository",
    "SmartleadRepository",
    "AuditRepository",
]
