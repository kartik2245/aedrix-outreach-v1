"""
test_email_status_routing.py

Unit and Integration tests for Part 2: Email Status Routing & Approval Workflow.

Verifies:
1. VERIFIED leads:
   VERIFIED -> AI Email Generation -> Human Approval Gate -> Smartlead Staging Eligible.
2. UNVERIFIED leads:
   UNVERIFIED -> Staged at EMAIL_STATUS_APPROVAL -> Human Approval BEFORE AI Generation -> If Approved: AI Email Generation -> Stage 2 Draft Approval Gate -> Smartlead Staging Eligible.
3. UNVERIFIED Rejected leads:
   UNVERIFIED -> Rejection -> Preserved in store -> NO AI Email Generation -> NO Smartlead.
4. NO_EMAIL leads:
   NO_EMAIL -> Preserved in store -> NO AI Email Generation -> NO Send Approval -> NO Smartlead.
5. Smartlead Safety Gate:
   smartlead_eligible == True strictly AFTER final stage 2 approval.
"""

import pytest
import os
from unittest.mock import MagicMock
from src.approval.approval_engine import ApprovalEngine
from src.approval.approval_models import ApprovalStatus, ApprovalRecord
from src.approval.approval_store import ApprovalStore
from src.models import EmailStatus
from src.smartlead_staging_runner import SmartleadStagingRunner


@pytest.fixture
def tmp_approval_store(tmp_path):
    json_file = tmp_path / "approval_queue.json"
    return ApprovalStore(storage_path=str(json_file))


@pytest.fixture
def mock_llm_client():
    from src.models import EmailGenerationResult, PersonalizationNoteStatus
    client = MagicMock()
    mock_email = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Operations efficiency",
        body="Hello Jane,\n\nCustom email body for outreach.\n\nBest regards,\nAedrix Outreach Team\n\nIf you prefer not to receive emails, reply unsubscribe.",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
    )
    client.generate_email_1.return_value = mock_email
    client.generate_followup_a.return_value = mock_email
    client.generate_followup_b.return_value = mock_email
    return client


def test_verified_lead_routing(tmp_approval_store):
    engine = ApprovalEngine(store=tmp_approval_store)
    rec = engine.enroll_draft(
        company="Acme Build Ltd",
        contact="John Doe",
        title="Operations Manager",
        email="john@acmebuild.co.uk",
        qualification_status="QUALIFIED",
        opportunity_score=85.0,
        accessibility_score=90.0,
        outreach_priority_index=87.5,
        priority="P1",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="High growth commercial general contractor.",
        voc_angle="Commercial Subcontractor Coordination",
        email_1="Hello John, loved your recent commercial project.",
        followup_a="Following up on operational efficiency.",
        followup_b="Final check on subcontractor management.",
        qa_status="PASS",
        qa_reasons=[],
        email_status="VERIFIED",
    )

    assert rec.email_status == "VERIFIED"
    assert rec.approval_stage == "AI_EMAIL_APPROVAL"
    assert rec.workflow_status == "AWAITING_EMAIL_APPROVAL"
    assert rec.approval_status == ApprovalStatus.PENDING_REVIEW
    assert rec.smartlead_eligible is False
    assert rec.email_1_original == "Hello John, loved your recent commercial project."

    # Stage 2 Approval
    approved_rec = engine.approve(rec.lead_id, reviewer="HUMAN_OPERATOR")
    assert approved_rec.approval_status == ApprovalStatus.APPROVED
    assert approved_rec.smartlead_eligible is True


def test_unverified_lead_routing_approval_flow(tmp_approval_store, mock_llm_client):
    engine = ApprovalEngine(store=tmp_approval_store)

    # Step 1: Enroll UNVERIFIED lead (No AI generation initially)
    rec = engine.enroll_unverified_lead(
        company="Subcontractor Supplies Ltd",
        contact="Jane Smith",
        title="Commercial Director",
        email="jane@subconsupplies.co.uk",
        qualification_status="QUALIFIED",
        opportunity_score=80.0,
        accessibility_score=75.0,
        outreach_priority_index=77.5,
        priority="P2",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Expanding operations in North West.",
        voc_angle="Supply Chain Management",
    )

    assert rec.email_status == "UNVERIFIED"
    assert rec.approval_stage == "EMAIL_STATUS_APPROVAL"
    assert rec.workflow_status == "AWAITING_EMAIL_STATUS_APPROVAL"
    assert rec.approval_status == ApprovalStatus.PENDING_REVIEW
    assert rec.smartlead_eligible is False
    assert rec.email_1_original == ""

    # Step 2: Approve Email Status -> Triggers AI generation
    stage2_rec = engine.approve_email_status(rec.lead_id, llm_client=mock_llm_client, reviewer="HUMAN_OPERATOR")
    assert stage2_rec.approval_stage == "AI_EMAIL_APPROVAL"
    assert stage2_rec.workflow_status == "AWAITING_EMAIL_APPROVAL"
    assert stage2_rec.approval_status == ApprovalStatus.PENDING_REVIEW
    assert stage2_rec.smartlead_eligible is False
    assert stage2_rec.email_1_original == "Hello Jane,\n\nCustom email body for outreach.\n\nBest regards,\nAedrix Outreach Team\n\nIf you prefer not to receive emails, reply unsubscribe.", f"Blocked reason: {stage2_rec.blocked_reason}"

    # Step 3: Final Stage 2 Approval -> Smartlead Eligible
    final_rec = engine.approve(rec.lead_id, reviewer="HUMAN_OPERATOR")
    assert final_rec.approval_status == ApprovalStatus.APPROVED
    assert final_rec.smartlead_eligible is True


