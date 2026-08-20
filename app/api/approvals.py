"""
approvals.py
FastAPI router for the Human Approval Gate & Safety layer.
Supports Supabase PostgreSQL primary database with offline JSON fallback.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.approval.approval_engine import ApprovalEngine
from src.approval.approval_models import ApprovalRecord, ApprovalStatus
from src.approval.approval_store import ApprovalStore
from src.database.connection import is_database_enabled, get_db_session
from src.database.repositories.approval_repository import ApprovalRepository

router = APIRouter(prefix="/approvals", tags=["Approvals"])


class ApproveRequest(BaseModel):
    reviewer: str = "HUMAN_OPERATOR"


class RejectRequest(BaseModel):
    reviewer: str = "HUMAN_OPERATOR"
    reason: str = "Rejected by human operator"


class BlockRequest(BaseModel):
    reviewer: str = "HUMAN_OPERATOR"
    reason: str = "Blocked manually by operator"


class EditDraftRequest(BaseModel):
    email_1: Optional[str] = None
    followup_a: Optional[str] = None
    followup_b: Optional[str] = None
    touch_3: Optional[str] = None
    touch_4: Optional[str] = None
    touch_5: Optional[str] = None
    reviewer: str = "HUMAN_OPERATOR"


class ApprovalActionResponse(BaseModel):
    ok: bool
    message: str
    record: ApprovalRecord


def _map_db_approval_to_record(app) -> ApprovalRecord:
    lead = app.lead
    draft = lead.email_draft if lead else None
    return ApprovalRecord(
        lead_id=app.lead_id,
        company=lead.company_name if lead else "Unknown",
        contact=lead.contact_name if lead else "Unknown",
        title=lead.job_title if lead else "Decision Maker",
        email=lead.email if lead else "",
        qualification_status=lead.qualification_status if lead else "QUALIFIED",
        opportunity_score=lead.opportunity_score if lead else 0.0,
        accessibility_score=lead.accessibility_score if lead else 0.0,
        outreach_priority_index=lead.outreach_priority_index if lead else 0.0,
        priority=lead.priority_level if lead else "P3",
        personalization_status=lead.personalization_status if lead else "SIGNAL_VERIFIED",
        personalization_note=lead.personalization_note or "",
        voc_angle=lead.voc_angle or "Operational Efficiency",
        email_1_original=draft.ai_original_email_1 if draft else "",
        followup_a_original=draft.ai_original_followup_a if draft else "",
        followup_b_original=draft.ai_original_followup_b if draft else "",
        qa_status=draft.qa_status if draft else "PASS",
        qa_reasons=draft.qa_reasons if draft else [],
        approval_status=ApprovalStatus(app.approval_status),
        reviewer=app.reviewer,
        reviewed_at=app.reviewed_at.isoformat() if app.reviewed_at else None,
        edited_email_1=draft.edited_email_1 if draft else None,
        edited_followup_a=draft.edited_followup_a if draft else None,
        edited_followup_b=draft.edited_followup_b if draft else None,
        smartlead_eligible=app.smartlead_eligible,
        blocked_reason=app.blocked_reason,
        flag_no_strong_signal=app.flag_no_strong_signal,
        campaign_id=lead.campaign_id if lead else "default_campaign",
        icp_id=lead.icp_id if lead else None,
        icp_version=lead.icp_version if lead else "1.0.0",
        metadata=app.metadata_json or {},
    )


@router.get("", response_model=List[ApprovalRecord])
def list_approval_queue(
    status: Optional[str] = Query(None, description="Filter by approval status (PENDING_REVIEW, APPROVED, REJECTED, EDITED, BLOCKED)"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID")
) -> List[ApprovalRecord]:
    """Lists records in the human approval queue isolated by active environment."""
    from src.config.app_mode import ModeService
    from src.demo.demo_data import DEMO_CAMPAIGN_ID

    mode_service = ModeService.get_instance()
    active_mode = mode_service.get_mode().value
    is_demo = mode_service.is_demo()

    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ApprovalRepository(session)
                db_approvals = repo.list_approvals(status=status, campaign_id=campaign_id, environment=active_mode)
                return [_map_db_approval_to_record(a) for a in db_approvals]
        except Exception:
            pass

    store = ApprovalStore()
    all_records = store.list_records(status_filter=status)
    if is_demo:
        demo_recs = [r for r in all_records if r.campaign_id == DEMO_CAMPAIGN_ID or r.lead_id.startswith("demo_")]
        return demo_recs if demo_recs else all_records
    else:
        return [r for r in all_records if r.campaign_id != DEMO_CAMPAIGN_ID and not r.lead_id.startswith("demo_")]


@router.get("/{lead_id}", response_model=ApprovalRecord)
def get_approval_record(lead_id: str) -> ApprovalRecord:
    """Gets a specific approval record by lead_id."""
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ApprovalRepository(session)
                db_app = repo.get_by_lead_id(lead_id)
                if db_app:
                    return _map_db_approval_to_record(db_app)
        except Exception:
            pass

    store = ApprovalStore()
    record = store.get_record(lead_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found in approval queue.")
    return record


@router.post("/{lead_id}/approve", response_model=ApprovalActionResponse)
def approve_lead(lead_id: str, payload: ApproveRequest) -> ApprovalActionResponse:
    """Explicitly marks a lead draft as APPROVED and smartlead_eligible=True."""
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ApprovalRepository(session)
                updated_db = repo.approve_lead(lead_id, reviewer=payload.reviewer)
                record = _map_db_approval_to_record(updated_db)
                return ApprovalActionResponse(
                    ok=True,
                    message=f"Lead '{lead_id}' successfully APPROVED for Smartlead staging.",
                    record=record,
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            pass

    engine = ApprovalEngine()
    try:
        updated = engine.approve(lead_id, reviewer=payload.reviewer)
        return ApprovalActionResponse(
            ok=True,
            message=f"Lead '{lead_id}' successfully APPROVED for Smartlead staging.",
            record=updated,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{lead_id}/reject", response_model=ApprovalActionResponse)
def reject_lead(lead_id: str, payload: RejectRequest) -> ApprovalActionResponse:
    """Rejects a lead draft from outreach."""
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ApprovalRepository(session)
                updated_db = repo.reject_lead(lead_id, reason=payload.reason, reviewer=payload.reviewer)
                record = _map_db_approval_to_record(updated_db)
                return ApprovalActionResponse(
                    ok=True,
                    message=f"Lead '{lead_id}' marked REJECTED.",
                    record=record,
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            pass

    engine = ApprovalEngine()
    try:
        updated = engine.reject(lead_id, reviewer=payload.reviewer, reason=payload.reason)
        return ApprovalActionResponse(
            ok=True,
            message=f"Lead '{lead_id}' marked REJECTED.",
            record=updated,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{lead_id}/edit", response_model=ApprovalActionResponse)
def edit_lead_draft(lead_id: str, payload: EditDraftRequest) -> ApprovalActionResponse:
    """
    Saves edited email copy while preserving immutable original AI drafts.
    Sets status to EDITED and requires explicit subsequent re-approval.
    """
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ApprovalRepository(session)
                updated_db = repo.edit_lead(
                    lead_id,
                    email_1=payload.email_1,
                    followup_a=payload.followup_a,
                    followup_b=payload.followup_b,
                    touch_3=payload.touch_3,
                    touch_4=payload.touch_4,
                    touch_5=payload.touch_5,
                    reviewer=payload.reviewer,
                )
                record = _map_db_approval_to_record(updated_db)
                return ApprovalActionResponse(
                    ok=True,
                    message=f"Lead '{lead_id}' copy updated. Status changed to EDITED (Requires explicit re-approval).",
                    record=record,
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            pass

    engine = ApprovalEngine()
    try:
        updated = engine.edit(
            lead_id,
            email_1=payload.email_1,
            followup_a=payload.followup_a,
            followup_b=payload.followup_b,
            touch_3=payload.touch_3,
            touch_4=payload.touch_4,
            touch_5=payload.touch_5,
            reviewer=payload.reviewer,
        )
        return ApprovalActionResponse(
            ok=True,
            message=f"Lead '{lead_id}' copy updated. Status changed to EDITED (Requires explicit re-approval).",
            record=updated,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{lead_id}/block", response_model=ApprovalActionResponse)
def block_lead(lead_id: str, payload: BlockRequest) -> ApprovalActionResponse:
    """Blocks a lead draft from outreach."""
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ApprovalRepository(session)
                updated_db = repo.block_lead(lead_id, reason=payload.reason, reviewer=payload.reviewer)
                record = _map_db_approval_to_record(updated_db)
                return ApprovalActionResponse(
                    ok=True,
                    message=f"Lead '{lead_id}' marked BLOCKED.",
                    record=record,
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            pass

    engine = ApprovalEngine()
    try:
        updated = engine.block(lead_id, reason=payload.reason, reviewer=payload.reviewer)
        return ApprovalActionResponse(
            ok=True,
            message=f"Lead '{lead_id}' marked BLOCKED.",
            record=updated,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
