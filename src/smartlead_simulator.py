"""
smartlead_simulator.py
Builds official Smartlead API payloads and simulates campaign execution in DRAFT/TEST mode (Python 3.12).
Zero real email sending; zero credit expenditure.
"""

import random
from typing import Dict, Any, Union
from src.models import LeadIntelligenceOutput, EmailGenerationResult, SmartleadPayload


class SmartleadSimulator:
    def __init__(self, campaign_id: int = 123456):
        self.campaign_id = campaign_id
        self.enrolled_leads = {}

    def build_lead_enrollment_payload(self, lead: LeadIntelligenceOutput, email_1: EmailGenerationResult) -> SmartleadPayload:
        """Builds official Smartlead API payload for POST /api/v1/campaigns/{campaign_id}/leads."""
        names = lead.contact_name.split(" ")
        first_name = names[0]
        last_name = " ".join(names[1:]) if len(names) > 1 else ""
        mock_lead_id = f"sl_lead_{random.randint(10000, 99999)}"

        return SmartleadPayload(
            api_endpoint=f"POST /api/v1/campaigns/{self.campaign_id}/leads",
            headers={
                "Content-Type": "application/json",
                "api_key": "YOUR_SMARTLEAD_API_KEY_PLACEHOLDER"
            },
            payload={
                "email": lead.email,
                "first_name": first_name,
                "last_name": last_name,
                "company_name": lead.company_name,
                "website": lead.company_domain,
                "linkedin_profile": lead.linkedin_url,
                "custom_fields": {
                    "job_title": lead.job_title,
                    "company_size": lead.company_size,
                    "icp_score": lead.ICP_score,
                    "personalization_note": lead.personalization_note,
                    "email_1_subject": email_1.subject,
                    "email_1_body": email_1.body
                }
            },
            campaign_status="DRAFT_PAUSED_TEST",
            mock_response={
                "ok": True,
                "status": "success",
                "lead_id": mock_lead_id,
                "campaign_id": self.campaign_id,
                "message": "Lead registered in Smartlead campaign (Draft Mode)."
            }
        )

    def build_update_lead_payload(self, lead_id: str, followup_data: Union[EmailGenerationResult, Dict[str, Any]]) -> SmartleadPayload:
        """Simulates updating lead custom variables via POST /api/v1/campaigns/{campaign_id}/leads/{lead_id}."""
        if isinstance(followup_data, EmailGenerationResult):
            subject = followup_data.subject
            body = followup_data.body
            trigger = followup_data.email_type
        else:
            subject = followup_data.get("subject", "")
            body = followup_data.get("body", "")
            trigger = followup_data.get("trigger_state") or followup_data.get("pivot_angle", "")

        return SmartleadPayload(
            api_endpoint=f"POST /api/v1/campaigns/{self.campaign_id}/leads/{lead_id}",
            headers={
                "Content-Type": "application/json",
                "api_key": "YOUR_SMARTLEAD_API_KEY_PLACEHOLDER"
            },
            payload={
                "custom_fields": {
                    "followup_subject": subject,
                    "followup_body": body,
                    "followup_trigger": trigger
                }
            },
            mock_response={
                "ok": True,
                "status": "success",
                "lead_id": lead_id,
                "message": "Lead dynamic follow-up content updated via Smartlead API."
            }
        )

    def build_pause_lead_payload(self, lead_id: str, reason: str) -> SmartleadPayload:
        """Simulates pausing lead sequence via POST /api/v1/campaigns/{campaign_id}/leads/{lead_id}/pause."""
        return SmartleadPayload(
            api_endpoint=f"POST /api/v1/campaigns/{self.campaign_id}/leads/{lead_id}/pause",
            headers={
                "Content-Type": "application/json",
                "api_key": "YOUR_SMARTLEAD_API_KEY_PLACEHOLDER"
            },
            payload={
                "pause_reason": reason
            },
            mock_response={
                "ok": True,
                "status": "success",
                "lead_id": lead_id,
                "message": f"Lead sequence immediately PAUSED in Smartlead due to: {reason}"
            }
        )
