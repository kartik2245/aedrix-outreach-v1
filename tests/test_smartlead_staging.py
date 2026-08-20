"""
test_smartlead_staging.py
Comprehensive test suite for Smartlead Staging Runner, Production Runner, Safety Gates, and Batch Processing.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from src.approval.approval_models import ApprovalRecord, ApprovalStatus
from src.approval.approval_store import ApprovalStore
from src.approval.approval_engine import ApprovalEngine
from src.smartlead_staging_runner import SmartleadStagingRunner
from src.smartlead_production_runner import SmartleadProductionRunner
from src.integrations.smartlead_client import (
    SmartleadClient,
    SmartleadConfigError,
)
from src.reply_classifier import ReplyClassifier
from src.models import SmartleadWebhookEventType


@pytest.fixture
def temp_approval_store(tmp_path):
    """Fixture creating an isolated ApprovalStore."""
    store_file = tmp_path / "approval_queue_test.json"
    store = ApprovalStore(storage_path=str(store_file))
    return store


@pytest.fixture
def populated_approval_store(temp_approval_store):
    """Populates store with diverse records: 1 Approved, 1 Pending, 1 Blocked, 1 Rejected, 1 Edited."""
    store = temp_approval_store
    engine = ApprovalEngine(store=store)

    # 1. Approved Lead
    r1 = engine.enroll_draft(
        company="Kier Group plc",
        contact="Colin Bell",
        title="Digital Director",
        email="c.bell@kier.co.uk",
        qualification_status="QUALIFIED",
        opportunity_score=87.0,
        accessibility_score=78.0,
        outreach_priority_index=83.4,
        priority="P2",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Operates an official Digital by Default strategy.",
        voc_angle="Digital Transformation",
        email_1="Hi Colin, email 1 original body",
        followup_a="Hi Colin, followup a original",
        followup_b="Hi Colin, followup b original",
        qa_status="PASS",
    )
    engine.approve(r1.lead_id, reviewer="Sarah Campaign Lead")

    # 2. Pending Lead
    engine.enroll_draft(
        company="Bowmer & Kirkland",
        contact="John Foster",
        title="Business Improvement Director",
        email="j.foster@bandk.co.uk",
        qualification_status="QUALIFIED",
        opportunity_score=89.0,
        accessibility_score=88.0,
        outreach_priority_index=88.6,
        priority="P1",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Saw recent digital expansion initiative.",
        voc_angle="Pre-construction",
        email_1="Hi John, email 1",
        followup_a="Hi John, followup a",
        followup_b="Hi John, followup b",
        qa_status="PASS",
    )

    # 3. Blocked Lead (QA Failure / Disqualified)
    engine.enroll_draft(
        company="Disqualified Contractor",
        contact="Dave Smith",
        title="Site Manager",
        email="dave@fake.com",
        qualification_status="HARD_DISQUALIFIED",
        opportunity_score=20.0,
        accessibility_score=30.0,
        outreach_priority_index=25.0,
        priority="P3",
        personalization_status="NO_STRONG_SIGNAL",
        personalization_note="None",
        voc_angle="N/A",
        email_1="[SKIPPED]",
        followup_a="[SKIPPED]",
        followup_b="[SKIPPED]",
        qa_status="FAIL",
        disqualification_reason="Outside UK territory"
    )

    # 4. Rejected Lead
    r4 = engine.enroll_draft(
        company="Balfour Beatty",
        contact="Jon Ozanne",
        title="CIO",
        email="j.ozanne@balfour.com",
        qualification_status="QUALIFIED",
        opportunity_score=80.0,
        accessibility_score=70.0,
        outreach_priority_index=75.0,
        priority="P2",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="CIO digital delivery mandate.",
        voc_angle="Pre-construction",
        email_1="Hi Jon, email 1",
        followup_a="Hi Jon, followup a",
        followup_b="Hi Jon, followup b",
        qa_status="PASS",
    )
    engine.reject(r4.lead_id, reviewer="Operator", reason="Not targeting currently")

    # 5. Edited but NOT re-approved Lead
    r5 = engine.enroll_draft(
        company="Morgan Sindall",
        contact="Lee Ramsey",
        title="BIM Director",
        email="l.ramsey@morgansindall.com",
        qualification_status="QUALIFIED",
        opportunity_score=81.0,
        accessibility_score=72.0,
        outreach_priority_index=77.4,
        priority="P2",
        personalization_status="NO_STRONG_SIGNAL",
        personalization_note="Role leading operations.",
        voc_angle="Pre-construction",
        email_1="Hi Lee, original email 1",
        followup_a="Hi Lee, original followup a",
        followup_b="Hi Lee, original followup b",
        qa_status="PASS",
    )
    engine.edit(r5.lead_id, email_1="Hi Lee, edited email 1 by human reviewer", reviewer="Editor")

    return store


def test_1_staging_runner_filters_only_approved_and_eligible(populated_approval_store, tmp_path):
    """Staging plan must include only the 1 approved lead and exclude pending/rejected/blocked/edited leads."""
    output_file = tmp_path / "smartlead_staging_plan.json"
    runner = SmartleadStagingRunner(approval_store=populated_approval_store, batch_size=400)
    plan = runner.build_staging_plan(output_path=str(output_file))

    assert os.path.exists(str(output_file))
    assert plan["summary"]["total_queue_records"] == 5
    assert plan["summary"]["approved_eligible_count"] == 1
    assert plan["summary"]["excluded_count"] == 4

    # Check the 1 approved lead
    staged_batch = plan["batches"][0]
    assert len(staged_batch["leads"]) == 1
    staged_lead = staged_batch["leads"][0]
    assert staged_lead["email"] == "c.bell@kier.co.uk"
    assert staged_lead["first_name"] == "Colin"
    assert staged_lead["last_name"] == "Bell"
    assert staged_lead["company_name"] == "Kier Group plc"


def test_2_lead_payload_custom_fields_mapping(populated_approval_store, tmp_path):
    """Custom fields mapping must contain all necessary dynamic variables for Smartlead."""
    output_file = tmp_path / "smartlead_staging_plan.json"
    runner = SmartleadStagingRunner(approval_store=populated_approval_store)
    plan = runner.build_staging_plan(output_path=str(output_file))

    staged_lead = plan["batches"][0]["leads"][0]
    custom_fields = staged_lead["custom_fields"]

    assert custom_fields["job_title"] == "Digital Director"
    assert custom_fields["opportunity_score"] == 87.0
    assert custom_fields["accessibility_score"] == 78.0
    assert custom_fields["outreach_priority_index"] == 83.4
    assert custom_fields["priority"] == "P2"
    assert "Digital by Default" in custom_fields["personalization_note"]
    assert custom_fields["voc_angle"] == "Digital Transformation"
    assert "email_1_subject" in custom_fields
    assert "email_1_body" in custom_fields
    assert "followup_a_subject" in custom_fields
    assert "followup_a_body" in custom_fields
    assert "followup_b_subject" in custom_fields
    assert "followup_b_body" in custom_fields


def test_3_sequence_configuration_enforces_2_day_wait_rule():
    """Sequence configuration must enforce wait rules for all 3 touches."""
    runner = SmartleadStagingRunner()
    seq = runner.build_campaign_sequence()

    assert len(seq) == 3
    assert seq[0]["step_type"] == "INITIAL_EMAIL"
    assert seq[0]["seq_delay_details"]["delay_in_days"] == 0

    assert seq[1]["step_type"] == "FOLLOW_UP_OPENED_BRANCH_A"
    assert seq[1]["seq_delay_details"]["delay_in_days"] == 2

    assert seq[2]["step_type"] == "FOLLOW_UP_UNOPENED_BRANCH_B"
    assert seq[2]["seq_delay_details"]["delay_in_days"] == 2


def test_4_edited_and_reapproved_lead_uses_edited_copy(temp_approval_store, tmp_path):
    """An edited draft that is subsequently approved must use the human-edited copy in staging."""
    store = temp_approval_store
    engine = ApprovalEngine(store=store)

    r = engine.enroll_draft(
        company="Laing O'Rourke",
        contact="Adrian Spragg",
        title="Head of Digital",
        email="a.spragg@laing.com",
        qualification_status="QUALIFIED",
        opportunity_score=85.0,
        accessibility_score=80.0,
        outreach_priority_index=82.5,
        priority="P2",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Leads digital strategy.",
        voc_angle="Pre-construction",
        email_1="Original AI Email 1",
        followup_a="Original Follow-up A",
        followup_b="Original Follow-up B",
        qa_status="PASS"
    )

    # Human edits Email 1
    engine.edit(r.lead_id, email_1="Human Edited Custom Email 1", reviewer="Reviewer")
    # Human re-approves
    engine.approve(r.lead_id, reviewer="Lead Reviewer")

    runner = SmartleadStagingRunner(approval_store=store)
    plan = runner.build_staging_plan(output_path=str(tmp_path / "plan.json"))

    staged_lead = plan["batches"][0]["leads"][0]
    assert staged_lead["custom_fields"]["email_1_body"] == "Human Edited Custom Email 1"


def test_5_batch_chunking_logic(temp_approval_store, tmp_path):
    """Batch chunking properly splits large lead volumes into configured batch sizes."""
    store = temp_approval_store
    engine = ApprovalEngine(store=store)

    # Create 5 approved leads
    for i in range(5):
        rec = engine.enroll_draft(
            company=f"Company {i+1}",
            contact=f"Contact {i+1}",
            title="Director",
            email=f"contact{i+1}@company{i+1}.co.uk",
            qualification_status="QUALIFIED",
            opportunity_score=80.0,
            accessibility_score=80.0,
            outreach_priority_index=80.0,
            priority="P1",
            personalization_status="SIGNAL_VERIFIED",
            personalization_note="Note",
            voc_angle="VoC",
            email_1="Email 1",
            followup_a="Followup A",
            followup_b="Followup B",
            qa_status="PASS"
        )
        engine.approve(rec.lead_id)

    # Run with batch_size=2 -> should generate 3 batches (2, 2, 1)
    runner = SmartleadStagingRunner(approval_store=store, batch_size=2)
    plan = runner.build_staging_plan(output_path=str(tmp_path / "batch_plan.json"))

    batches = plan["batches"]
    assert len(batches) == 3
    assert batches[0]["batch_size"] == 2
    assert batches[1]["batch_size"] == 2
    assert batches[2]["batch_size"] == 1


def test_6_production_runner_mode_1_dry_run(populated_approval_store, tmp_path):
    """Production runner in dry-run mode produces staging plan with 0 API calls."""
    client = SmartleadClient(dry_run=True, live=False)
    log_dir = tmp_path / "logs"
    runner = SmartleadProductionRunner(
        client=client,
        approval_store=populated_approval_store,
        log_dir=str(log_dir)
    )

    res = runner.run()
    assert res["mode"] == "MODE_1_DRY_RUN"
    assert res["status"] == "SUCCESS"
    assert res["leads_uploaded"] == 0
    assert os.path.exists(runner.audit_log_path)


def test_7_production_runner_send_emails_requires_confirmation(populated_approval_store, tmp_path):
    """Production runner with SEND_EMAILS=true without confirmation must raise SmartleadConfigError and block."""
    client = SmartleadClient(api_key="valid_key", dry_run=False, live=True, send_emails=True)
    log_dir = tmp_path / "logs"
    runner = SmartleadProductionRunner(
        client=client,
        approval_store=populated_approval_store,
        log_dir=str(log_dir)
    )

    with pytest.raises(SmartleadConfigError) as exc_info:
        runner.run(force_production_confirmation=False)
    assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


@patch("urllib.request.urlopen")
def test_8_production_runner_mode_2_safe_api_test(mock_urlopen, populated_approval_store, tmp_path):
    """Production runner in Mode 2 performs safe API calls, uploads leads in paused state with 0 emails sent."""
    # Mock responses for create_campaign, update_sequence, add_leads, pause_campaign
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({
        "ok": True,
        "id": 991122,
        "status": "DRAFT",
        "leads_added": 1
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = SmartleadClient(api_key="valid_key", dry_run=False, live=True, send_emails=False)
    log_dir = tmp_path / "logs"
    runner = SmartleadProductionRunner(
        client=client,
        approval_store=populated_approval_store,
        log_dir=str(log_dir)
    )

    res = runner.run()
    assert res["mode"] == "MODE_2_API_TEST"
    assert res["status"] == "SUCCESS"
    assert res["campaign_id"] == "991122"
    assert res["leads_uploaded"] == 1


def test_9_webhook_to_reply_classifier_sales_handoff():
    """Normalized reply webhook with positive intent triggers human sales handoff."""
    client = SmartleadClient()
    classifier = ReplyClassifier()

    raw_webhook = {
        "event_type": "email_reply",
        "lead_email": "c.bell@kier.co.uk",
        "reply_text": "Hi, sounds interesting. Can you schedule a 2-minute demo with our BIM director next Tuesday?"
    }

    event = client.normalize_webhook_event(raw_webhook)
    assert event.event_type == SmartleadWebhookEventType.EMAIL_REPLIED

    classification = classifier.classify_reply(event.details["reply_text"])
    assert classification.classification == "POSITIVE"
    assert classification.requires_human_handoff is True
