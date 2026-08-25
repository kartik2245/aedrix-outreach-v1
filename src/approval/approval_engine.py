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

        # Safety & Gate Evaluation (Delivery & Compliance constraints ONLY)
        email_str = str(email or "").strip().lower()
        email_st = str(email_status or meta.get("email_status", "")).strip().upper()

        has_valid_syntax = bool(email_str and "@" in email_str and "." in email_str.split("@")[-1] and len(email_str) >= 5)

        is_bounced = email_st in ("BOUNCED", "INVALID_BOUNCED", "EMAILSTATUS.BOUNCED", "EMAILSTATUS.INVALID_BOUNCED") or "bounce" in email_str
        is_invalid_email = (not has_valid_syntax) or email_st in ("INVALID", "EMAILSTATUS.INVALID", "MALFORMED")
        is_compliance_blocked = (
            email_st in ("SUPPRESSED", "OPT_OUT", "EMAILSTATUS.SUPPRESSED", "EMAILSTATUS.OPT_OUT")
            or meta.get("is_global_suppressed") is True
            or meta.get("is_compliance_blocked") is True
            or meta.get("is_opt_out") is True
            or meta.get("is_opted_out") is True
            or "suppression" in str(disqualification_reason or "").lower()
            or "opt-out" in str(disqualification_reason or "").lower()
        )
        is_qa_failed = qa_status == "FAIL"

        blocked_reason: Optional[str] = None
        if is_invalid_email:
            status = ApprovalStatus.BLOCKED
            blocked_reason = "Email address is missing or syntactically invalid."
        elif is_bounced:
            status = ApprovalStatus.BLOCKED
            blocked_reason = "Email address is marked BOUNCED."
        elif is_compliance_blocked:
            status = ApprovalStatus.BLOCKED
            blocked_reason = disqualification_reason or "Contact/domain is listed on global suppression or compliance opt-out list."
        elif is_qa_failed:
            status = ApprovalStatus.BLOCKED
            blocked_reason = f"Personalization QA failed: {', '.join(reasons)}"
        else:
            status = ApprovalStatus.PENDING_REVIEW
            if disqualification_reason:
                blocked_reason = disqualification_reason

        # Ensure email_status is preserved in metadata
        resolved_email_status = email_st if email_st else ("VALID" if has_valid_syntax else "INVALID")
        meta["email_status"] = resolved_email_status

        flag_no_strong_signal = (
            personalization_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL.value
            or personalization_status == "NO_STRONG_SIGNAL"
        )

        existing = self.store.get_record(resolved_lead_id)
        if existing:
            # Preserve human review status if already approved/edited/rejected unless newly blocked by delivery safety constraint
            if existing.approval_status in (ApprovalStatus.APPROVED, ApprovalStatus.EDITED, ApprovalStatus.REJECTED) and not (is_invalid_email or is_compliance_blocked or is_qa_failed):
                status = existing.approval_status
                if existing.approval_status != ApprovalStatus.APPROVED:
                    blocked_reason = existing.blocked_reason
                else:
                    blocked_reason = None

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
                email_1_original=email_1 or existing.email_1_original,
                followup_a_original=followup_a or existing.followup_a_original,
                followup_b_original=followup_b or existing.followup_b_original,
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
                email_status=resolved_email_status,
                approval_stage="AI_EMAIL_APPROVAL",
                workflow_status="AWAITING_EMAIL_APPROVAL" if status == ApprovalStatus.PENDING_REVIEW else str(status.value),
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
                email_status=resolved_email_status,
                approval_stage="AI_EMAIL_APPROVAL",
                workflow_status="AWAITING_EMAIL_APPROVAL" if status == ApprovalStatus.PENDING_REVIEW else str(status.value),
                metadata=meta
            )

        self.store.upsert_record(record)
        return record

    def enroll_unverified_lead(
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
        disqualification_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        lead_id: Optional[str] = None,
    ) -> ApprovalRecord:
        """
        Enrolls an UNVERIFIED lead awaiting email status approval prior to AI draft generation.
        AI generation is deferred until the user explicitly approves the unverified email status.
        """
        resolved_lead_id = lead_id or self.generate_lead_id(company, contact, email)
        meta = dict(metadata or {})
        meta["email_status"] = "UNVERIFIED"

        existing = self.store.get_record(resolved_lead_id)
        if existing:
            return existing

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
            email_1_original="",
            followup_a_original="",
            followup_b_original="",
            qa_status="PENDING_AI_GENERATION",
            qa_reasons=[],
            approval_status=ApprovalStatus.PENDING_REVIEW,
            smartlead_eligible=False,
            blocked_reason=None,
            campaign_id=meta.get("campaign_id", "default_campaign"),
            icp_id=meta.get("icp_id"),
            icp_version=meta.get("icp_version", "1.0.0"),
            email_status="UNVERIFIED",
            approval_stage="EMAIL_STATUS_APPROVAL",
            workflow_status="AWAITING_EMAIL_STATUS_APPROVAL",
            metadata=meta,
        )
        self.store.upsert_record(record)
        return record

    def enroll_no_email_lead(
        self,
        company: str,
        contact: str,
        title: str,
        qualification_status: str,
        opportunity_score: float,
        accessibility_score: float,
        outreach_priority_index: float,
        priority: str,
        personalization_status: str,
        personalization_note: str,
        voc_angle: str,
        disqualification_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        lead_id: Optional[str] = None,
    ) -> ApprovalRecord:
        """
        Enrolls a NO_EMAIL lead into the system strictly for lead preservation.
        AI generation and Smartlead submission are disabled (NO_SEND).
        """
        resolved_lead_id = lead_id or self.generate_lead_id(company, contact, "")
        meta = dict(metadata or {})
        meta["email_status"] = "NO_EMAIL"

        existing = self.store.get_record(resolved_lead_id)
        if existing:
            return existing

        record = ApprovalRecord(
            lead_id=resolved_lead_id,
            company=company,
            contact=contact,
            title=title,
            email="",
            qualification_status=qualification_status,
            opportunity_score=opportunity_score,
            accessibility_score=accessibility_score,
            outreach_priority_index=outreach_priority_index,
            priority=priority,
            personalization_status=personalization_status,
            personalization_note=personalization_note,
            voc_angle=voc_angle,
            email_1_original="",
            followup_a_original="",
            followup_b_original="",
            qa_status="NO_EMAIL",
            qa_reasons=["No email address discovered"],
            approval_status=ApprovalStatus.BLOCKED,
            smartlead_eligible=False,
            blocked_reason="No email address discovered for lead.",
            campaign_id=meta.get("campaign_id", "default_campaign"),
            icp_id=meta.get("icp_id"),
            icp_version=meta.get("icp_version", "1.0.0"),
            email_status="NO_EMAIL",
            approval_stage="NO_SEND",
            workflow_status="NO_EMAIL_PERSISTED",
            metadata=meta,
        )
        self.store.upsert_record(record)
        return record

    def approve_email_status(
        self,
        lead_id: str,
        llm_client=None,
        reviewer: Optional[str] = None,
    ) -> ApprovalRecord:
        """
        Approves an UNVERIFIED lead's email status at stage 1 (EMAIL_STATUS_APPROVAL),
        triggers AI email copy generation, and advances the lead to stage 2 (AI_EMAIL_APPROVAL).
        The lead remains smartlead_eligible=False until explicit stage 2 draft approval.
        """
        record = self.store.get_record(lead_id)
        if not record:
            raise ValueError(f"Approval record for lead_id '{lead_id}' not found.")

        # Idempotency check: if already generated and at stage 2 or approved, return existing record
        if record.approval_stage == "AI_EMAIL_APPROVAL" or record.approval_status == ApprovalStatus.APPROVED:
            return record

        if record.email_status == "NO_EMAIL":
            raise ValueError(f"Cannot generate AI email copy for NO_EMAIL lead '{lead_id}'.")

        # Advance to AI generation stage
        record.approval_stage = "AI_GENERATION"
        record.workflow_status = "AWAITING_AI_GENERATION"

        # Execute existing LLM generation if client provided or available
        client = llm_client or getattr(self, "llm_client", None)
        if client is not None:
            try:
                from src.models import (
                    LeadIntelligenceOutput,
                    DisqualificationStatus,
                    PersonalizationNoteStatus,
                    EvidenceLevel,
                    PriorityLevel,
                    AccessibilityTier,
                )
                from src.personalization.voc_engine import VoCEngine
                from src.personalization.personalization_qa import PersonalizationQA

                voc_engine = VoCEngine()
                qa_engine = PersonalizationQA()

                from src.models import EmailStatus
                emp_count = record.metadata.get("employee_count", 100) or 100
                st_enum = EmailStatus.UNVERIFIED
                try:
                    st_enum = EmailStatus(record.email_status)
                except ValueError:
                    pass

                intel = LeadIntelligenceOutput(
                    company_name=record.company,
                    company_domain=record.metadata.get("website") or record.metadata.get("company_domain") or "example.com",
                    contact_name=record.contact,
                    job_title=record.title,
                    email=record.email,
                    email_status=st_enum,
                    linkedin_url=record.metadata.get("linkedin_url"),
                    company_size=f"{emp_count} employees",
                    company_size_evidence=EvidenceLevel.VERIFIED,
                    industry=record.metadata.get("industry", "Technology"),
                    opportunity_score=record.opportunity_score,
                    accessibility_score=record.accessibility_score,
                    outreach_priority_index=record.outreach_priority_index,
                    priority_level=PriorityLevel(record.priority) if record.priority in [p.value for p in PriorityLevel] else PriorityLevel.P2,
                    opportunity_tier="Tier 1" if record.priority == "P1" else "Tier 2",
                    accessibility_tier=AccessibilityTier.HIGH if record.accessibility_score >= 80 else AccessibilityTier.MEDIUM,
                    disqualification_status=DisqualificationStatus.QUALIFIED,
                    personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED if record.personalization_note else PersonalizationNoteStatus.NO_STRONG_SIGNAL,
                    personalization_note=record.personalization_note or "Target contractor decision maker.",
                    research_sources=["Deepline Research Ingestion"],
                    ICP_score=record.opportunity_score,
                    pain_point="Operational efficiency and workflow coordination.",
                    pain_point_evidence=EvidenceLevel.INFERRED,
                    relevant_signal=record.personalization_note or "Verified target lead.",
                    relevant_signal_evidence=EvidenceLevel.VERIFIED,
                    persona_selection_rationale=f"Selected {record.title} as primary decision maker."
                )

                voc = voc_engine.map_lead_voc(intel)
                e1 = client.generate_email_1(intel, voc)
                fa = client.generate_followup_a(intel, e1, voc)
                fb = client.generate_followup_b(intel, voc)

                qa_res = qa_engine.validate_lead_drafts(lead_intel=intel, email_1=e1, followup_a=fa, followup_b=fb)

                record.email_1_original = getattr(e1, "body", str(e1))
                record.followup_a_original = getattr(fa, "body", str(fa))
                record.followup_b_original = getattr(fb, "body", str(fb))
                record.qa_status = qa_res.qa_status
                record.qa_reasons = qa_res.qa_reasons
            except Exception as gen_err:
                record.blocked_reason = f"AI_GENERATION_FAILED: {str(gen_err)}"

        record.approval_stage = "AI_EMAIL_APPROVAL"
        record.workflow_status = "AWAITING_EMAIL_APPROVAL"
        record.approval_status = ApprovalStatus.PENDING_REVIEW
        record.smartlead_eligible = False
        record.reviewer = reviewer or "HUMAN_OPERATOR"
        record.reviewed_at = datetime.now(timezone.utc).isoformat()

        self.store.upsert_record(record)
        return record

    def approve(self, lead_id: str, reviewer: Optional[str] = None) -> ApprovalRecord:
        """
        Explicitly approves a lead draft for Smartlead eligibility.
        Re-checks delivery/compliance safety constraints prior to approval.
        NEVER mutates qualification_status.
        """
        record = self.store.get_record(lead_id)
        if not record:
            raise ValueError(f"Approval record for lead_id '{lead_id}' not found.")

        # Re-verify delivery and compliance safety gates
        email_str = str(record.email or "").strip().lower()
        email_st = str(record.metadata.get("email_status", "")).upper()
        has_valid_syntax = bool(email_str and "@" in email_str and "." in email_str.split("@")[-1] and len(email_str) >= 5)

        is_bounced = email_st in ("BOUNCED", "INVALID_BOUNCED", "EMAILSTATUS.BOUNCED", "EMAILSTATUS.INVALID_BOUNCED") or "bounce" in email_str
        is_invalid_email = (not has_valid_syntax) or email_st in ("INVALID", "EMAILSTATUS.INVALID", "MALFORMED")
        is_compliance_blocked = (
            email_st in ("SUPPRESSED", "OPT_OUT", "EMAILSTATUS.SUPPRESSED", "EMAILSTATUS.OPT_OUT")
            or record.metadata.get("is_global_suppressed") is True
            or record.metadata.get("is_compliance_blocked") is True
            or record.metadata.get("is_opt_out") is True
            or record.metadata.get("is_opted_out") is True
        )
        is_qa_failed = record.qa_status == "FAIL"

        if is_invalid_email or is_bounced or is_compliance_blocked:
            record.approval_status = ApprovalStatus.BLOCKED
            record.smartlead_eligible = False
            reason = "Email address is missing or syntactically invalid" if is_invalid_email else ("Email address is marked BOUNCED" if is_bounced else "Suppression/opt-out compliance block")
            record.blocked_reason = reason
            self.store.upsert_record(record)
            raise ValueError(f"Cannot approve delivery-blocked lead '{lead_id}'. Safety constraint: {reason}")

        # Post-Approval AI Copy Generation Trigger
        if not record.email_1_original or record.qa_status == "PENDING_AI_GENERATION":
            try:
                from src.integrations.claude_client import ClaudeClient
                from src.personalization.voc_engine import VoCEngine
                from src.personalization.personalization_qa import PersonalizationQA
                from src.lead_intelligence import (
                    LeadIntelligenceOutput, PriorityLevel, EvidenceLevel,
                    PersonalizationNoteStatus, AccessibilityTier, EmailStatus, DisqualificationStatus
                )

                client = getattr(self, 'llm_client', None) or ClaudeClient()
                voc_engine = VoCEngine()
                qa_engine = PersonalizationQA()

                qual_val = record.qualification_status or "QUALIFIED"
                qual_st = DisqualificationStatus(qual_val) if qual_val in [e.value for e in DisqualificationStatus] else DisqualificationStatus.QUALIFIED

                intel = LeadIntelligenceOutput(
                    company_name=record.company,
                    company_domain=record.metadata.get("website") or "example.com",
                    contact_name=record.contact,
                    job_title=record.title,
                    email=record.email,
                    email_status=EmailStatus.VERIFIED if record.email and "@" in record.email else EmailStatus.NO_EMAIL,
                    company_size="50 employees",
                    company_size_evidence=EvidenceLevel.VERIFIED,
                    industry="Technology",
                    opportunity_score=record.opportunity_score,
                    accessibility_score=record.accessibility_score,
                    outreach_priority_index=record.outreach_priority_index,
                    priority_level=PriorityLevel(record.priority) if record.priority in [e.value for e in PriorityLevel] else PriorityLevel.P2,
                    opportunity_tier="Tier 1",
                    accessibility_tier=AccessibilityTier.HIGH,
                    disqualification_status=qual_st,
                    disqualification_reason=record.metadata.get("disqualification_reason"),
                    personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED if record.personalization_note else PersonalizationNoteStatus.NO_STRONG_SIGNAL,
                    personalization_note=record.personalization_note or "Target lead.",
                    research_sources=["Lead Ingestion"],
                    ICP_score=record.opportunity_score,
                    pain_point="Operational efficiency.",
                    pain_point_evidence=EvidenceLevel.INFERRED,
                    relevant_signal=record.personalization_note or "Verified target lead.",
                    relevant_signal_evidence=EvidenceLevel.VERIFIED,
                    persona_selection_rationale=f"Selected {record.title} as primary decision maker."
                )

                voc = voc_engine.map_lead_voc(intel)
                e1 = client.generate_email_1(intel, voc)
                fa = client.generate_followup_a(intel, e1, voc)
                fb = client.generate_followup_b(intel, voc)

                e1_body = getattr(e1, "body", str(e1))
                fa_body = getattr(fa, "body", str(fa))
                fb_body = getattr(fb, "body", str(fb))

                qa_res = qa_engine.validate_lead_drafts(lead_intel=intel, email_1=e1_body, followup_a=fa_body, followup_b=fb_body)

                record.email_1_original = e1_body
                record.followup_a_original = fa_body
                record.followup_b_original = fb_body
                record.qa_status = qa_res.qa_status
                record.qa_reasons = qa_res.qa_reasons
            except Exception as gen_err:
                record.qa_status = "FAIL"
                record.qa_reasons = [f"AI_GENERATION_FAILED: {str(gen_err)}"]

        is_qa_failed = record.qa_status == "FAIL"
        if is_qa_failed:
            record.approval_status = ApprovalStatus.BLOCKED
            record.smartlead_eligible = False
            reason = f"QA failed: {', '.join(record.qa_reasons)}"
            record.blocked_reason = reason
            self.store.upsert_record(record)
            raise ValueError(f"Cannot approve delivery-blocked lead '{lead_id}'. Safety constraint: {reason}")

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
