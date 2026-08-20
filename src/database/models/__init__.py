"""
models package for Aedrix PostgreSQL Database.
Aggregates all 16 normalized models.
"""

from src.database.base import Base, TimestampMixin
from src.database.models.campaign import Campaign
from src.database.models.icp import ICP, ICPVersion, ICPApproval
from src.database.models.lead import Lead, LeadResearch, LeadEvidence, VoCContext
from src.database.models.email import EmailDraft, EmailApproval
from src.database.models.deepline import DeeplineRun, DeeplineRunLead
from src.database.models.smartlead import SmartleadCampaign, SmartleadLead
from src.database.models.audit import AuditLog, OutreachEvent

__all__ = [
    "Base",
    "TimestampMixin",
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
]
