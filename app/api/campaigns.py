"""
campaigns.py
FastAPI router for campaign sequence visualization, outreach state machine graph, and Smartlead staging plan.
"""

from typing import Any, Dict, List
from fastapi import APIRouter
from pydantic import BaseModel

from src.models import OutreachState
from src.smartlead_staging_runner import SmartleadStagingRunner

router = APIRouter(tags=["Campaigns & Staging"])


class CampaignStep(BaseModel):
    step_number: int
    name: str
    delay_display: str
    delay_days: int
    description: str
    condition: str


class CampaignFlowResponse(BaseModel):
    name: str
    description: str
    steps: List[CampaignStep]
    event_branches: List[Dict[str, Any]]
    all_states: List[str]


@router.get("/campaign", response_model=CampaignFlowResponse)
def get_campaign_flow() -> CampaignFlowResponse:
    """Returns the visual flow structure and state machine definitions for the campaign visualizer."""
    steps = [
        CampaignStep(
            step_number=1,
            name="Email 1 (Initial Outreach)",
            delay_display="Immediate (Day 0)",
            delay_days=0,
            description="High-relevance, zero-hallucination cold email grounded in verified Deepline research.",
            condition="ICP Qualified & Human Approved"
        ),
        CampaignStep(
            step_number=2,
            name="Behavior Checkpoint (2-Day Wait)",
            delay_display="Wait 2 Days (48h)",
            delay_days=2,
            description="System pauses sequence for exactly 2 days to monitor email open or reply events.",
            condition="Delivered"
        ),
        CampaignStep(
            step_number=3,
            name="Branch A: Opened Follow-up",
            delay_display="+1 Day after open",
            delay_days=1,
            description="Follow-up A referencing the opened context with deeper evidence on pre-construction control.",
            condition="EMAIL_OPENED within 48h"
        ),
        CampaignStep(
            step_number=4,
            name="Branch B: Unopened Follow-up",
            delay_display="After 2 Days timeout",
            delay_days=2,
            description="Follow-up B pivoting angle to real-time site manpower & financial tracking.",
            condition="EMAIL_UNOPENED after 48h"
        )
    ]

    event_branches = [
        {
            "event": "POSITIVE_REPLY",
            "action": "Immediate Slack sales handoff alert (#sales-hot-leads) within 1 hour + Pause outreach",
            "target_state": OutreachState.HANDOFF_HUMAN_SALES.value,
            "badge_color": "emerald"
        },
        {
            "event": "NEGATIVE_REPLY",
            "action": "Mark prospect not interested + Pause sequence",
            "target_state": OutreachState.SUPPRESSED_NOT_INTERESTED.value,
            "badge_color": "amber"
        },
        {
            "event": "EMAIL_BOUNCED",
            "action": "Stop outreach immediately + Mark lead invalid/bounced",
            "target_state": OutreachState.STOPPED_BOUNCED.value,
            "badge_color": "rose"
        },
        {
            "event": "EMAIL_UNSUBSCRIBED",
            "action": "Immediate global opt-out suppression + Pause sequence",
            "target_state": OutreachState.STOPPED_UNSUBSCRIBED.value,
            "badge_color": "rose"
        },
        {
            "event": "OOO (Out of Office)",
            "action": "Log return date + schedule gentle re-check without interrupting sequence",
            "target_state": OutreachState.WAITING_FOLLOWUP_B.value,
            "badge_color": "blue"
        }
    ]

    all_states = [s.value for s in OutreachState]

    return CampaignFlowResponse(
        name="Aedrix UK Construction High-Priority Sequence",
        description="Event-driven outreach pipeline connecting Smartlead webhooks, n8n orchestration, and Claude dynamic follow-ups.",
        steps=steps,
        event_branches=event_branches,
        all_states=all_states
    )


@router.get("/smartlead/staging")
def get_smartlead_staging_plan() -> Dict[str, Any]:
    """Generates and returns the latest Smartlead staging plan (0 real API calls)."""
    runner = SmartleadStagingRunner()
    plan = runner.build_staging_plan()
    return plan
