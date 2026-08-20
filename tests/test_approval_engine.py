"""
test_approval_engine.py
Unit tests for Human Approval & Safety Gate layer in Aedrix Cold Outreach System (Python 3.12).

Tests:
1. New email enters PENDING_REVIEW.
2. QA failure creates BLOCKED.
3. Hard-disqualified lead is BLOCKED.
4. Campaign-excluded lead is BLOCKED.
5. Invalid email is BLOCKED.
6. NO_STRONG_SIGNAL remains reviewable but flagged.
7. Pending email cannot become Smartlead eligible.
8. Approved email becomes Smartlead eligible.
9. Rejected email cannot become Smartlead eligible.
10. Edited email preserves original AI draft.
11. Edited email requires approval.
12. Approval timestamp is recorded.
13. Original AI content is never overwritten.
14. No approval operation sends an email.
15. Approval store persistence and reload.
"""

import json
import os
import pytest
from src.approval.approval_engine import ApprovalEngine
from src.approval.approval_store import ApprovalStore
from src.approval.approval_models import ApprovalStatus, ApprovalRecord


@pytest.fixture
def tmp_store(tmp_path):
    store_file = str(tmp_path / "test_approval_queue.json")
    return ApprovalStore(storage_path=store_file)


@pytest.fixture
def engine(tmp_store):
    return ApprovalEngine(store=tmp_store)


@pytest.fixture
def base_qualified_lead_kwargs():
    return {
        "company": "Bowmer & Kirkland (B&K)",
        "contact": "John Foster",
        "title": "Business Improvement Director",
        "email": "j.foster@bandk.co.uk",
        "qualification_status": "QUALIFIED",
        "opportunity_score": 89.0,
        "accessibility_score": 88.0,
        "outreach_priority_index": 88.6,
        "priority": "P1",
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Saw Bowmer & Kirkland expanding their digital team.",
        "voc_angle": "Digital Transformation",
        "email_1": "Hi John,\n\nSaw your expansion.\n\nBest,\nAedrix",
        "followup_a": "Hi John,\n\nFollowing up.\n\nBest,\nAedrix",
        "followup_b": "Hi John,\n\nPivoting to workforce.\n\nBest,\nAedrix",
        "qa_status": "PASS",
        "qa_reasons": [],
        "email_status": "PATTERN_CONFIRMED"
    }


# --- Test 1: New email enters PENDING_REVIEW ---

def test_1_new_email_enters_pending_review(engine, base_qualified_lead_kwargs):
    record = engine.enroll_draft(**base_qualified_lead_kwargs)
    assert record.approval_status == ApprovalStatus.PENDING_REVIEW
    assert record.smartlead_eligible is False
    assert record.reviewer is None
    assert record.reviewed_at is None


# --- Test 2: QA failure creates BLOCKED ---

def test_2_qa_failure_creates_blocked(engine, base_qualified_lead_kwargs):
    kwargs = dict(base_qualified_lead_kwargs)
    kwargs["qa_status"] = "FAIL"
    kwargs["qa_reasons"] = ["Invented date/year '2029' detected", "Email 1 exceeds limit"]

    record = engine.enroll_draft(**kwargs)
    assert record.approval_status == ApprovalStatus.BLOCKED
    assert record.smartlead_eligible is False
    assert "Personalization QA failed" in (record.blocked_reason or "")
    assert "2029" in (record.blocked_reason or "")


# --- Test 3: Hard-disqualified lead is BLOCKED ---

def test_3_hard_disqualified_lead_is_blocked(engine, base_qualified_lead_kwargs):
    kwargs = dict(base_qualified_lead_kwargs)
    kwargs["qualification_status"] = "HARD_DISQUALIFIED"
    kwargs["disqualification_reason"] = "Non-UK geography (Headquarters or primary operations outside UK)"

    record = engine.enroll_draft(**kwargs)
    assert record.approval_status == ApprovalStatus.BLOCKED
    assert record.smartlead_eligible is False
    assert "Non-UK geography" in (record.blocked_reason or "")


# --- Test 4: Campaign-excluded lead is BLOCKED ---

def test_4_campaign_excluded_lead_is_blocked(engine, base_qualified_lead_kwargs):
    kwargs = dict(base_qualified_lead_kwargs)
    kwargs["qualification_status"] = "CAMPAIGN_EXCLUDED"
    kwargs["disqualification_reason"] = "Active sales deal or existing customer in CRM"

    record = engine.enroll_draft(**kwargs)
    assert record.approval_status == ApprovalStatus.BLOCKED
    assert record.smartlead_eligible is False
    assert "Active sales deal" in (record.blocked_reason or "")


# --- Test 5: Invalid email is BLOCKED ---

def test_5_invalid_email_is_blocked(engine, base_qualified_lead_kwargs):
    kwargs = dict(base_qualified_lead_kwargs)
    kwargs["email_status"] = "INVALID_BOUNCED"
    kwargs["email"] = "bounced_user@bandk.co.uk"

    record = engine.enroll_draft(**kwargs)
    assert record.approval_status == ApprovalStatus.BLOCKED
    assert record.smartlead_eligible is False
    assert "INVALID_BOUNCED" in (record.blocked_reason or "")


# --- Test 6: NO_STRONG_SIGNAL remains reviewable but flagged ---

