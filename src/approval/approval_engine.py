"""
approval_engine.py
Human Approval & Safety Gate Engine for Aedrix Cold Outreach System (Python 3.12).

Enforces:
- All generated drafts start as PENDING_REVIEW (smartlead_eligible=False).
- Hard disqualifications, campaign exclusions, invalid emails, and QA failures are auto-BLOCKED.
- NO_STRONG_SIGNAL leads remain reviewable but explicitly flagged.
- Original AI-generated drafts are immutable.
- Edited drafts require explicit human re-approval.
- Only explicitly APPROVED drafts become Smartlead-eligible.
- ZERO automated email sending or API dispatching.
"""

import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.approval.approval_models import ApprovalRecord, ApprovalStatus
from src.approval.approval_store import ApprovalStore
from src.models import (
    DisqualificationStatus,
    PersonalizationNoteStatus,
    EmailStatus,
)


class ApprovalEngine:
    def __init__(self, store: Optional[ApprovalStore] = None):
        self.store = store or ApprovalStore()

    def generate_lead_id(self, company: str, contact: str, email: str) -> str:
        """Generates a clean deterministic slug ID for a lead."""
        slug_company = re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")
        slug_contact = re.sub(r"[^a-z0-9]+", "_", contact.lower()).strip("_")
        if not slug_company and not slug_contact:
            slug_email = re.sub(r"[^a-z0-9]+", "_", email.lower()).strip("_")
            return f"lead_{slug_email}"
        return f"lead_{slug_company}_{slug_contact}".strip("_")

    def enroll_draft(
        self,
        company: str,
        contact: str,
        title: str,
        email: str,
        qualification_status: str,
        opportunity_score: float,
        accessibility_score: float,
        outreach_priority_index: float,
        priority: str,
        personalization_status: str,
        personalization_note: str,
        voc_angle: str,
        email_1: str,
        followup_a: str,
        followup_b: str,
        qa_status: str,
        qa_reasons: Optional[List[str]] = None,
        email_status: Optional[str] = None,
        disqualification_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        lead_id: Optional[str] = None,
    ) -> ApprovalRecord:
        """
        Creates or updates an approval queue record from batch pipeline output.
        Automatically sets initial approval and safety status.
        """
        resolved_lead_id = lead_id or self.generate_lead_id(company, contact, email)
        reasons = list(qa_reasons or [])
        meta = dict(metadata or {})

        # Safety & Gate Evaluation
        is_hard_disqualified = qualification_status == DisqualificationStatus.HARD_DISQUALIFIED.value or qualification_status == "HARD_DISQUALIFIED"
        is_campaign_excluded = qualification_status == DisqualificationStatus.CAMPAIGN_EXCLUDED.value or qualification_status == "CAMPAIGN_EXCLUDED"
        is_invalid_email = email_status == EmailStatus.INVALID_BOUNCED.value or email_status == "INVALID_BOUNCED" or "bounce" in email.lower()
        is_qa_failed = qa_status == "FAIL"

        blocked_reason: Optional[str] = None
        if is_hard_disqualified:
            status = ApprovalStatus.BLOCKED
            blocked_reason = disqualification_reason or "Account is HARD_DISQUALIFIED by ICP Engine."
        elif is_campaign_excluded:
            status = ApprovalStatus.BLOCKED
            blocked_reason = disqualification_reason or "Account is CAMPAIGN_EXCLUDED (CRM active / suppression / recent contact)."
        elif is_invalid_email:
            status = ApprovalStatus.BLOCKED
            blocked_reason = "Email address is marked INVALID_BOUNCED."
        elif is_qa_failed:
            status = ApprovalStatus.BLOCKED
            blocked_reason = f"Personalization QA failed: {', '.join(reasons)}"
        else:
            status = ApprovalStatus.PENDING_REVIEW

        flag_no_strong_signal = (
            personalization_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL.value
            or personalization_status == "NO_STRONG_SIGNAL"
        )

        existing = self.store.get_record(resolved_lead_id)
        if existing:
            # Preserve human review status if already approved/edited/rejected unless newly blocked by hard qualification
            if existing.approval_status in (ApprovalStatus.APPROVED, ApprovalStatus.EDITED, ApprovalStatus.REJECTED) and not (is_hard_disqualified or is_campaign_excluded or is_invalid_email):
                status = existing.approval_status
                blocked_reason = existing.blocked_reason

            record = ApprovalRecord(
                lead_id=resolved_lead_id,
                company=company,
                contact=contact,
                title=title,
                email=email,
                qualification_status=qualification_status,
                opportunity_score=opportunity_score,
                accessibility_score=accessibility_score,
                outreach_priority_index=outreach_priority_index,
                priority=priority,
                personalization_status=personalization_status,
                personalization_note=personalization_note,
                voc_angle=voc_angle,
                email_1_original=existing.email_1_original or email_1,
                followup_a_original=existing.followup_a_original or followup_a,
                followup_b_original=existing.followup_b_original or followup_b,
                qa_status=qa_status,
                qa_reasons=reasons,
                approval_status=status,
                reviewer=existing.reviewer,
                reviewed_at=existing.reviewed_at,
                edited_email_1=existing.edited_email_1,
                edited_followup_a=existing.edited_followup_a,
                edited_followup_b=existing.edited_followup_b,
                smartlead_eligible=(status == ApprovalStatus.APPROVED),
                blocked_reason=blocked_reason,
                flag_no_strong_signal=flag_no_strong_signal,
                campaign_id=meta.get("campaign_id", existing.campaign_id if existing else "default_campaign"),
                icp_id=meta.get("icp_id", existing.icp_id if existing else None),
                icp_version=meta.get("icp_version", existing.icp_version if existing else "1.0.0"),
                metadata=meta
            )
        else:
            record = ApprovalRecord(
                lead_id=resolved_lead_id,
                company=company,
                contact=contact,
                title=title,
                email=email,
                qualification_status=qualification_status,
                opportunity_score=opportunity_score,
                accessibility_score=accessibility_score,
                outreach_priority_index=outreach_priority_index,
                priority=priority,
                personalization_status=personalization_status,
                personalization_note=personalization_note,
                voc_angle=voc_angle,
                email_1_original=email_1,
                followup_a_original=followup_a,
                followup_b_original=followup_b,
                qa_status=qa_status,
                qa_reasons=reasons,
                approval_status=status,
                reviewer=None,
                reviewed_at=None,
                edited_email_1=None,
                edited_followup_a=None,
                edited_followup_b=None,
                smartlead_eligible=False,
                blocked_reason=blocked_reason,
                flag_no_strong_signal=flag_no_strong_signal,
                campaign_id=meta.get("campaign_id", "default_campaign"),
                icp_id=meta.get("icp_id"),
                icp_version=meta.get("icp_version", "1.0.0"),
                metadata=meta
            )

        self.store.upsert_record(record)
        return record

    def approve(self, lead_id: str, reviewer: Optional[str] = None) -> ApprovalRecord:
        """
        Explicitly approves a lead draft for Smartlead eligibility.
        """
        record = self.store.get_record(lead_id)
        if not record:
            raise ValueError(f"Approval record for lead_id '{lead_id}' not found.")

        if record.approval_status == ApprovalStatus.BLOCKED:
            raise ValueError(f"Cannot approve BLOCKED lead '{lead_id}'. Reason: {record.blocked_reason}")

        record.approval_status = ApprovalStatus.APPROVED
        record.smartlead_eligible = True
        record.reviewer = reviewer or "HUMAN_OPERATOR"
        record.reviewed_at = datetime.now(timezone.utc).isoformat()
        record.blocked_reason = None

        self.store.upsert_record(record)
        return record

    def reject(self, lead_id: str, reviewer: Optional[str] = None, reason: Optional[str] = None) -> ApprovalRecord:
        """
        Rejects a lead draft. Disallows Smartlead eligibility.
        """
        record = self.store.get_record(lead_id)
        if not record:
            raise ValueError(f"Approval record for lead_id '{lead_id}' not found.")

        record.approval_status = ApprovalStatus.REJECTED
        record.smartlead_eligible = False
        record.reviewer = reviewer or "HUMAN_OPERATOR"
        record.reviewed_at = datetime.now(timezone.utc).isoformat()
        record.blocked_reason = reason or "Rejected by human reviewer."

        self.store.upsert_record(record)
        return record

    def edit(
        self,
        lead_id: str,
        email_1: Optional[str] = None,
        followup_a: Optional[str] = None,
        followup_b: Optional[str] = None,
        touch_3: Optional[str] = None,
        touch_4: Optional[str] = None,
        touch_5: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> ApprovalRecord:
        """
        Saves edited versions of emails while preserving original AI drafts.
        Sets status to EDITED and requires explicit subsequent approval.
        """
        if touch_3 is not None or touch_4 is not None or touch_5 is not None:
            raise ValueError("Touch 3, 4, and 5 are non-executable in AEDRIX V1 sequence (Email 1, Follow-up A, Follow-up B only).")

        record = self.store.get_record(lead_id)
        if not record:
            raise ValueError(f"Approval record for lead_id '{lead_id}' not found.")

        if email_1 is not None:
            record.edited_email_1 = email_1
        if followup_a is not None:
            record.edited_followup_a = followup_a
        if followup_b is not None:
            record.edited_followup_b = followup_b

        record.approval_status = ApprovalStatus.EDITED
        record.smartlead_eligible = False  # Must be explicitly approved after editing
        record.reviewer = reviewer or "HUMAN_OPERATOR"
        record.reviewed_at = datetime.now(timezone.utc).isoformat()

        self.store.upsert_record(record)
        return record

    def block(self, lead_id: str, reason: str, reviewer: Optional[str] = None) -> ApprovalRecord:
        """
        Explicitly blocks a lead draft.
        """
        record = self.store.get_record(lead_id)
        if not record:
            raise ValueError(f"Approval record for lead_id '{lead_id}' not found.")

        record.approval_status = ApprovalStatus.BLOCKED
        record.smartlead_eligible = False
        record.blocked_reason = reason
        record.reviewer = reviewer or "HUMAN_OPERATOR"
        record.reviewed_at = datetime.now(timezone.utc).isoformat()

        self.store.upsert_record(record)
        return record

    def get_effective_drafts(self, record: ApprovalRecord) -> Dict[str, str]:
        """Returns the active email text (edited if present, else original)."""
        return {
            "email_1": record.edited_email_1 or record.email_1_original,
            "followup_a": record.edited_followup_a or record.followup_a_original,
            "followup_b": record.edited_followup_b or record.followup_b_original,
        }
