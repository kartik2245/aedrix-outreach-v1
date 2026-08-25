"""
icp.py
FastAPI router for Dynamic ICP Designer, Human ICP Approval Gate, and Deepline Discovery runs.
Supports Supabase PostgreSQL primary database with offline JSON fallback.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.icp.icp_models import ICPConfig, ICPStatus, DeeplineDiscoveryRequest
from src.icp.icp_designer import ICPDesigner
from src.icp.icp_approval_engine import ICPApprovalEngine
from src.icp.icp_approval_store import ICPApprovalStore
from src.icp.icp_approval_models import ICPApprovalRecord
from src.deepline_discovery_runner import DeeplineDiscoveryRunner
from src.database.connection import is_database_enabled, get_db_session
from src.database.repositories.icp_repository import ICPRepository

router = APIRouter(prefix="/icp", tags=["ICP Designer & Discovery"])


class GenerateICPRequest(BaseModel):
    campaign_name: str
    campaign_objective: str
    product_context: Optional[str] = None
    geography: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    target_personas: Optional[List[str]] = Field(default_factory=list)
    minimum_employees: Optional[int] = 10
    maximum_employees: Optional[int] = None
    minimum_revenue: Optional[float] = None
    maximum_revenue: Optional[float] = None
    positive_signals: Optional[List[str]] = Field(default_factory=list)
    negative_signals: Optional[List[str]] = Field(default_factory=list)
    hard_disqualifiers: Optional[List[str]] = Field(default_factory=list)
    campaign_exclusions: Optional[List[str]] = Field(default_factory=list)
    voc_context: Optional[str] = None
    campaign_id: Optional[str] = None
    product_or_service: Optional[str] = None
    value_proposition: Optional[str] = None
    offer: Optional[str] = None
    cta: Optional[str] = None
    company_name: Optional[str] = None
    sender_name: Optional[str] = None


class CreateManualICPRequest(BaseModel):
    campaign_name: str = Field(..., min_length=2, description="Human readable campaign name")
    campaign_objective: str = Field(..., min_length=5, description="High-level objective and campaign strategy")
    industry: Optional[str] = None
    industries: Optional[List[str]] = None
    geography: Optional[str] = None
    allowed_country_keywords: Optional[List[str]] = None
    minimum_employees: Optional[int] = 10
    maximum_employees: Optional[int] = None
    minimum_revenue: Optional[float] = 10.0
    maximum_revenue: Optional[float] = None
    company_size: Optional[str] = None
    target_personas: Optional[List[str]] = None
    seniority_levels: Optional[List[str]] = None
    technologies: Optional[List[str]] = None
    qualification_rules: Optional[List[str]] = None
    hard_disqualification_rules: Optional[List[str]] = None
    campaign_exclusion_rules: Optional[List[str]] = None
    additional_notes: Optional[str] = None
    voc_context: Optional[str] = None
    campaign_id: Optional[str] = None
    company_name: Optional[str] = None
    product_or_service: Optional[str] = None
    value_proposition: Optional[str] = None
    offer: Optional[str] = None
    cta: Optional[str] = None
    sender_name: Optional[str] = None


class ApproveICPRequest(BaseModel):
    reviewer: str = "HUMAN_OPERATOR"


class RejectICPRequest(BaseModel):
    reason: str = "Rejected by human operator"
    reviewer: str = "HUMAN_OPERATOR"


class EditICPRequest(BaseModel):
    updated_data: Dict[str, Any]
    reviewer: str = "HUMAN_OPERATOR"


class DeeplineRunRequest(BaseModel):
    requested_count: int = Field(default=100, ge=1, le=5000)


def _map_db_icp_to_record(app_obj) -> ICPApprovalRecord:
    from src.icp.icp_models import ICPSource
    source_val = getattr(app_obj, "source", None) or (getattr(app_obj.icp, "source", None) if getattr(app_obj, "icp", None) else None) or "CLAUDE_GENERATED"
    original_claude = None
    if app_obj.original_claude_icp:
        try:
            original_claude = ICPConfig.model_validate(app_obj.original_claude_icp)
        except Exception:
            pass

    return ICPApprovalRecord(
        icp_id=app_obj.icp_id,
        campaign_id=app_obj.icp.campaign_id if app_obj.icp else "default_campaign",
        name=app_obj.icp.name if app_obj.icp else "Untitled ICP",
        version=app_obj.version,
        status=ICPStatus(app_obj.status),
        source=ICPSource(source_val) if source_val in [e.value for e in ICPSource] else ICPSource.CLAUDE_GENERATED,
        original_claude_icp=original_claude,
        effective_icp=ICPConfig.model_validate(app_obj.effective_icp),
        reviewer=app_obj.reviewer,
        reviewed_at=app_obj.reviewed_at.isoformat() if app_obj.reviewed_at else None,
        rejection_reason=app_obj.rejection_reason,
        blocked_reason=app_obj.blocked_reason,
        deepline_eligible=app_obj.deepline_eligible,
        deepline_run_ids=app_obj.deepline_run_ids or [],
        edit_history=app_obj.edit_history or [],
        audit_trail=app_obj.audit_trail or [],
    )


@router.post("/manual")
def create_manual_icp(payload: CreateManualICPRequest):
    """
    Creates an ICPConfig directly from manually supplied criteria.
    Sets source = MANUAL and enrolls in Human Approval Queue as PENDING_REVIEW.
    Never automatically calls Deepline.
    """
    import re
    from datetime import datetime, timezone
    from src.icp.icp_models import (
        ICPConfig,
        ICPStatus,
        ICPSource,
        GeographyConfig,
        HardDisqualificationRule,
        CampaignExclusionRule,
        ScoringWeights,
    )
    from src.config.app_mode import ModeService

    mode_service = ModeService.get_instance()
    active_mode = mode_service.get_mode().value

    # 1. Derive Campaign ID & ICP ID
    clean_name = re.sub(r'[^a-zA-Z0-9_]+', '_', payload.campaign_name.strip().lower()).strip('_')
    timestamp_suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    campaign_id = payload.campaign_id or f"campaign_{clean_name}_{timestamp_suffix}"
    icp_id = f"icp_{clean_name}_{timestamp_suffix}"

    # 2. Geography Configuration
    geo_country = (payload.geography or "United Kingdom").strip()
    if payload.allowed_country_keywords:
        geo_keywords = payload.allowed_country_keywords
    else:
        geo_keywords = []
        for term in re.split(r'[\n,;]+', geo_country):
            clean_t = term.strip().upper()
            if clean_t and clean_t not in geo_keywords:
                geo_keywords.append(clean_t)
        if not geo_keywords:
            geo_keywords = [geo_country.upper()]

    geography_cfg = GeographyConfig(
        primary_country=geo_country,
        country_codes=[geo_keywords[0][:3].upper()] if geo_keywords else [geo_country[:3].upper()],
        allowed_country_keywords=geo_keywords,
        require_target_country_operating=True,
    )

    # 3. Industries & Personas
    ind_list = payload.industries or [ind.strip() for ind in (payload.industry or "Technology").split(",") if ind.strip()]
    if not ind_list:
        ind_list = ["Technology", "Software", "Services"]
    allowed_ind_keywords = [i.upper() for i in ind_list]

    personas = payload.target_personas or ["Founder", "CEO", "Chief Technology Officer", "Head of Technology", "Director"]
    persona_keywords = [p.upper() for p in personas]

    # 4. Company Size description
    size_desc = payload.company_size
    if not size_desc:
        size_parts = []
        if payload.minimum_employees:
            if payload.maximum_employees:
                size_parts.append(f"{payload.minimum_employees}-{payload.maximum_employees} employees")
            else:
                size_parts.append(f"{payload.minimum_employees}+ employees")
        if payload.minimum_revenue:
            if payload.maximum_revenue:
                size_parts.append(f"£{payload.minimum_revenue}M-£{payload.maximum_revenue}M revenue")
            else:
                size_parts.append(f"£{payload.minimum_revenue}M+ revenue")
        size_desc = " or ".join(size_parts) if size_parts else "10+ employees"

    # 5. Qualification / Positive Signals
    pos_signals = payload.qualification_rules or [
        f"Operating in target geography: {geo_country}",
        f"Operating in target industry: {', '.join(ind_list)}",
        "Target decision maker persona match",
    ]

    # 6. Hard Disqualification Rules
    hard_disqualifiers: List[HardDisqualificationRule] = []
    if payload.hard_disqualification_rules:
        for idx, rule in enumerate(payload.hard_disqualification_rules):
            hard_disqualifiers.append(
                HardDisqualificationRule(
                    code=f"HD_MANUAL_{idx+1}",
                    description=rule,
                    field="geography" if any(k in rule.lower() for k in ["geography", "country", "location"]) else "industry" if any(k in rule.lower() for k in ["industry", "sector"]) else "company_size",
                )
            )
    else:
        hard_disqualifiers = [
            HardDisqualificationRule(code="HD_NON_TARGET_GEO", description=f"Operating exclusively outside {geo_country}", field="geography"),
            HardDisqualificationRule(code="HD_NON_TARGET_INDUSTRY", description=f"Non-target industry sector outside {', '.join(ind_list)}", field="industry"),
            HardDisqualificationRule(code="HD_BELOW_SIZE_THRESHOLD", description=f"Company size below {size_desc}", field="company_size"),
        ]

    # 7. Campaign Exclusion Rules
    campaign_exclusions: List[CampaignExclusionRule] = []
    if payload.campaign_exclusion_rules:
        for idx, rule in enumerate(payload.campaign_exclusion_rules):
            campaign_exclusions.append(
                CampaignExclusionRule(
                    code=f"EX_MANUAL_{idx+1}",
                    description=rule,
                    fields=["crm_status"] if "crm" in rule.lower() else ["opt_out"] if "opt" in rule.lower() else ["contact_history"],
                )
            )
    else:
        campaign_exclusions = [
            CampaignExclusionRule(code="EX_ACTIVE_CRM_DEAL", description="Active deal in CRM pipeline", fields=["crm_status"]),
            CampaignExclusionRule(code="EX_GLOBAL_OPT_OUT", description="Global email suppression or opt-out match", fields=["opt_out"]),
            CampaignExclusionRule(code="EX_RECENT_OUTREACH", description="Contacted by sales team within past 60 days", fields=["contact_history"]),
            CampaignExclusionRule(code="EX_INVALID_EMAIL", description="Invalid, unverified, or bounced email address", fields=["email_status"]),
        ]

    # 8. Construct ICPConfig
    icp = ICPConfig(
        id=icp_id,
        campaign_id=campaign_id,
        name=payload.campaign_name.strip(),
        version="1.0.0",
        campaign_description=payload.campaign_objective.strip(),
        geography=geography_cfg,
        industries=ind_list,
        allowed_industry_keywords=allowed_ind_keywords,
        disallowed_industry_keywords=[],
        company_size=size_desc,
        minimum_employees=payload.minimum_employees or 10,
        maximum_employees=payload.maximum_employees,
        minimum_revenue=payload.minimum_revenue or 0.0,
        maximum_revenue=payload.maximum_revenue,
        target_personas=personas,
        persona_title_keywords=persona_keywords,
        positive_signals=pos_signals,
        negative_signals=["Out of scope business model", "Under minimum employee threshold"],
        hard_disqualifiers=hard_disqualifiers,
        campaign_exclusions=campaign_exclusions,
        required_conditions=[f"Operating in {geo_country}", f"Meets {size_desc}"],
        preferred_conditions=["Active growth initiatives", "Identifiable decision maker"],
        scoring_weights=ScoringWeights(),
        source_context=payload.additional_notes or "Manually created ICP via operator interface.",
        voc_context=payload.voc_context or "Target audience operational challenges and growth requirements.",
        reasoning="Manually configured by operator.",
        status=ICPStatus.PENDING_REVIEW,
        source=ICPSource.MANUAL,
        company_name=payload.company_name,
        product_or_service=payload.product_or_service,
        value_proposition=payload.value_proposition,
        offer=payload.offer,
        cta=payload.cta,
        sender_name=payload.sender_name,
    )

    # 9. Enroll in PostgreSQL or fallback store
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ICPRepository(session)
                db_app = repo.enroll_icp(icp, environment=active_mode, source="MANUAL")
                record = _map_db_icp_to_record(db_app)
                return {
                    "ok": True,
                    "message": f"Manual ICP '{icp.id}' created successfully and enrolled for review.",
                    "icp_id": icp.id,
                    "campaign_id": icp.campaign_id,
                    "status": record.status.value,
                    "source": record.source.value,
                    "icp": icp,
                    "record": record,
                }
        except Exception:
            pass

    engine = ICPApprovalEngine()
    record = engine.enroll_icp(icp, source="MANUAL")

    return {
        "ok": True,
        "message": f"Manual ICP '{icp.id}' created successfully and enrolled for review.",
        "icp_id": icp.id,
        "campaign_id": icp.campaign_id,
        "status": record.status.value,
        "source": record.source.value,
        "icp": icp,
        "record": record,
    }


@router.post("/generate")
def generate_icp(payload: GenerateICPRequest):
    """
    Translates natural-language campaign requirements into a structured ICPConfig.
    Enrolls the output in the Human Approval Queue as PENDING_REVIEW.
    """
    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name=payload.campaign_name,
        campaign_objective=payload.campaign_objective,
        product_context=payload.product_context or "",
        geography=payload.geography,
        industry=payload.industry,
        company_size=payload.company_size,
        target_personas=payload.target_personas,
        minimum_employees=payload.minimum_employees,
        maximum_employees=payload.maximum_employees,
        minimum_revenue=payload.minimum_revenue,
        maximum_revenue=payload.maximum_revenue,
        positive_signals=payload.positive_signals,
        negative_signals=payload.negative_signals,
        hard_disqualifiers=payload.hard_disqualifiers,
        campaign_exclusions=payload.campaign_exclusions,
        voc_context=payload.voc_context,
        campaign_id=payload.campaign_id,
        company_name=payload.company_name,
        product_or_service=payload.product_or_service,
        value_proposition=payload.value_proposition,
        offer=payload.offer,
        cta=payload.cta,
        sender_name=payload.sender_name,
    )

    from src.config.app_mode import ModeService
    from src.demo.demo_data import DEMO_CAMPAIGN_ID, DEMO_ICP_ID

    mode_service = ModeService.get_instance()
    active_mode = mode_service.get_mode().value
    is_demo = mode_service.is_demo()

    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ICPRepository(session)
                db_app = repo.enroll_icp(icp, environment=active_mode, source="CLAUDE_GENERATED")
                record = _map_db_icp_to_record(db_app)
                return {
                    "ok": True,
                    "message": f"ICP '{icp.id}' generated successfully and enrolled for review.",
                    "icp_id": icp.id,
                    "campaign_id": icp.campaign_id,
                    "status": record.status.value,
                    "source": record.source.value,
                    "icp": icp,
                    "record": record,
                }
        except Exception:
            pass

    engine = ICPApprovalEngine()
    record = engine.enroll_icp(icp, source="CLAUDE_GENERATED")

    return {
        "ok": True,
        "message": f"ICP '{icp.id}' generated successfully and enrolled for review.",
        "icp_id": icp.id,
        "campaign_id": icp.campaign_id,
        "status": record.status.value,
        "source": record.source.value,
        "icp": icp,
        "record": record,
    }


@router.get("", response_model=List[ICPApprovalRecord])
def list_icps(
    status: Optional[str] = Query(None, description="Filter by status (PENDING_REVIEW, APPROVED, EDITED, REJECTED, BLOCKED)"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID")
) -> List[ICPApprovalRecord]:
    """Lists all ICP configurations isolated by active environment."""
    from src.config.app_mode import ModeService
    from src.demo.demo_data import DEMO_CAMPAIGN_ID, DEMO_ICP_ID

    mode_service = ModeService.get_instance()
    active_mode = mode_service.get_mode().value
    is_demo = mode_service.is_demo()

    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ICPRepository(session)
                db_apps = repo.list_approvals(status=status, campaign_id=campaign_id, environment=active_mode)
                return [_map_db_icp_to_record(a) for a in db_apps]
        except Exception:
            pass

    store = ICPApprovalStore()
    all_records = store.list_records(status_filter=status, campaign_id=campaign_id)
    if is_demo:
        demo_recs = [r for r in all_records if r.campaign_id == DEMO_CAMPAIGN_ID or r.icp_id == DEMO_ICP_ID or r.icp_id.startswith("demo_")]
        return demo_recs if demo_recs else all_records
    else:
        return [r for r in all_records if r.campaign_id != DEMO_CAMPAIGN_ID and r.icp_id != DEMO_ICP_ID and not r.icp_id.startswith("demo_")]


@router.get("/{icp_id}", response_model=ICPApprovalRecord)
def get_icp_record(icp_id: str) -> ICPApprovalRecord:
    """Retrieves a single ICP approval record including original copy and audit history."""
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ICPRepository(session)
                db_app = repo.get_approval_record(icp_id)
                if db_app:
                    return _map_db_icp_to_record(db_app)
        except Exception:
            pass

    store = ICPApprovalStore()
    record = store.get_record(icp_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"ICP '{icp_id}' not found.")
    return record


@router.post("/{icp_id}/approve", response_model=ICPApprovalRecord)
def approve_icp(icp_id: str, payload: ApproveICPRequest) -> ICPApprovalRecord:
    """Approves an ICP configuration, marking it eligible for Deepline lead discovery."""
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ICPRepository(session)
                updated_db = repo.approve_icp(icp_id, reviewer=payload.reviewer)
                return _map_db_icp_to_record(updated_db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            pass

    engine = ICPApprovalEngine()
    try:
        return engine.approve_icp(icp_id, reviewer=payload.reviewer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{icp_id}/reject", response_model=ICPApprovalRecord)
def reject_icp(icp_id: str, payload: RejectICPRequest) -> ICPApprovalRecord:
    """Rejects an ICP configuration."""
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ICPRepository(session)
                updated_db = repo.reject_icp(icp_id, reason=payload.reason, reviewer=payload.reviewer)
                return _map_db_icp_to_record(updated_db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            pass

    engine = ICPApprovalEngine()
    try:
        return engine.reject_icp(icp_id, reason=payload.reason, reviewer=payload.reviewer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{icp_id}", response_model=ICPApprovalRecord)
def edit_icp(icp_id: str, payload: EditICPRequest) -> ICPApprovalRecord:
    """
    Edits an ICP configuration.
    Preserves original Claude copy, invalidates prior approval, and resets status to EDITED.
    """
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ICPRepository(session)
                updated_db = repo.edit_icp(icp_id, updated_data=payload.updated_data, reviewer=payload.reviewer)
                return _map_db_icp_to_record(updated_db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            pass

    engine = ICPApprovalEngine()
    try:
        return engine.edit_icp(icp_id, updated_data=payload.updated_data, reviewer=payload.reviewer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{icp_id}/deepline-preview")
def preview_deepline_discovery(icp_id: str, payload: DeeplineRunRequest):
    """Generates the Deepline discovery specification without executing network discovery."""
    record = None
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ICPRepository(session)
                db_app = repo.get_approval_record(icp_id)
                if db_app:
                    record = _map_db_icp_to_record(db_app)
        except Exception:
            pass

    if not record:
        store = ICPApprovalStore()
        record = store.get_record(icp_id)

    if not record:
        raise HTTPException(status_code=404, detail=f"ICP '{icp_id}' not found.")

    icp = record.effective_icp
    req = DeeplineDiscoveryRequest(
        icp_id=icp.id,
        campaign_id=icp.campaign_id,
        campaign_name=icp.name,
        geography=icp.geography.allowed_country_keywords,
        industries=icp.industries,
        company_size=icp.company_size,
        personas=icp.target_personas,
        positive_signals=icp.positive_signals,
        exclusions=[c.description for c in icp.campaign_exclusions],
        requested_lead_count=payload.requested_count,
        batch_size=400,
    )

    return {
        "icp_id": icp.id,
        "campaign_id": icp.campaign_id,
        "approval_status": record.status.value,
        "deepline_eligible": record.deepline_eligible,
        "discovery_request": req,
        "estimated_batches": max(1, (payload.requested_count + 399) // 400),
        "safety_mode": "PREVIEW_ONLY (Zero API credits consumed)",
    }


@router.post("/{icp_id}/deepline-run")
def execute_deepline_discovery(icp_id: str, payload: DeeplineRunRequest):
    """
    Executes Deepline discovery and passes discovered leads through the intelligence, scoring, and personalization pipeline.
    Requires ICP to be in APPROVED status.
    """
    record = None
    if is_database_enabled():
        try:
            with get_db_session() as session:
                repo = ICPRepository(session)
                db_app = repo.get_approval_record(icp_id)
                if db_app:
                    record = _map_db_icp_to_record(db_app)
        except Exception:
            pass

    if not record:
        store = ICPApprovalStore()
        record = store.get_record(icp_id)

    if not record:
        raise HTTPException(status_code=404, detail=f"ICP '{icp_id}' not found.")

    if record.status != ICPStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute Deepline discovery on unapproved ICP '{icp_id}'. Current status is '{record.status.value}'. Please approve the ICP first.",
        )

    runner = DeeplineDiscoveryRunner()
    try:
        result = runner.run_discovery_pipeline(
            icp=record.effective_icp,
            requested_count=payload.requested_count,
        )
        return {
            "ok": True,
            "message": f"Deepline discovery pipeline executed for {payload.requested_count} leads.",
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
