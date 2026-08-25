"""
leads.py
FastAPI router for leads table, filtering, search, sorting, and comprehensive lead detail dossiers.
Supports Supabase PostgreSQL primary database with offline JSON fallback.
"""

import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.approval.approval_models import ApprovalRecord
from src.approval.approval_store import ApprovalStore
from src.database.connection import is_database_enabled, get_db_session
from src.database.repositories.lead_repository import LeadRepository

router = APIRouter(prefix="/leads", tags=["Leads"])


class LeadSummaryItem(BaseModel):
    lead_id: str
    company: str
    contact: str
    title: str
    email: str
    email_status: str = "VERIFIED"
    email_source: Optional[str] = None
    approval_stage: Optional[str] = None
    workflow_status: Optional[str] = None
    qualification_status: str
    opportunity_score: float
    accessibility_score: float
    outreach_priority_index: float
    priority: str
    personalization_status: str
    approval_status: str
    smartlead_eligible: bool
    qa_status: str


class LeadsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[LeadSummaryItem]


class LeadDetailResponse(BaseModel):
    lead_id: str
    company: str
    contact: str
    title: str
    email: str
    email_status: str = "VERIFIED"
    email_source: Optional[str] = None
    email_validated: Optional[bool] = None
    email_found_and_valid: Optional[bool] = None
    miss_reason: Optional[str] = None
    approval_stage: Optional[str] = None
    workflow_status: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    qualification_status: str
    disqualification_reason: Optional[str] = None
    opportunity_score: float
    accessibility_score: float
    outreach_priority_index: float
    priority: str
    evidence_levels: Dict[str, str] = Field(default_factory=dict)
    personalization_status: str
    personalization_note: str
    voc_angle: str
    research_signals: Optional[str] = None
    email_1: str
    followup_a: str
    followup_b: str
    email_1_original: str
    followup_a_original: str
    followup_b_original: str
    edited_email_1: Optional[str] = None
    edited_followup_a: Optional[str] = None
    edited_followup_b: Optional[str] = None
    qa_status: str
    qa_reasons: List[str] = Field(default_factory=list)
    approval_status: str
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None
    smartlead_eligible: bool
    blocked_reason: Optional[str] = None
    flag_no_strong_signal: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _load_lead_intel_lookup() -> Dict[str, Dict[str, Any]]:
    """Loads final_lead_intelligence.json if available to enrich leads."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    intel_path = os.path.join(base_dir, "data", "final_lead_intelligence.json")
    lookup = {}
    if os.path.exists(intel_path):
        try:
            with open(intel_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    email = item.get("email", "").lower()
                    if email:
                        lookup[email] = item
        except Exception:
            pass
    return lookup


@router.get("", response_model=LeadsListResponse)
def list_leads(
    search: Optional[str] = Query(None, description="Search company, contact, or email"),
    icp_status: Optional[str] = Query(None, description="Filter by ICP status"),
    priority: Optional[str] = Query(None, description="Filter by priority (P1, P2, P3)"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    personalization_status: Optional[str] = Query(None, description="Filter by personalization note status"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    sort_by: str = Query("outreach_priority_index", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> LeadsListResponse:
    """Lists leads with rich multi-filter, search, and pagination isolated by environment."""
    from src.config.app_mode import ModeService
    from src.demo.demo_data import DEMO_CAMPAIGN_ID

    mode_service = ModeService.get_instance()
    active_mode = mode_service.get_mode().value  # "DEMO" or "PRODUCTION"
    is_demo = mode_service.is_demo()

    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = LeadRepository(session)
                db_leads, total = repo.list_leads(
                    search=search,
                    icp_status=icp_status,
                    priority=priority,
                    approval_status=approval_status,
                    personalization_status=personalization_status,
                    campaign_id=campaign_id,
                    environment=active_mode,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    page=page,
                    page_size=page_size,
                )

                items = [
                    LeadSummaryItem(
                        lead_id=l.id,
                        company=l.company_name,
                        contact=l.contact_name,
                        title=l.job_title,
                        email=l.email,
                        email_status=l.email_status.value if hasattr(l.email_status, "value") else str(getattr(l, "email_status", "VERIFIED")),
                        email_source=getattr(l, "email_source", None),
                        approval_stage=l.email_approval.approval_stage if hasattr(l, "email_approval") and l.email_approval and hasattr(l.email_approval, "approval_stage") else "AI_EMAIL_APPROVAL",
                        workflow_status=l.email_approval.workflow_status if hasattr(l, "email_approval") and l.email_approval and hasattr(l.email_approval, "workflow_status") else "AWAITING_EMAIL_APPROVAL",
                        qualification_status=l.qualification_status,
                        opportunity_score=l.opportunity_score,
                        accessibility_score=l.accessibility_score,
                        outreach_priority_index=l.outreach_priority_index,
                        priority=l.priority_level,
                        personalization_status=l.personalization_status,
                        approval_status=l.email_approval.approval_status if l.email_approval else "PENDING_REVIEW",
                        smartlead_eligible=l.email_approval.smartlead_eligible if l.email_approval else False,
                        qa_status=l.email_draft.qa_status if l.email_draft else "PASS",
                    )
                    for l in db_leads
                ]
                total_pages = max(1, (total + page_size - 1) // page_size)
                return LeadsListResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                    items=items,
                )
        except Exception:
            pass

    # Offline JSON fallback
    store = ApprovalStore()
    all_records = store.load_queue()

    if is_demo:
        demo_recs = [r for r in all_records if r.campaign_id == DEMO_CAMPAIGN_ID or r.lead_id.startswith("demo_")]
        records = demo_recs if demo_recs else all_records
    else:
        records = [r for r in all_records if r.campaign_id != DEMO_CAMPAIGN_ID and not r.lead_id.startswith("demo_")]

    filtered = []
    for r in records:
        if search:
            q = search.lower()
            if q not in r.company.lower() and q not in r.contact.lower() and q not in r.email.lower() and q not in r.lead_id.lower():
                continue
        if icp_status and r.qualification_status.upper() != icp_status.upper():
            continue
        if priority and r.priority.upper() != priority.upper():
            continue
        if approval_status and r.approval_status.value.upper() != approval_status.upper():
            continue
        if personalization_status and r.personalization_status.upper() != personalization_status.upper():
            continue
        if campaign_id and r.campaign_id != campaign_id:
            continue
        filtered.append(r)

    reverse = (sort_order.lower() == "desc")
    if sort_by in ("opportunity_score", "accessibility_score", "outreach_priority_index"):
        filtered.sort(key=lambda x: getattr(x, sort_by, 0.0), reverse=reverse)
    elif sort_by in ("company", "contact", "email", "priority", "qualification_status"):
        filtered.sort(key=lambda x: str(getattr(x, sort_by, "")).lower(), reverse=reverse)
    else:
        filtered.sort(key=lambda x: x.outreach_priority_index, reverse=True)

    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start_idx = (page - 1) * page_size
    page_items = filtered[start_idx : start_idx + page_size]

    items = [
        LeadSummaryItem(
            lead_id=r.lead_id,
            company=r.company,
            contact=r.contact,
            title=r.title,
            email=r.email,
            email_status=getattr(r, "email_status", r.metadata.get("email_status", "VERIFIED")),
            email_source=getattr(r, "email_source", r.metadata.get("email_source")),
            approval_stage=getattr(r, "approval_stage", "AI_EMAIL_APPROVAL"),
            workflow_status=getattr(r, "workflow_status", "AWAITING_EMAIL_APPROVAL"),
            qualification_status=r.qualification_status,
            opportunity_score=r.opportunity_score,
            accessibility_score=r.accessibility_score,
            outreach_priority_index=r.outreach_priority_index,
            priority=r.priority,
            personalization_status=r.personalization_status,
            approval_status=r.approval_status.value,
            smartlead_eligible=r.smartlead_eligible,
            qa_status=r.qa_status,
        )
        for r in page_items
    ]

    return LeadsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/{lead_id}", response_model=LeadDetailResponse)
def get_lead_detail(lead_id: str) -> LeadDetailResponse:
    """Retrieves full lead dossier with verified evidence, VoC angle, and draft copy."""
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = LeadRepository(session)
                db_lead = repo.get_by_id(lead_id)
                if db_lead:
                    draft = db_lead.email_draft
                    app = db_lead.email_approval

                    e1_orig = draft.ai_original_email_1 if draft else ""
                    fa_orig = draft.ai_original_followup_a if draft else ""
                    fb_orig = draft.ai_original_followup_b if draft else ""

                    effective_e1 = (draft.edited_email_1 if draft and draft.edited_email_1 else e1_orig) or ""
                    effective_fa = (draft.edited_followup_a if draft and draft.edited_followup_a else fa_orig) or ""
                    effective_fb = (draft.edited_followup_b if draft and draft.edited_followup_b else fb_orig) or ""

                    evidence_levels = {}
                    if db_lead.evidence_items:
                        for ev in db_lead.evidence_items:
                            evidence_levels[ev.claim_type] = ev.evidence_level
                    else:
                        evidence_levels = {
                            "signal": "VERIFIED" if db_lead.personalization_status == "SIGNAL_VERIFIED" else "UNKNOWN",
                            "company_size": "VERIFIED",
                            "pain_point": "INFERRED",
                        }

                    return LeadDetailResponse(
                        lead_id=db_lead.id,
                        company=db_lead.company_name,
                        contact=db_lead.contact_name,
                        title=db_lead.job_title,
                        email=db_lead.email,
                        email_status=db_lead.email_status.value if hasattr(db_lead.email_status, "value") else str(getattr(db_lead, "email_status", "VERIFIED")),
                        email_source=getattr(db_lead, "email_source", app.metadata_json.get("email_source") if app else None),
                        email_validated=getattr(db_lead, "email_validated", app.metadata_json.get("email_validated") if app else None),
                        email_found_and_valid=getattr(db_lead, "email_found_and_valid", app.metadata_json.get("email_found_and_valid") if app else None),
                        miss_reason=getattr(db_lead, "miss_reason", app.metadata_json.get("miss_reason") if app else None),
                        approval_stage=app.approval_stage if app else "AI_EMAIL_APPROVAL",
                        workflow_status=app.workflow_status if app else "AWAITING_EMAIL_APPROVAL",
                        website=db_lead.company_domain,
                        linkedin_url=db_lead.linkedin_url,
                        qualification_status=db_lead.qualification_status,
                        disqualification_reason=db_lead.disqualification_reason or (app.blocked_reason if app else None),
                        opportunity_score=db_lead.opportunity_score,
                        accessibility_score=db_lead.accessibility_score,
                        outreach_priority_index=db_lead.outreach_priority_index,
                        priority=db_lead.priority_level,
                        evidence_levels=evidence_levels,
                        personalization_status=db_lead.personalization_status,
                        personalization_note=db_lead.personalization_note or "",
                        voc_angle=db_lead.voc_angle or (db_lead.voc.voc_angle if db_lead.voc else "Operational Efficiency"),
                        research_signals=db_lead.personalization_note,
                        email_1=effective_e1,
                        followup_a=effective_fa,
                        followup_b=effective_fb,
                        email_1_original=e1_orig,
                        followup_a_original=fa_orig,
                        followup_b_original=fb_orig,
                        edited_email_1=draft.edited_email_1 if draft else None,
                        edited_followup_a=draft.edited_followup_a if draft else None,
                        edited_followup_b=draft.edited_followup_b if draft else None,
                        qa_status=draft.qa_status if draft else "PASS",
                        qa_reasons=draft.qa_reasons if draft else [],
                        approval_status=app.approval_status if app else "PENDING_REVIEW",
                        reviewer=app.reviewer if app else None,
                        reviewed_at=app.reviewed_at.isoformat() if app and app.reviewed_at else None,
                        smartlead_eligible=app.smartlead_eligible if app else False,
                        blocked_reason=app.blocked_reason if app else None,
                        flag_no_strong_signal=app.flag_no_strong_signal if app else False,
                        metadata=app.metadata_json if app else {},
                    )
        except Exception:
            pass

    # Offline JSON fallback
    store = ApprovalStore()
    record = store.get_record(lead_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found in approval queue.")

    intel_lookup = _load_lead_intel_lookup()
    intel = intel_lookup.get(record.email.lower(), {})

    evidence_levels = {
        "signal": intel.get("relevant_signal_evidence", "VERIFIED" if record.personalization_status == "SIGNAL_VERIFIED" else "UNKNOWN"),
        "company_size": intel.get("company_size_evidence", "ESTIMATED"),
        "pain_point": intel.get("pain_point_evidence", "INFERRED"),
    }

    effective_e1 = record.edited_email_1 or record.email_1_original
    effective_fa = record.edited_followup_a or record.followup_a_original
    effective_fb = record.edited_followup_b or record.followup_b_original

    return LeadDetailResponse(
        lead_id=record.lead_id,
        company=record.company,
        contact=record.contact,
        title=record.title,
        email=record.email,
        email_status=getattr(record, "email_status", record.metadata.get("email_status", "VERIFIED")),
        email_source=getattr(record, "email_source", record.metadata.get("email_source")),
        email_validated=getattr(record, "email_validated", record.metadata.get("email_validated")),
        email_found_and_valid=getattr(record, "email_found_and_valid", record.metadata.get("email_found_and_valid")),
        miss_reason=getattr(record, "miss_reason", record.metadata.get("miss_reason")),
        approval_stage=getattr(record, "approval_stage", "AI_EMAIL_APPROVAL"),
        workflow_status=getattr(record, "workflow_status", "AWAITING_EMAIL_APPROVAL"),
        website=record.metadata.get("website") or intel.get("company_domain"),
        linkedin_url=record.metadata.get("linkedin_url") or intel.get("linkedin_url"),
        qualification_status=record.qualification_status,
        disqualification_reason=record.blocked_reason or intel.get("disqualification_reason"),
        opportunity_score=record.opportunity_score,
        accessibility_score=record.accessibility_score,
        outreach_priority_index=record.outreach_priority_index,
        priority=record.priority,
        evidence_levels=evidence_levels,
        personalization_status=record.personalization_status,
        personalization_note=record.personalization_note,
        voc_angle=record.voc_angle,
        research_signals=intel.get("relevant_signal") or record.personalization_note,
        email_1=effective_e1,
        followup_a=effective_fa,
        followup_b=effective_fb,
        email_1_original=record.email_1_original,
        followup_a_original=record.followup_a_original,
        followup_b_original=record.followup_b_original,
        edited_email_1=record.edited_email_1,
        edited_followup_a=record.edited_followup_a,
        edited_followup_b=record.edited_followup_b,
        qa_status=record.qa_status,
        qa_reasons=record.qa_reasons,
        approval_status=record.approval_status.value,
        reviewer=record.reviewer,
        reviewed_at=record.reviewed_at,
        smartlead_eligible=record.smartlead_eligible,
        blocked_reason=record.blocked_reason,
        flag_no_strong_signal=record.flag_no_strong_signal,
        metadata=record.metadata,
    )
