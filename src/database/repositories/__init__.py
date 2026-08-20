"""
repositories package for Aedrix PostgreSQL Database.
Exports all repository classes.
"""

from src.database.repositories.campaign_repository import CampaignRepository
from src.database.repositories.icp_repository import ICPRepository
from src.database.repositories.lead_repository import LeadRepository
from src.database.repositories.email_draft_repository import EmailDraftRepository
from src.database.repositories.approval_repository import ApprovalRepository
from src.database.repositories.deepline_repository import DeeplineRunRepository
from src.database.repositories.smartlead_repository import SmartleadRepository
from src.database.repositories.audit_repository import AuditRepository

__all__ = [
    "CampaignRepository",
    "ICPRepository",
    "LeadRepository",
    "EmailDraftRepository",
    "ApprovalRepository",
    "DeeplineRunRepository",
    "SmartleadRepository",
    "AuditRepository",
]
