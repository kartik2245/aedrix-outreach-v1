"""
dashboard.py
FastAPI router for aggregated dashboard metrics, funnel analytics, and safety indicators.
Supports Supabase PostgreSQL primary database with offline JSON fallback and strict environment isolation (DEMO vs PRODUCTION).
"""

import os
from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from src.approval.approval_models import ApprovalStatus
from src.approval.approval_store import ApprovalStore
from src.database.connection import is_database_enabled, get_db_session
from src.database.models import Lead, EmailApproval, EmailDraft
from src.integrations.smartlead_client import load_env_file_if_present
from src.config.app_mode import ModeService, AppMode
from src.demo.demo_data import DEMO_CAMPAIGN_ID

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class SafetyIndicators(BaseModel):
    dry_run: bool
    send_emails: bool
    smartlead_live: bool
    production_send_confirmation: bool
    mode_display: str
    real_emails_sent: int


class DashboardStatsResponse(BaseModel):
    total_leads: int
    qualified_leads: int
    p1_leads: int
    p2_leads: int
    p3_leads: int
    pending_approvals: int
    approved_leads: int
    rejected_leads: int
    edited_leads: int
    blocked_leads: int
    smartlead_eligible_leads: int
    emails_generated: int
    qa_passed: int
    qa_failed: int
    safety: SafetyIndicators


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats() -> DashboardStatsResponse:
    """Returns aggregated outreach stats, approval funnel counts, and live safety indicators isolated by active environment."""
    load_env_file_if_present()

    mode_service = ModeService.get_instance()
    active_mode = mode_service.get_mode().value  # "DEMO" or "PRODUCTION"
    is_demo = mode_service.is_demo()

    env_dry_run = True if is_demo else os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
    env_send_emails = False if is_demo else os.getenv("SEND_EMAILS", "false").lower() in ("true", "1", "yes")
    env_smartlead_live = False if is_demo else os.getenv("SMARTLEAD_LIVE", "false").lower() in ("true", "1", "yes")
    env_prod_confirm = False if is_demo else os.getenv("PRODUCTION_SEND_CONFIRMATION", "false").lower() in ("true", "1", "yes")

    mode_display = "DEMO / DRY RUN" if is_demo else ("PRODUCTION ACTIVE" if (env_send_emails and env_prod_confirm) else "PRODUCTION (GUARDED)")

    if is_database_enabled():
        try:
            with get_db_session() as session:
                # Query leads for active environment
                total_leads = session.scalar(
                    select(func.count(Lead.id)).where(Lead.environment == active_mode)
                ) or 0

                qualified = session.scalar(
                    select(func.count(Lead.id)).where(
                        Lead.environment == active_mode,
                        Lead.qualification_status == "QUALIFIED"
                    )
                ) or 0

                p1 = session.scalar(
                    select(func.count(Lead.id)).where(
                        Lead.environment == active_mode,
                        Lead.priority_level == "P1"
                    )
                ) or 0

                p2 = session.scalar(
                    select(func.count(Lead.id)).where(
                        Lead.environment == active_mode,
                        Lead.priority_level == "P2"
                    )
                ) or 0

                p3 = session.scalar(
                    select(func.count(Lead.id)).where(
                        Lead.environment == active_mode,
                        Lead.priority_level == "P3"
                    )
                ) or 0

                # Query approvals joined on Lead for active environment
                pending = session.scalar(
                    select(func.count(EmailApproval.id))
                    .join(Lead, EmailApproval.lead_id == Lead.id)
                    .where(
                        Lead.environment == active_mode,
                        EmailApproval.approval_status == ApprovalStatus.PENDING_REVIEW.value
                    )
                ) or 0

                approved = session.scalar(
                    select(func.count(EmailApproval.id))
                    .join(Lead, EmailApproval.lead_id == Lead.id)
                    .where(
                        Lead.environment == active_mode,
                        EmailApproval.approval_status == ApprovalStatus.APPROVED.value
                    )
                ) or 0

                rejected = session.scalar(
                    select(func.count(EmailApproval.id))
                    .join(Lead, EmailApproval.lead_id == Lead.id)
                    .where(
                        Lead.environment == active_mode,
                        EmailApproval.approval_status == ApprovalStatus.REJECTED.value
                    )
                ) or 0

                edited = session.scalar(
                    select(func.count(EmailApproval.id))
                    .join(Lead, EmailApproval.lead_id == Lead.id)
                    .where(
                        Lead.environment == active_mode,
                        EmailApproval.approval_status == ApprovalStatus.EDITED.value
                    )
                ) or 0

                blocked = session.scalar(
                    select(func.count(EmailApproval.id))
                    .join(Lead, EmailApproval.lead_id == Lead.id)
                    .where(
                        Lead.environment == active_mode,
                        EmailApproval.approval_status == ApprovalStatus.BLOCKED.value
                    )
                ) or 0

                eligible = session.scalar(
                    select(func.count(EmailApproval.id))
                    .join(Lead, EmailApproval.lead_id == Lead.id)
                    .where(
                        Lead.environment == active_mode,
                        EmailApproval.smartlead_eligible.is_(True)
                    )
                ) or 0

                # Query drafts joined on Lead for active environment
                qa_passed = session.scalar(
                    select(func.count(EmailDraft.id))
                    .join(Lead, EmailDraft.lead_id == Lead.id)
                    .where(
                        Lead.environment == active_mode,
                        EmailDraft.qa_status == "PASS"
                    )
                ) or 0

                qa_failed = session.scalar(
                    select(func.count(EmailDraft.id))
                    .join(Lead, EmailDraft.lead_id == Lead.id)
                    .where(
                        Lead.environment == active_mode,
                        EmailDraft.qa_status == "FAIL"
                    )
                ) or 0

                generated_emails = (session.scalar(
                    select(func.count(EmailDraft.id))
                    .join(Lead, EmailDraft.lead_id == Lead.id)
                    .where(Lead.environment == active_mode)
                ) or 0) * 3

                return DashboardStatsResponse(
                    total_leads=total_leads,
                    qualified_leads=qualified,
                    p1_leads=p1,
                    p2_leads=p2,
                    p3_leads=p3,
                    pending_approvals=pending,
                    approved_leads=approved,
                    rejected_leads=rejected,
                    edited_leads=edited,
                    blocked_leads=blocked,
                    smartlead_eligible_leads=eligible,
                    emails_generated=generated_emails,
                    qa_passed=qa_passed,
                    qa_failed=qa_failed,
                    safety=SafetyIndicators(
                        dry_run=env_dry_run,
                        send_emails=env_send_emails,
                        smartlead_live=env_smartlead_live,
                        production_send_confirmation=env_prod_confirm,
                        mode_display=mode_display,
                        real_emails_sent=0,
                    ),
                )
        except Exception:
            pass

    # Fallback to local ApprovalStore
    store = ApprovalStore()
    all_records = store.load_queue()

    if is_demo:
        demo_recs = [r for r in all_records if r.campaign_id == DEMO_CAMPAIGN_ID or r.lead_id.startswith("demo_")]
        records = demo_recs if demo_recs else all_records
    else:
        records = [r for r in all_records if r.campaign_id != DEMO_CAMPAIGN_ID and not r.lead_id.startswith("demo_")]

    total_leads = len(records)
    qualified = sum(1 for r in records if r.qualification_status == "QUALIFIED")
    p1 = sum(1 for r in records if r.priority == "P1")
    p2 = sum(1 for r in records if r.priority == "P2")
    p3 = sum(1 for r in records if r.priority == "P3")

    pending = sum(1 for r in records if r.approval_status == ApprovalStatus.PENDING_REVIEW)
    approved = sum(1 for r in records if r.approval_status == ApprovalStatus.APPROVED)
    rejected = sum(1 for r in records if r.approval_status == ApprovalStatus.REJECTED)
    edited = sum(1 for r in records if r.approval_status == ApprovalStatus.EDITED)
    blocked = sum(1 for r in records if r.approval_status == ApprovalStatus.BLOCKED)
    eligible = sum(1 for r in records if r.smartlead_eligible is True)

    generated_emails = sum(
        3 for r in records if r.qualification_status == "QUALIFIED" and r.email_1_original and not r.email_1_original.startswith("[SKIPPED]")
    )

    qa_passed = sum(1 for r in records if r.qa_status == "PASS")
    qa_failed = sum(1 for r in records if r.qa_status == "FAIL")

    return DashboardStatsResponse(
        total_leads=total_leads,
        qualified_leads=qualified,
        p1_leads=p1,
        p2_leads=p2,
        p3_leads=p3,
        pending_approvals=pending,
        approved_leads=approved,
        rejected_leads=rejected,
        edited_leads=edited,
        blocked_leads=blocked,
        smartlead_eligible_leads=eligible,
        emails_generated=generated_emails,
        qa_passed=qa_passed,
        qa_failed=qa_failed,
        safety=SafetyIndicators(
            dry_run=env_dry_run,
            send_emails=env_send_emails,
            smartlead_live=env_smartlead_live,
            production_send_confirmation=env_prod_confirm,
            mode_display=mode_display,
            real_emails_sent=0,
        ),
    )
