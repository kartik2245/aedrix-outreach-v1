"""
outreach_engine.py
Master Orchestration Engine for Phase 5 (Offline Dry-Run - Python 3.12).
Connects Lead Intelligence Output -> Email Generation -> Smartlead Payloads -> State Machine -> Reply Intent Classification.
Zero external network calls; 100% dry-run template mode.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from src.models import (
    LeadIntelligenceOutput,
    DisqualificationStatus,
    OutreachState,
    EmailGenerationResult,
    ReplyClassificationResult,
)
from src.email_generator import EmailGenerator
from src.reply_classifier import ReplyClassifier
from src.outreach_state_machine import OutreachStateMachine
from src.smartlead_simulator import SmartleadSimulator


class PipelineRecord:
    def __init__(
        self,
        lead: LeadIntelligenceOutput,
        state_machine: OutreachStateMachine,
        email1: EmailGenerationResult,
        smartlead_id: str
    ):
        self.lead = lead
        self.state_machine = state_machine
        self.email1 = email1
        self.smartlead_id = smartlead_id
        self.followup_a: Optional[EmailGenerationResult] = None
        self.followup_b: Optional[EmailGenerationResult] = None
        self.reply_classification: Optional[ReplyClassificationResult] = None


class OutreachEngine:
    def __init__(self):
        self.email_generator = EmailGenerator()
        self.reply_classifier = ReplyClassifier()
        self.smartlead_simulator = SmartleadSimulator(123456)
        self.pipelines: Dict[str, PipelineRecord] = {}
        self.stats = {
            "qualified_leads": 0,
            "email_1_generated": 0,
            "followup_a_generated": 0,
            "followup_b_generated": 0,
            "positive_replies": 0,
            "human_handoffs": 0,
            "bounces_handled": 0,
            "unsubscribes_handled": 0
        }

    def enroll_lead(self, lead_intel: LeadIntelligenceOutput) -> Optional[PipelineRecord]:
        """Enrolls a qualified lead into the outreach pipeline."""
        if lead_intel.disqualification_status != DisqualificationStatus.QUALIFIED:
            return None

        self.stats["qualified_leads"] += 1
        sm = OutreachStateMachine(lead_intel.email)
        sm.transition(OutreachState.QUALIFIED, {"lead_name": lead_intel.contact_name, "company": lead_intel.company_name})

        # 1. Generate Email 1
        sm.transition(OutreachState.EMAIL_1_READY)
        email1 = self.email_generator.generate_email_1(lead_intel)
        self.stats["email_1_generated"] += 1

        # 2. Build Smartlead Payload
        smartlead_payload = self.smartlead_simulator.build_lead_enrollment_payload(lead_intel, email1)
        smartlead_id = smartlead_payload.mock_response["lead_id"]

        sm.transition(OutreachState.EMAIL_1_SENT, {"email_1": email1.model_dump(), "smartlead_id": smartlead_id})

        record = PipelineRecord(
            lead=lead_intel,
            state_machine=sm,
            email1=email1,
            smartlead_id=smartlead_id
        )

        self.pipelines[lead_intel.email] = record
        return record

    def simulate_opened_event(self, lead_email: str, open_timestamp: Optional[str] = None) -> Optional[EmailGenerationResult]:
        """Simulates EMAIL_OPENED event (Branch A)."""
        record = self.pipelines.get(lead_email)
        if not record:
            return None

        if not open_timestamp:
            open_timestamp = datetime.now(timezone.utc).isoformat()

        sm = record.state_machine
        sm.transition(OutreachState.EMAIL_1_OPENED, {"timestamp": open_timestamp})
        sm.transition(OutreachState.WAITING_FOLLOWUP_A, {"delay_days": 1})

        sm.transition(OutreachState.FOLLOWUP_A_READY)
        followup_a = self.email_generator.generate_followup_a(record.lead, record.email1)
        self.stats["followup_a_generated"] += 1

        update_payload = self.smartlead_simulator.build_update_lead_payload(record.smartlead_id, followup_a)
        sm.transition(OutreachState.FOLLOWUP_A_SENT, {"followup_a": followup_a.model_dump(), "payload": update_payload.model_dump()})

        record.followup_a = followup_a
        return followup_a

    def simulate_unopened_timeout(self, lead_email: str) -> Optional[EmailGenerationResult]:
        """Simulates EMAIL_UNOPENED 48h timeout event (Branch B)."""
        record = self.pipelines.get(lead_email)
        if not record:
            return None

        sm = record.state_machine
        sm.transition(OutreachState.EMAIL_1_UNOPENED, {"timeout": "48_HOURS_NO_OPEN"})
        sm.transition(OutreachState.WAITING_FOLLOWUP_B, {"delay_days": 2})

        sm.transition(OutreachState.FOLLOWUP_B_READY)
        followup_b = self.email_generator.generate_followup_b(record.lead)
        self.stats["followup_b_generated"] += 1

        update_payload = self.smartlead_simulator.build_update_lead_payload(record.smartlead_id, followup_b)
        sm.transition(OutreachState.FOLLOWUP_B_SENT, {"followup_b": followup_b.model_dump(), "payload": update_payload.model_dump()})

        record.followup_b = followup_b
        return followup_b

    def simulate_reply_event(self, lead_email: str, reply_text: str) -> Optional[ReplyClassificationResult]:
        """Simulates prospect reply event & classification."""
        record = self.pipelines.get(lead_email)
        if not record:
            return None

        sm = record.state_machine
        self.smartlead_simulator.build_pause_lead_payload(record.smartlead_id, "PROSPECT_REPLIED")
        sm.transition(OutreachState.STOPPED_REPLIED, {"reply_text": reply_text})

        classification = self.reply_classifier.classify_reply(reply_text)
        record.reply_classification = classification

        if classification.classification == "POSITIVE":
            self.stats["positive_replies"] += 1
            self.stats["human_handoffs"] += 1
            sm.transition(OutreachState.HANDOFF_HUMAN_SALES, {"classification": classification.model_dump()})
        elif classification.classification == "UNSUBSCRIBE":
            self.stats["unsubscribes_handled"] += 1
            sm.transition(OutreachState.STOPPED_UNSUBSCRIBED, {"classification": classification.model_dump()})
        elif classification.classification == "OOO":
            sm.transition(OutreachState.OOO_DELAYED, {"classification": classification.model_dump(), "delay_days": 5})
        else:
            sm.transition(OutreachState.SUPPRESSED_NOT_INTERESTED, {"classification": classification.model_dump()})

        return classification

    def simulate_bounce_event(self, lead_email: str, bounce_type: str = "HARD_BOUNCE") -> OutreachState:
        """Simulates EMAIL_BOUNCED event."""
        record = self.pipelines.get(lead_email)
        if not record:
            return OutreachState.INITIAL

        sm = record.state_machine
        self.smartlead_simulator.build_pause_lead_payload(record.smartlead_id, "EMAIL_BOUNCED")
        self.stats["bounces_handled"] += 1
        sm.transition(OutreachState.STOPPED_BOUNCED, {"bounce_type": bounce_type})
        return OutreachState.STOPPED_BOUNCED

    def simulate_unsubscribe_event(self, lead_email: str) -> OutreachState:
        """Simulates EMAIL_UNSUBSCRIBED event."""
        record = self.pipelines.get(lead_email)
        if not record:
            return OutreachState.INITIAL

        sm = record.state_machine
        self.smartlead_simulator.build_pause_lead_payload(record.smartlead_id, "PROSPECT_UNSUBSCRIBED")
        self.stats["unsubscribes_handled"] += 1
        sm.transition(OutreachState.STOPPED_UNSUBSCRIBED)
        return OutreachState.STOPPED_UNSUBSCRIBED

    def simulate_touch_3(self, lead_email: str) -> Optional[EmailGenerationResult]:
        """Touch 3 is non-executable in AEDRIX V1 (Strict 3-step sequence)."""
        raise NotImplementedError("Touch 3 is non-executable in AEDRIX V1 sequence (Email 1, Follow-up A, Follow-up B only).")

    def simulate_touch_4(self, lead_email: str) -> Optional[EmailGenerationResult]:
        """Touch 4 is non-executable in AEDRIX V1 (Strict 3-step sequence)."""
        raise NotImplementedError("Touch 4 is non-executable in AEDRIX V1 sequence (Email 1, Follow-up A, Follow-up B only).")

    def simulate_touch_5(self, lead_email: str, touch_4_subject: str) -> Optional[EmailGenerationResult]:
        """Touch 5 is non-executable in AEDRIX V1 (Strict 3-step sequence)."""
        raise NotImplementedError("Touch 5 is non-executable in AEDRIX V1 sequence (Email 1, Follow-up A, Follow-up B only).")

    def get_stats(self) -> Dict[str, int]:
        return self.stats