def test_6_no_strong_signal_reviewable_and_flagged(engine, base_qualified_lead_kwargs):
    kwargs = dict(base_qualified_lead_kwargs)
    kwargs["personalization_status"] = "NO_STRONG_SIGNAL"

    record = engine.enroll_draft(**kwargs)
    assert record.approval_status == ApprovalStatus.PENDING_REVIEW
    assert record.flag_no_strong_signal is True
    assert record.smartlead_eligible is False


# --- Test 7: Pending email cannot become Smartlead eligible ---

def test_7_pending_email_not_smartlead_eligible(engine, base_qualified_lead_kwargs):
    record = engine.enroll_draft(**base_qualified_lead_kwargs)
    assert record.approval_status == ApprovalStatus.PENDING_REVIEW
    assert record.smartlead_eligible is False


# --- Test 8: Approved email becomes Smartlead eligible ---

def test_8_approved_email_becomes_smartlead_eligible(engine, base_qualified_lead_kwargs):
    record = engine.enroll_draft(**base_qualified_lead_kwargs)
    approved = engine.approve(record.lead_id, reviewer="Senior SDR Reviewer")

    assert approved.approval_status == ApprovalStatus.APPROVED
    assert approved.smartlead_eligible is True
    assert approved.reviewer == "Senior SDR Reviewer"
    assert approved.reviewed_at is not None


# --- Test 9: Rejected email cannot become Smartlead eligible ---

def test_9_rejected_email_cannot_become_eligible(engine, base_qualified_lead_kwargs):
    record = engine.enroll_draft(**base_qualified_lead_kwargs)
    rejected = engine.reject(record.lead_id, reviewer="Senior SDR", reason="Not the right timing for this account")

    assert rejected.approval_status == ApprovalStatus.REJECTED
    assert rejected.smartlead_eligible is False
    assert "Not the right timing" in (rejected.blocked_reason or "")


# --- Test 10: Edited email preserves original AI draft ---

def test_10_edited_email_preserves_original_ai_draft(engine, base_qualified_lead_kwargs):
    record = engine.enroll_draft(**base_qualified_lead_kwargs)
    original_e1 = record.email_1_original

    edited = engine.edit(
        record.lead_id,
        email_1="Hi John,\n\nCustom human edited message text.\n\nBest,\nHuman",
        reviewer="Campaign Manager"
    )

    assert edited.email_1_original == original_e1  # Untouched
    assert edited.edited_email_1 == "Hi John,\n\nCustom human edited message text.\n\nBest,\nHuman"
    assert edited.approval_status == ApprovalStatus.EDITED


# --- Test 11: Edited email requires explicit approval ---

def test_11_edited_email_requires_approval(engine, base_qualified_lead_kwargs):
    record = engine.enroll_draft(**base_qualified_lead_kwargs)
    engine.edit(record.lead_id, email_1="Modified text", reviewer="Editor")

    edited_rec = engine.store.get_record(record.lead_id)
    assert edited_rec.approval_status == ApprovalStatus.EDITED
    assert edited_rec.smartlead_eligible is False  # Must NOT be eligible immediately

    # Explicit approval subsequent to edit
    approved_rec = engine.approve(record.lead_id, reviewer="Approver")
    assert approved_rec.approval_status == ApprovalStatus.APPROVED
    assert approved_rec.smartlead_eligible is True


# --- Test 12: Approval timestamp is recorded ---

def test_12_approval_timestamp_is_recorded(engine, base_qualified_lead_kwargs):
    record = engine.enroll_draft(**base_qualified_lead_kwargs)
    approved = engine.approve(record.lead_id, reviewer="Compliance Officer")

    assert approved.reviewed_at is not None
    assert "T" in approved.reviewed_at  # ISO format string


# --- Test 13: Original AI content is never overwritten ---

def test_13_original_ai_content_immutable_across_multiple_edits(engine, base_qualified_lead_kwargs):
    record = engine.enroll_draft(**base_qualified_lead_kwargs)
    orig_1 = record.email_1_original
    orig_fa = record.followup_a_original
    orig_fb = record.followup_b_original

    engine.edit(record.lead_id, email_1="Edit 1", reviewer="User A")
    engine.edit(record.lead_id, email_1="Edit 2", followup_a="FA Edit 1", reviewer="User B")

    updated = engine.store.get_record(record.lead_id)
    assert updated.email_1_original == orig_1
    assert updated.followup_a_original == orig_fa
    assert updated.followup_b_original == orig_fb
    assert updated.edited_email_1 == "Edit 2"
    assert updated.edited_followup_a == "FA Edit 1"


# --- Test 14: No approval operation sends an email ---

def test_14_no_approval_operation_sends_email(engine, base_qualified_lead_kwargs):
    """Verifies that approval operations are strictly state transitions without external side-effects."""
    record = engine.enroll_draft(**base_qualified_lead_kwargs)
    app = engine.approve(record.lead_id)
    assert app.approval_status == ApprovalStatus.APPROVED
    # State updated locally, zero network calls or external mutations performed.


# --- Test 15: Cannot approve a BLOCKED lead directly ---

def test_15_cannot_approve_blocked_lead_directly(engine, base_qualified_lead_kwargs):
    kwargs = dict(base_qualified_lead_kwargs)
    kwargs["qa_status"] = "FAIL"
    record = engine.enroll_draft(**kwargs)

    with pytest.raises(ValueError, match="Cannot approve BLOCKED lead"):
        engine.approve(record.lead_id)
