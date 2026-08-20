"""
icp_approval_models.py
Data models and audit structures for the Human ICP Approval & Safety Gate layer (Python 3.12).
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from src.icp.icp_models import ICPConfig, ICPStatus, ICPSource


class ICPAuditEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    action: str
    reviewer: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ICPApprovalRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    icp_id: str
    campaign_id: str
    name: str
    version: str = "1.0.0"
    status: ICPStatus = ICPStatus.PENDING_REVIEW
    source: ICPSource = Field(default=ICPSource.CLAUDE_GENERATED, description="Origin: CLAUDE_GENERATED or MANUAL")
    original_claude_icp: Optional[ICPConfig] = None
    effective_icp: ICPConfig
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    blocked_reason: Optional[str] = None
    deepline_eligible: bool = False
    deepline_run_ids: List[str] = Field(default_factory=list)
    edit_history: List[Dict[str, Any]] = Field(default_factory=list)
    audit_trail: List[ICPAuditEntry] = Field(default_factory=list)
