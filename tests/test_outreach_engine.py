"""
test_outreach_engine.py
Pytest unit tests for Phase 5 Outreach Engine (Python 3.12).
Tests 14 mandatory test cases.
"""

import json
import os
import pytest
from src.outreach_engine import OutreachEngine
from src.email_generator import EmailGenerator
from src.reply_classifier import ReplyClassifier
from src.research_pipeline import ResearchPipeline
from src.models import OutreachState, PersonalizationNoteStatus, LeadIntelligenceOutput


@pytest.fixture
def engine():
    return OutreachEngine()


@pytest.fixture
def generator():
    return EmailGenerator()


@pytest.fixture
def classifier():
    return ReplyClassifier()


@pytest.fixture
def pilot_leads():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    export_path = os.path.join(base_dir, "data", "deepline_export_sample.json")
    return ResearchPipeline().process_dataset(export_path)


def test_1_qualified_lead_generates_email_1(engine, pilot_leads):
    lead1 = pilot_leads[0]
    record = engine.enroll_lead(lead1)
    assert record is not None
    assert record.email1 is not None
    assert record.email1.email_type == "EMAIL_1"
    assert len(record.email1.body) > 0


def test_2_no_strong_signal_lead_uses_baseline_value_prop(generator, pilot_leads):
    no_signal_lead = next(l for l in pilot_leads if l.personalization_note_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL)
    email_res = generator.generate_email_1(no_signal_lead)
    assert email_res.personalization_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL
    assert "more clients now expect a common data environment" in email_res.body


def test_3_signal_verified_lead_uses_approved_personalization(generator, pilot_leads):
    verified_lead = next(l for l in pilot_leads if l.personalization_note_status == PersonalizationNoteStatus.SIGNAL_VERIFIED)
    email_res = generator.generate_email_1(verified_lead)
    assert email_res.personalization_status == PersonalizationNoteStatus.SIGNAL_VERIFIED
    assert "John" in email_res.body
    assert verified_lead.company_name in email_res.body


def test_4_email_1_payload_generated_correctly(engine, pilot_leads):
    record = engine.enroll_lead(pilot_leads[1])
    assert record.smartlead_id.startswith("sl_lead_")
    assert record.state_machine.get_current_state() == OutreachState.EMAIL_1_SENT


def test_5_opened_event_moves_to_followup_a(engine, pilot_leads):
    engine.enroll_lead(pilot_leads[0])
    followup_a = engine.simulate_opened_event(pilot_leads[0].email)
    state = engine.pipelines[pilot_leads[0].email].state_machine.get_current_state()
    assert state == OutreachState.FOLLOWUP_A_SENT
    assert followup_a.email_type == "FOLLOWUP_A"
    assert followup_a.subject.startswith("Re:")


def test_6_unopened_event_moves_to_followup_b(engine, pilot_leads):
    engine.enroll_lead(pilot_leads[3])
    followup_b = engine.simulate_unopened_timeout(pilot_leads[3].email)
    state = engine.pipelines[pilot_leads[3].email].state_machine.get_current_state()
    assert state == OutreachState.FOLLOWUP_B_SENT
    assert followup_b.email_type == "FOLLOWUP_B"
    assert followup_b.subject in ("who owns the record", "the golden thread question")


def test_7_positive_reply_triggers_human_sales_handoff(engine, pilot_leads):
    engine.enroll_lead(pilot_leads[2])
    pos_res = engine.simulate_reply_event(pilot_leads[2].email, "Yes, this sounds interesting. Can we schedule a demo next week?")
    state = engine.pipelines[pilot_leads[2].email].state_machine.get_current_state()
    assert pos_res.classification == "POSITIVE"
    assert pos_res.requires_human_handoff is True
    assert state == OutreachState.HANDOFF_HUMAN_SALES


def test_8_negative_reply_does_not_trigger_handoff(engine, pilot_leads):
    engine.enroll_lead(pilot_leads[4])
    neg_res = engine.simulate_reply_event(pilot_leads[4].email, "Not interested, thanks.")
    state = engine.pipelines[pilot_leads[4].email].state_machine.get_current_state()
    assert neg_res.classification == "NEGATIVE"
    assert neg_res.requires_human_handoff is False
    assert state == OutreachState.SUPPRESSED_NOT_INTERESTED


def test_9_ooo_reply_does_not_trigger_sales_handoff(classifier):
    ooo_res = classifier.classify_reply("I am currently out of the office and will return Monday.")
    assert ooo_res.classification == "OOO"
    assert ooo_res.requires_human_handoff is False


def test_10_unsubscribe_stops_outreach(classifier):
    unsub_res = classifier.classify_reply("Please remove me from your mailing list.")
    assert unsub_res.classification == "UNSUBSCRIBE"
    assert unsub_res.classification != "POSITIVE"
    assert unsub_res.requires_human_handoff is False


def test_11_bounce_stops_outreach(engine, pilot_leads):
    engine.enroll_lead(pilot_leads[3])
    bounce_state = engine.simulate_bounce_event(pilot_leads[3].email, "HARD_BOUNCE")
    assert bounce_state == OutreachState.STOPPED_BOUNCED


def test_12_transition_history_recording(engine, pilot_leads):
    engine.enroll_lead(pilot_leads[0])
    engine.simulate_opened_event(pilot_leads[0].email)
    history = engine.pipelines[pilot_leads[0].email].state_machine.get_history()
    assert len(history) >= 4
    assert any(h.get("metadata", {}).get("delay_days") == 1 for h in history)


def test_13_zero_external_network_calls_enforced(generator, classifier, pilot_leads):
    email_res = generator.generate_email_1(pilot_leads[0])
    class_res = classifier.classify_reply("Yes, send info")
    assert email_res.generation_mode == "DRY_RUN_TEMPLATE"
    assert class_res.generation_mode == "DRY_RUN_TEMPLATE"


def test_14_all_5_pilot_leads_orchestration(engine, pilot_leads):
    for lead in pilot_leads:
        record = engine.enroll_lead(lead)
        assert record is not None and record.email1 is not None