def test_unverified_lead_routing_rejection(tmp_approval_store):
    engine = ApprovalEngine(store=tmp_approval_store)

    rec = engine.enroll_unverified_lead(
        company="Risky Build Corp",
        contact="Mark Taylor",
        title="Director",
        email="mark@riskybuild.co.uk",
        qualification_status="QUALIFIED",
        opportunity_score=70.0,
        accessibility_score=60.0,
        outreach_priority_index=65.0,
        priority="P3",
        personalization_status="NO_STRONG_SIGNAL",
        personalization_note="Unverified email domain.",
        voc_angle="General Efficiency",
    )

    # Rejection at stage 1
    rejected_rec = engine.reject(rec.lead_id, reviewer="HUMAN_OPERATOR", reason="Unverified domain rejected")
    assert rejected_rec.approval_status == ApprovalStatus.REJECTED
    assert rejected_rec.smartlead_eligible is False
    assert rejected_rec.email_1_original == ""

    # Saved and preserved in store
    loaded = tmp_approval_store.get_record(rec.lead_id)
    assert loaded is not None
    assert loaded.approval_status == ApprovalStatus.REJECTED
    assert loaded.smartlead_eligible is False


def test_no_email_lead_routing(tmp_approval_store):
    engine = ApprovalEngine(store=tmp_approval_store)

    rec = engine.enroll_no_email_lead(
        company="Anonymous Builders PLC",
        contact="Unknown Contact",
        title="Managing Director",
        qualification_status="QUALIFIED",
        opportunity_score=90.0,
        accessibility_score=50.0,
        outreach_priority_index=70.0,
        priority="P2",
        personalization_status="NO_STRONG_SIGNAL",
        personalization_note="No email listed.",
        voc_angle="General Construction",
    )

    assert rec.email_status == "NO_EMAIL"
    assert rec.approval_stage == "NO_SEND"
    assert rec.workflow_status == "NO_EMAIL_PERSISTED"
    assert rec.approval_status == ApprovalStatus.BLOCKED
    assert rec.smartlead_eligible is False
    assert rec.email == ""
    assert rec.email_1_original == ""

    # Attempting to approve email status for NO_EMAIL lead raises error
    with pytest.raises(ValueError, match="Cannot generate AI email copy for NO_EMAIL lead"):
        engine.approve_email_status(rec.lead_id)


def test_smartlead_staging_runner_filters_unapproved_and_no_email(tmp_approval_store, mock_llm_client):
    engine = ApprovalEngine(store=tmp_approval_store)

    # 1. VERIFIED & APPROVED -> Eligible for Smartlead
    v_rec = engine.enroll_draft(
        company="Verified Corp",
        contact="Dave Ops",
        title="COO",
        email="dave@verifiedcorp.co.uk",
        qualification_status="QUALIFIED",
        opportunity_score=90.0,
        accessibility_score=90.0,
        outreach_priority_index=90.0,
        priority="P1",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Note",
        voc_angle="Angle",
        email_1="Hi Dave",
        followup_a="Followup A",
        followup_b="Followup B",
        qa_status="PASS",
        email_status="VERIFIED",
    )
    engine.approve(v_rec.lead_id)

    # 2. UNVERIFIED & PENDING -> Excluded
    engine.enroll_unverified_lead(
        company="Unverified Corp",
        contact="Sarah Ops",
        title="Director",
        email="sarah@unverifiedcorp.co.uk",
        qualification_status="QUALIFIED",
        opportunity_score=80.0,
        accessibility_score=80.0,
        outreach_priority_index=80.0,
        priority="P2",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Note",
        voc_angle="Angle",
    )

    # 3. NO_EMAIL -> Excluded
    engine.enroll_no_email_lead(
        company="No Email Ltd",
        contact="Bob Ops",
        title="Partner",
        qualification_status="QUALIFIED",
        opportunity_score=70.0,
        accessibility_score=70.0,
        outreach_priority_index=70.0,
        priority="P3",
        personalization_status="NO_STRONG_SIGNAL",
        personalization_note="Note",
        voc_angle="Angle",
    )

    runner = SmartleadStagingRunner(approval_store=tmp_approval_store)
    plan = runner.build_staging_plan()

    assert plan["summary"]["approved_eligible_count"] == 1
    assert plan["summary"]["excluded_count"] == 2
    assert plan["batches"][0]["leads"][0]["email"] == "dave@verifiedcorp.co.uk"
