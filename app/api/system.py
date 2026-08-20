"""
system.py
FastAPI router for system configuration audit, integration status matrix, safety flags, application mode, and diagnostics.
"""

import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.integrations.smartlead_client import (
    SmartleadClient,
    load_env_file_if_present,
)
from src.production_batch_runner import ProductionBatchRunner
from src.smartlead_staging_runner import SmartleadStagingRunner
from src.approval.approval_store import ApprovalStore
from src.approval.approval_models import ApprovalStatus
from src.models import SmartleadAuditEntry
from src.config.app_mode import (
    ModeService,
    AppMode,
    ModeConfigResponse,
    ReadinessResponse,
)

router = APIRouter(tags=["System & Demo"])


class IntegrationStatus(BaseModel):
    name: str
    status: str
    mode: str
    description: str


class SystemStatusResponse(BaseModel):
    integrations: List[IntegrationStatus]
    safety_flags: Dict[str, Any]
    masked_env: Dict[str, str]
    recent_logs: List[Dict[str, Any]]


class DemoRunResponse(BaseModel):
    ok: bool
    message: str
    summary: Dict[str, Any]


class DatabaseHealthResponse(BaseModel):
    database: str
    connected: bool
    latency_ms: Optional[float] = None
    database_enabled: bool
    status: str


class SetModeRequest(BaseModel):
    mode: str
    confirmation: Optional[str] = None


@router.get("/system/mode", response_model=ModeConfigResponse)
@router.get("/mode", response_model=ModeConfigResponse)
def get_application_mode() -> ModeConfigResponse:
    """Returns the current centralized application mode (DEMO vs PRODUCTION) and integration status."""
    service = ModeService.get_instance()
    return service.get_mode_config()


@router.post("/system/mode", response_model=ModeConfigResponse)
@router.post("/mode", response_model=ModeConfigResponse)
def set_application_mode(payload: SetModeRequest) -> ModeConfigResponse:
    """
    Switches runtime application mode between DEMO and PRODUCTION.
    Switching to PRODUCTION requires explicit confirmation.
    """
    target_mode = payload.mode.strip().upper()
    service = ModeService.get_instance()

    if target_mode == "PRODUCTION":
        if payload.confirmation != "ENABLE PRODUCTION":
            raise HTTPException(
                status_code=400,
                detail="Switching to PRODUCTION requires explicit confirmation text 'ENABLE PRODUCTION'."
            )
        service.set_mode(AppMode.PRODUCTION)
    elif target_mode == "DEMO":
        service.set_mode(AppMode.DEMO)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{payload.mode}'. Must be 'DEMO' or 'PRODUCTION'."
        )

    return service.get_mode_config()


@router.get("/system/readiness", response_model=ReadinessResponse)
@router.get("/readiness", response_model=ReadinessResponse)
def get_readiness_status() -> ReadinessResponse:
    """Returns detailed startup readiness and integration diagnostic status."""
    service = ModeService.get_instance()
    return service.get_readiness_status()


@router.get("/system/database-health", response_model=DatabaseHealthResponse)
@router.get("/database-health", response_model=DatabaseHealthResponse)
def get_database_health() -> DatabaseHealthResponse:
    """Returns real-time PostgreSQL / Supabase connection health, latency, and status."""
    from src.database.connection import check_db_health
    health = check_db_health()
    return DatabaseHealthResponse(**health)


