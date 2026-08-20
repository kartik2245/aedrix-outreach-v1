"""
approval_repository.py
Repository for Human Email Approvals and Safety Gate transactions in PostgreSQL.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, desc

from src.database.models.lead import Lead
from src.database.models.email import EmailApproval, EmailDraft
from src.database.models.audit import AuditLog
from src.approval.approval_models import ApprovalStatus


class ApprovalRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_lead_id(self, lead_id: str) -> Optional[EmailApproval]:
        stmt = (
            select(EmailApproval)
            .options(
                joinedload(EmailApproval.lead).joinedload(Lead.email_draft)
            )
            .where(EmailApproval.lead_id == lead_id)
        )
        return self.session.scalar(stmt)

    def list_approvals(
        self,
        status: Optional[str] = None,
        campaign_id: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> List[EmailApproval]:
        stmt = (
            select(EmailApproval)
            .options(
                joinedload(EmailApproval.lead).joinedload(Lead.email_draft)
            )
            .join(Lead, EmailApproval.lead_id == Lead.id)
            .order_by(desc(EmailApproval.created_at))
        )
        if status:
            stmt = stmt.where(EmailApproval.approval_status == status.upper())
        if campaign_id:
            stmt = stmt.where(Lead.campaign_id == campaign_id)
        if environment:
            stmt = stmt.where(Lead.environment == environment.upper())

        return list(self.session.scalars(stmt).unique().all())

    def enroll_draft(
        self,
        lead_id: str,
        qualification_status: str,
        qa_status: str,
        qa_reasons: Optional[List[str]] = None,
        email_status: Optional[str] = None,
        disqualification_reason: Optional[str] = None,
        personalization_status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmailApproval:
        """Atomic evaluation and enrollment of a lead draft into the Human Approval Gate."""
        is_hard_disqualified = qualification_status in ("HARD_DISQUALIFIED", "DisqualificationStatus.HARD_DISQUALIFIED")
        is_campaign_excluded = qualification_status in ("CAMPAIGN_EXCLUDED", "DisqualificationStatus.CAMPAIGN_EXCLUDED")
        is_invalid_email = email_status in ("INVALID_BOUNCED", "EmailStatus.INVALID_BOUNCED")
        is_qa_failed = qa_status == "FAIL"

        blocked_reason: Optional[str] = None
        if is_hard_disqualified:
            status = ApprovalStatus.BLOCKED.value
            blocked_reason = disqualification_reason or "Account is HARD_DISQUALIFIED by ICP Engine."
        elif is_campaign_excluded:
            status = ApprovalStatus.BLOCKED.value
            blocked_reason = disqualification_reason or "Account is CAMPAIGN_EXCLUDED."
        elif is_invalid_email:
            status = ApprovalStatus.BLOCKED.value
            blocked_reason = "Email address is marked INVALID_BOUNCED."
        elif is_qa_failed:
            status = ApprovalStatus.BLOCKED.value
            blocked_reason = f"Personalization QA failed: {', '.join(qa_reasons or [])}"
        else:
            status = ApprovalStatus.PENDING_REVIEW.value

        flag_no_strong_signal = personalization_status in ("NO_STRONG_SIGNAL", "PersonalizationNoteStatus.NO_STRONG_SIGNAL")

        existing = self.session.scalar(select(EmailApproval).where(EmailApproval.lead_id == lead_id))
        if existing:
            # Preserve approved status if not hard disqualified
            if existing.approval_status in (ApprovalStatus.APPROVED.value, ApprovalStatus.EDITED.value, ApprovalStatus.REJECTED.value) and not (is_hard_disqualified or is_campaign_excluded or is_invalid_email):
                status = existing.approval_status
                blocked_reason = existing.blocked_reason

            existing.approval_status = status
            existing.smartlead_eligible = (status == ApprovalStatus.APPROVED.value)
            existing.blocked_reason = blocked_reason
            existing.flag_no_strong_signal = flag_no_strong_signal
            if metadata:
                existing.metadata_json = metadata
            self.session.flush()
            return existing

        approval = EmailApproval(
            lead_id=lead_id,
            approval_status=status,
            reviewer=None,
            reviewed_at=None,
            smartlead_eligible=(status == ApprovalStatus.APPROVED.value),
            blocked_reason=blocked_reason,
            flag_no_strong_signal=flag_no_strong_signal,
            metadata_json=metadata or {},
        )
        self.session.add(approval)

        audit = AuditLog(
            entity_type="LEAD",
            entity_id=lead_id,
            action="ENROLLED_FOR_REVIEW",
            actor="SYSTEM_PIPELINE",
            details={"status": status, "blocked_reason": blocked_reason}
        )
        self.session.add(audit)
        self.session.flush()
        return approval

    def approve_lead(self, lead_id: str, reviewer: str = "HUMAN_OPERATOR") -> EmailApproval:
        approval = self.session.scalar(select(EmailApproval).where(EmailApproval.lead_id == lead_id))
        if not approval:
            raise ValueError(f"Approval record for lead '{lead_id}' not found.")

        if approval.approval_status == ApprovalStatus.BLOCKED.value:
            raise ValueError(f"Cannot approve blocked lead '{lead_id}': {approval.blocked_reason}")

        now_dt = datetime.now(timezone.utc)
        approval.approval_status = ApprovalStatus.APPROVED.value
        approval.smartlead_eligible = True
        approval.reviewer = reviewer
        approval.reviewed_at = now_dt

        audit = AuditLog(
            entity_type="LEAD",
            entity_id=lead_id,
            action="APPROVED",
            actor=reviewer,
            details={"smartlead_eligible": True}
        )
        self.session.add(audit)
        self.session.flush()
        return approval

    def edit_lead(
        self,
        lead_id: str,
        email_1: Optional[str] = None,
        followup_a: Optional[str] = None,
        followup_b: Optional[str] = None,
        touch_3: Optional[str] = None,
        touch_4: Optional[str] = None,
        touch_5: Optional[str] = None,
        reviewer: str = "HUMAN_OPERATOR",
    ) -> EmailApproval:
        if touch_3 is not None or touch_4 is not None or touch_5 is not None:
            raise ValueError("Touch 3, 4, and 5 are non-executable in AEDRIX V1 sequence (Email 1, Follow-up A, Follow-up B only).")

        approval = self.session.scalar(select(EmailApproval).where(EmailApproval.lead_id == lead_id))
        if not approval:
            raise ValueError(f"Approval record for lead '{lead_id}' not found.")

        draft = self.session.scalar(select(EmailDraft).where(EmailDraft.lead_id == lead_id))
        if draft:
            if email_1 is not None:
                draft.edited_email_1 = email_1
            if followup_a is not None:
                draft.edited_followup_a = followup_a
            if followup_b is not None:
                draft.edited_followup_b = followup_b

        # Save edited touches in metadata_json
        meta = dict(approval.metadata_json or {})
        if touch_3 is not None:
            meta["edited_touch_3"] = touch_3
        if touch_4 is not None:
            meta["edited_touch_4"] = touch_4
        if touch_5 is not None:
            meta["edited_touch_5"] = touch_5
        approval.metadata_json = meta

        now_dt = datetime.now(timezone.utc)
        approval.approval_status = ApprovalStatus.EDITED.value
        approval.smartlead_eligible = False  # Invalidate prior approval!
        approval.reviewer = reviewer
        approval.reviewed_at = now_dt

        audit = AuditLog(
            entity_type="LEAD",
            entity_id=lead_id,
            action="EDITED",
            actor=reviewer,
            details={"status": "EDITED", "smartlead_eligible": False}
        )
        self.session.add(audit)
        self.session.flush()
        return approval

    def reject_lead(self, lead_id: str, reason: str, reviewer: str = "HUMAN_OPERATOR") -> EmailApproval:
        approval = self.session.scalar(select(EmailApproval).where(EmailApproval.lead_id == lead_id))
        if not approval:
            raise ValueError(f"Approval record for lead '{lead_id}' not found.")

        now_dt = datetime.now(timezone.utc)
        approval.approval_status = ApprovalStatus.REJECTED.value
        approval.smartlead_eligible = False
        approval.blocked_reason = reason
        approval.reviewer = reviewer
        approval.reviewed_at = now_dt

        audit = AuditLog(
            entity_type="LEAD",
            entity_id=lead_id,
            action="REJECTED",
            actor=reviewer,
            details={"reason": reason}
        )
        self.session.add(audit)
        self.session.flush()
        return approval

    def block_lead(self, lead_id: str, reason: str, reviewer: str = "HUMAN_OPERATOR") -> EmailApproval:
        approval = self.session.scalar(select(EmailApproval).where(EmailApproval.lead_id == lead_id))
        if not approval:
            raise ValueError(f"Approval record for lead '{lead_id}' not found.")

        now_dt = datetime.now(timezone.utc)
        approval.approval_status = ApprovalStatus.BLOCKED.value
        approval.smartlead_eligible = False
        approval.blocked_reason = reason
        approval.reviewer = reviewer
        approval.reviewed_at = now_dt

        audit = AuditLog(
            entity_type="LEAD",
            entity_id=lead_id,
            action="BLOCKED",
            actor=reviewer,
            details={"reason": reason}
        )
        self.session.add(audit)
        self.session.flush()
        return approval
