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
        meta = dict(metadata or {})
        is_invalid_email = email_status in ("INVALID_BOUNCED", "EmailStatus.INVALID_BOUNCED")
        is_compliance_blocked = meta.get("is_global_suppressed") is True or meta.get("is_compliance_blocked") is True or meta.get("is_opt_out") is True or "suppression" in str(disqualification_reason or "").lower() or "opt-out" in str(disqualification_reason or "").lower()
        is_qa_failed = qa_status == "FAIL"

        blocked_reason: Optional[str] = None
        if is_invalid_email:
            status = ApprovalStatus.BLOCKED.value
            blocked_reason = "Email address is marked INVALID_BOUNCED or missing."
        elif is_compliance_blocked:
            status = ApprovalStatus.BLOCKED.value
            blocked_reason = disqualification_reason or "Contact/domain is listed on global suppression or compliance opt-out list."
        elif is_qa_failed:
            status = ApprovalStatus.BLOCKED.value
            blocked_reason = f"Personalization QA failed: {', '.join(qa_reasons or [])}"
        else:
            status = ApprovalStatus.PENDING_REVIEW.value
            if disqualification_reason:
                blocked_reason = disqualification_reason

        flag_no_strong_signal = personalization_status in ("NO_STRONG_SIGNAL", "PersonalizationNoteStatus.NO_STRONG_SIGNAL")

        existing = self.session.scalar(select(EmailApproval).where(EmailApproval.lead_id == lead_id))
        if existing:
            # Preserve approved status if not delivery/compliance safety blocked
            if existing.approval_status in (ApprovalStatus.APPROVED.value, ApprovalStatus.EDITED.value, ApprovalStatus.REJECTED.value) and not (is_invalid_email or is_compliance_blocked or is_qa_failed):
                status = existing.approval_status
                if existing.approval_status != ApprovalStatus.APPROVED.value:
                    blocked_reason = existing.blocked_reason
                else:
                    blocked_reason = None

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

        lead = approval.lead
        draft = lead.email_draft if lead else None
        meta = approval.metadata_json or {}

        is_invalid_email = (lead and lead.email_status in ("INVALID_BOUNCED", "EmailStatus.INVALID_BOUNCED")) or not lead or not lead.email or "@" not in lead.email
        is_compliance_blocked = meta.get("is_global_suppressed") is True or meta.get("is_compliance_blocked") is True or meta.get("is_opt_out") is True

        if is_invalid_email or is_compliance_blocked:
            approval.approval_status = ApprovalStatus.BLOCKED.value
            approval.smartlead_eligible = False
            reason = "Email address is invalid/bounced" if is_invalid_email else "Suppression/opt-out compliance block"
            approval.blocked_reason = reason
            self.session.flush()
            raise ValueError(f"Cannot approve delivery-blocked lead '{lead_id}': {reason}")

        # Post-Approval AI Copy Generation Trigger
        if draft and (not draft.ai_original_email_1 or draft.qa_status == "PENDING_AI_GENERATION"):
            try:
                from src.integrations.claude_client import ClaudeClient
                from src.personalization.voc_engine import VoCEngine
                from src.personalization.personalization_qa import PersonalizationQA
                from src.lead_intelligence import (
                    LeadIntelligenceOutput, PriorityLevel, EvidenceLevel,
                    PersonalizationNoteStatus, AccessibilityTier, EmailStatus, DisqualificationStatus
                )

                client = ClaudeClient()
                voc_engine = VoCEngine()
                qa_engine = PersonalizationQA()

                qual_val = lead.qualification_status if lead else "QUALIFIED"
                qual_st = DisqualificationStatus(qual_val) if qual_val in [e.value for e in DisqualificationStatus] else DisqualificationStatus.QUALIFIED

                intel = LeadIntelligenceOutput(
                    company_name=lead.company_name if lead else "Unknown",
                    company_domain=lead.company_domain or "example.com",
                    contact_name=lead.contact_name if lead else "Unknown",
                    job_title=lead.job_title if lead else "Decision Maker",
                    email=lead.email if lead else "",
                    email_status=EmailStatus.VERIFIED if lead and lead.email and "@" in lead.email else EmailStatus.NO_EMAIL,
                    company_size=lead.company_size if (lead and lead.company_size) else "50 employees",
                    company_size_evidence=EvidenceLevel.VERIFIED,
                    industry=lead.industry if (lead and lead.industry) else "Technology",
                    opportunity_score=lead.opportunity_score if lead else 70.0,
                    accessibility_score=lead.accessibility_score if lead else 70.0,
                    outreach_priority_index=lead.outreach_priority_index if lead else 70.0,
                    priority_level=PriorityLevel(lead.priority_level) if lead and lead.priority_level in [e.value for e in PriorityLevel] else PriorityLevel.P2,
                    opportunity_tier="Tier 1",
                    accessibility_tier=AccessibilityTier.HIGH,
                    disqualification_status=qual_st,
                    disqualification_reason=lead.disqualification_reason if lead else None,
                    personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED if lead and lead.personalization_note else PersonalizationNoteStatus.NO_STRONG_SIGNAL,
                    personalization_note=lead.personalization_note if lead else "Target lead.",
                    research_sources=["Lead Ingestion"],
                    ICP_score=lead.opportunity_score if lead else 70.0,
                    pain_point="Operational efficiency.",
                    pain_point_evidence=EvidenceLevel.INFERRED,
                    relevant_signal=lead.personalization_note if lead else "Verified target lead.",
                    relevant_signal_evidence=EvidenceLevel.VERIFIED,
                    persona_selection_rationale=f"Selected {lead.job_title if lead else 'Decision Maker'} as primary decision maker."
                )

                voc = voc_engine.map_lead_voc(intel)
                e1 = client.generate_email_1(intel, voc)
                fa = client.generate_followup_a(intel, e1, voc)
                fb = client.generate_followup_b(intel, voc)

                e1_body = getattr(e1, "body", str(e1))
                fa_body = getattr(fa, "body", str(fa))
                fb_body = getattr(fb, "body", str(fb))

                qa_res = qa_engine.validate_lead_drafts(lead_intel=intel, email_1=e1_body, followup_a=fa_body, followup_b=fb_body)

                draft.ai_original_email_1 = e1_body
                draft.ai_original_followup_a = fa_body
                draft.ai_original_followup_b = fb_body
                draft.qa_status = qa_res.qa_status
                draft.qa_reasons = qa_res.qa_reasons
            except Exception as gen_err:
                draft.qa_status = "FAIL"
                draft.qa_reasons = [f"AI_GENERATION_FAILED: {str(gen_err)}"]

        is_qa_failed = draft and draft.qa_status == "FAIL"
        if is_qa_failed:
            approval.approval_status = ApprovalStatus.BLOCKED.value
            approval.smartlead_eligible = False
            reason = f"QA failed: {', '.join(draft.qa_reasons or [])}"
            approval.blocked_reason = reason
            self.session.flush()
            raise ValueError(f"Cannot approve delivery-blocked lead '{lead_id}': {reason}")

        now_dt = datetime.now(timezone.utc)
        approval.approval_status = ApprovalStatus.APPROVED.value
        approval.smartlead_eligible = True
        approval.reviewer = reviewer
        approval.reviewed_at = now_dt
        approval.blocked_reason = None

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