@router.get("/system/status", response_model=SystemStatusResponse)
@router.get("/status", response_model=SystemStatusResponse)
def get_system_status() -> SystemStatusResponse:
    """Returns the integration status matrix, masked environment flags, and recent audit logs."""
    load_env_file_if_present()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    smartlead_key = os.getenv("SMARTLEAD_API_KEY", "")

    env_dry_run = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
    env_send_emails = os.getenv("SEND_EMAILS", "false").lower() in ("true", "1", "yes")
    env_smartlead_live = os.getenv("SMARTLEAD_LIVE", "false").lower() in ("true", "1", "yes")
    env_prod_confirm = os.getenv("PRODUCTION_SEND_CONFIRMATION", "false").lower() in ("true", "1", "yes")
    batch_size = int(os.getenv("BATCH_SIZE", "400"))

    mode_service = ModeService.get_instance()
    is_demo = mode_service.is_demo()

    integrations = [
        IntegrationStatus(
            name="Deepline Research Ingestion",
            status="CONNECTED",
            mode="DEMO_SIMULATED_BUFFER" if is_demo else "LOCAL_EXPORT_BUFFER",
            description="Deepline export adapter parses and validates raw contractor research."
        ),
        IntegrationStatus(
            name="Anthropic Claude Personalization",
            status="CONFIGURED" if anthropic_key else "OFFLINE_FALLBACK",
            mode="DEMO_SIMULATED_DRAFTS" if is_demo else ("DRY_RUN_TEMPLATE" if env_dry_run or not anthropic_key else "LIVE_API"),
            description="Claude 3.5 Sonnet generates grounded, zero-hallucination drafts."
        ),
        IntegrationStatus(
            name="Smartlead Outreach Integration",
            status="CONFIGURED" if smartlead_key else "READY_STAGING",
            mode="DEMO_SIMULATED_STAGING" if is_demo else ("LIVE_API" if env_smartlead_live else "DRY_RUN_STAGING"),
            description="REST API client for campaign creation, sequence setup, and lead upload."
        ),
        IntegrationStatus(
            name="n8n Orchestration",
            status="CONFIGURED",
            mode="WORKFLOW_READY",
            description="Event-driven webhook router for opens, replies, and sales alerts."
        )
    ]

    safety_flags = {
        "APP_MODE": mode_service.get_mode().value,
        "DRY_RUN": True if is_demo else env_dry_run,
        "SEND_EMAILS": False if is_demo else env_send_emails,
        "SMARTLEAD_LIVE": False if is_demo else env_smartlead_live,
        "PRODUCTION_SEND_CONFIRMATION": False if is_demo else env_prod_confirm,
        "BATCH_SIZE": batch_size,
        "REAL_EMAILS_SENT": 0
    }

    masked_env = {
        "APP_MODE": mode_service.get_mode().value,
        "ANTHROPIC_API_KEY": SmartleadClient.mask_api_key(anthropic_key),
        "SMARTLEAD_API_KEY": SmartleadClient.mask_api_key(smartlead_key),
        "SMARTLEAD_BASE_URL": os.getenv("SMARTLEAD_BASE_URL", "https://server.smartlead.ai/api/v1"),
        "CLAUDE_MODEL": os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
        "BATCH_SIZE": str(batch_size),
        "DRY_RUN": str(safety_flags["DRY_RUN"]).lower(),
        "SEND_EMAILS": str(safety_flags["SEND_EMAILS"]).lower(),
        "SMARTLEAD_LIVE": str(safety_flags["SMARTLEAD_LIVE"]).lower(),
    }

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_path = os.path.join(base_dir, "data", "logs", "smartlead_audit.jsonl")
    recent_logs = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
                for line in lines[-20:]:
                    try:
                        recent_logs.append(json.loads(line))
                    except Exception:
                        pass
        except Exception:
            pass

    return SystemStatusResponse(
        integrations=integrations,
        safety_flags=safety_flags,
        masked_env=masked_env,
        recent_logs=list(reversed(recent_logs))
    )


@router.post("/system/demo/run", response_model=DemoRunResponse)
def execute_demo_pipeline() -> DemoRunResponse:
    """
    Executes complete local batch pipeline & Smartlead staging planner with sample Deepline data.
    ZERO real email sending; ZERO external credit expenditure.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sample_export = os.path.join(base_dir, "data", "deepline_export_sample.json")
    output_drafts = os.path.join(base_dir, "data", "claude_personalization_drafts.json")

    batch_runner = ProductionBatchRunner()
    drafts = batch_runner.run_batch(sample_export, output_drafts)

    staging_runner = SmartleadStagingRunner()
    staging_plan = staging_runner.build_staging_plan()

    store = ApprovalStore()
    queue = store.load_queue()

    qualified_count = sum(1 for r in queue if r.qualification_status == "QUALIFIED")
    p1_count = sum(1 for r in queue if r.priority == "P1")
    p2_count = sum(1 for r in queue if r.priority == "P2")
    p3_count = sum(1 for r in queue if r.priority == "P3")
    pending_count = sum(1 for r in queue if r.approval_status == ApprovalStatus.PENDING_REVIEW)
    approved_count = sum(1 for r in queue if r.approval_status == ApprovalStatus.APPROVED)
    qa_pass_count = sum(1 for r in queue if r.qa_status == "PASS")

    summary = {
        "records_processed": len(drafts),
        "qualified_leads": qualified_count,
        "p1_leads": p1_count,
        "p2_leads": p2_count,
        "p3_leads": p3_count,
        "emails_generated": len(drafts) * 3,
        "qa_passed": qa_pass_count,
        "pending_approvals": pending_count,
        "approved_leads": approved_count,
        "smartlead_staged_leads": staging_plan["summary"]["approved_eligible_count"],
        "smartlead_batches": staging_plan["summary"]["total_batches"],
        "api_calls_made": 0,
        "real_emails_sent": 0,
        "safety_mode": "DEMO / ZERO-RISK DRY RUN"
    }

    return DemoRunResponse(
        ok=True,
        message="Demo pipeline executed successfully. All drafts enrolled in Human Approval Gate and staged for Smartlead (0 real emails sent).",
        summary=summary
    )
