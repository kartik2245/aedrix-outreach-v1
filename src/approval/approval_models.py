"""
approval_models.py
Data models and Enums for the Aedrix Human Approval & Safety Gate layer (Python 3.12).
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ApprovalStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"
    BLOCKED = "BLOCKED"


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    lead_id: str
    company: str
    contact: str
    title: str
    email: str
    qualification_status: str
    opportunity_score: float = Field(ge=0, le=100)
    accessibility_score: float = Field(ge=0, le=100)
    outreach_priority_index: float = Field(ge=0, le=100)
    priority: str
    personalization_status: str
    personalization_note: str
    voc_angle: str
    email_1_original: str
    followup_a_original: str
    followup_b_original: str
    qa_status: str
    qa_reasons: List[str] = Field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING_REVIEW
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None
    edited_email_1: Optional[str] = None
    edited_followup_a: Optional[str] = None
    edited_followup_b: Optional[str] = None
    smartlead_eligible: bool = False
    blocked_reason: Optional[str] = None
    flag_no_strong_signal: bool = False
    campaign_id: str = "default_campaign"
    icp_id: Optional[str] = None
    icp_version: str = "1.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)
