"""
test_revised_qa.py
Focused Unit Tests for AEDRIX Deterministic Personalization QA Engine.
Covers exact 30 PASS (1-12) and FAIL (13-30) scenarios requested by Section 5.
"""

import os
import tempfile
import pytest

from src.personalization.personalization_qa import PersonalizationQA
from src.approval.approval_engine import ApprovalEngine
from src.approval.approval_store import ApprovalStore
from src.models import (
    LeadIntelligenceOutput,
    EvidenceLevel,
    EmailStatus,
    DisqualificationStatus,
    PersonalizationNoteStatus,
    PriorityLevel,
    AccessibilityTier,
    EmailGenerationResult,
)


@pytest.fixture
def qa_engine():
    return PersonalizationQA()


@pytest.fixture
def valid_lead():
    return LeadIntelligenceOutput(
        company_name="AcmeMinds Private Limited",
        company_domain="acmeminds.com",
        contact_name="Sandeep Mehra",
        job_title="Managing Director",
        email="sandeep.mehra@acmeminds.com",
        email_status=EmailStatus.VERIFIED,
        company_size="100 employees",
        company_size_evidence=EvidenceLevel.VERIFIED,
        industry="Software & IT Solutions",
        opportunity_score=85.0,
        accessibility_score=90.0,
        outreach_priority_index=87.0,
        priority_level=PriorityLevel.P1,
        opportunity_tier="Tier 1",
        accessibility_tier=AccessibilityTier.HIGH,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
        personalization_note="Expanding software development team to 15 members in 2025.",
        research_sources=["https://acmeminds.com/about"],
        ICP_score=85.0,
        pain_point="Streamlining client onboarding.",
        pain_point_evidence=EvidenceLevel.INFERRED,
        relevant_signal="expanding software development team in 2025",
        relevant_signal_evidence=EvidenceLevel.VERIFIED,
        persona_selection_rationale="Selected Managing Director for primary decision authority."
    )


# ==============================================================================
# PASS TEST CASES (1 - 12)
# ==============================================================================

def test_pass_01_valid_personalized_email(qa_engine, valid_lead):
    """PASS 1: Valid personalized email -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Software team onboarding at AcmeMinds",
        body="Hi Sandeep,\n\nSaw AcmeMinds Private Limited is expanding your software development team in 2025.\n\nAedrix provides automated outreach workflow tools.\n\nOpen for a 2-min chat?\n\nBest regards,\nAlex Mitchell\nOutreach Manager, Aedrix\nTo unsubscribe, click here: https://aedrix.com/unsubscribe?email=sandeep.mehra@acmeminds.com",
        word_count=42,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_02_correct_recipient_name(qa_engine, valid_lead):
    """PASS 2: Correct recipient name -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Growth note",
        body="Hi Sandeep,\n\nExpanding AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_03_valid_company(qa_engine, valid_lead):
    """PASS 3: Valid company -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Workflows at AcmeMinds",
        body="Hi Sandeep,\n\nNote regarding AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_04_evidence_grounded_personalization(qa_engine, valid_lead):
    """PASS 4: Evidence-grounded personalization -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Software team expansion",
        body="Hi Sandeep,\n\nSaw AcmeMinds Private Limited expanding software team in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=22,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_05_valid_unsubscribe_url(qa_engine, valid_lead):
    """PASS 5: Valid unsubscribe URL -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Outreach update",
        body="Hi Sandeep,\n\nExpanding AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nhttps://aedrix.com/unsubscribe?email=sandeep@acmeminds.com",
        word_count=18,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_06_valid_actionable_unsubscribe_cta(qa_engine, valid_lead):
    """PASS 6: Valid actionable unsubscribe CTA -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Outreach update",
        body="Hi Sandeep,\n\nExpanding AcmeMinds Private Limited in 2025.\n\nIf you prefer not to receive these emails, reply unsubscribe.\n\nBest regards,\nAlex Mitchell",
        word_count=22,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_07_normal_vocabulary_streamline_passes(qa_engine, valid_lead):
    """PASS 7: 'streamline' passes -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Streamline workflows",
        body="Hi Sandeep,\n\nHelp streamline AcmeMinds Private Limited operations in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_08_solution_passes(qa_engine, valid_lead):
    """PASS 8: 'solution' passes -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Outreach solution",
        body="Hi Sandeep,\n\nOur solution supports AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_09_leverage_passes(qa_engine, valid_lead):
    """PASS 9: 'leverage' passes -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Leverage data",
        body="Hi Sandeep,\n\nLeverage existing tools at AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_10_exclamation_mark_passes(qa_engine, valid_lead):
    """PASS 10: Exclamation mark passes -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Great news!",
        body="Hi Sandeep!\n\nExciting progress for AcmeMinds Private Limited in 2025!\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_11_em_dash_passes(qa_engine, valid_lead):
    """PASS 11: Em dash passes -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds — Roadmap",
        body="Hi Sandeep,\n\nAcmeMinds Private Limited — expanding rapidly in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "PASS"


def test_pass_12_followup_a_legitimate_re_passes(qa_engine, valid_lead):
    """PASS 12: Follow-up A with legitimate Re: passes -> PASS"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds outreach",
        body="Hi Sandeep,\n\nRegarding AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    fa = EmailGenerationResult(
        email_type="FOLLOWUP_A",
        subject="Re: AcmeMinds outreach",
        body="Hi Sandeep,\n\nFollowing up for AcmeMinds Private Limited.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=18,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1, fa)
    assert res.qa_status == "PASS"


# ==============================================================================
# FAIL TEST CASES (13 - 30)
# ==============================================================================

def test_fail_13_missing_first_name(qa_engine, valid_lead):
    """FAIL 13: Missing first name -> FAIL"""
    bad_lead = valid_lead.model_copy(update={"contact_name": ""})
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds note",
        body="Hello,\n\nRegarding AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=18,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(bad_lead, e1)
    assert res.qa_status == "FAIL"
    assert "VARIABLES_GATE_FIRST_NAME" in res.checks_failed


def test_fail_14_missing_company(qa_engine, valid_lead):
    """FAIL 14: Missing company -> FAIL"""
    bad_lead = valid_lead.model_copy(update={"company_name": ""})
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Outreach note",
        body="Hi Sandeep,\n\nWe provide software tools.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=18,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(bad_lead, e1)
    assert res.qa_status == "FAIL"
    assert "VARIABLES_GATE_COMPANY" in res.checks_failed


def test_fail_15_wrong_recipient_name(qa_engine, valid_lead):
    """FAIL 15: Wrong recipient name addressed -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds growth",
        body="Hi Sarah,\n\nSaw AcmeMinds Private Limited expanding in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "RECIPIENT_NAME_MATCH" in res.checks_failed


def test_fail_16_hi_there(qa_engine, valid_lead):
    """FAIL 16: 'Hi there' greeting -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds note",
        body="Hi there,\n\nRegarding AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=19,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "NO_HI_THERE" in res.checks_failed


def test_fail_17_unresolved_variable(qa_engine, valid_lead):
    """FAIL 17: Unresolved {{variable}} -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Hello {{first_name}}",
        body="Hi Sandeep,\n\nHope all is well at {{company}} in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=22,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "VARIABLES_RESOLVED" in res.checks_failed


def test_fail_18_invented_date_year(qa_engine, valid_lead):
    """FAIL 18: Invented date/year -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds plans",
        body="Hi Sandeep,\n\nIn 2029 AcmeMinds Private Limited will double headcount.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=21,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "NO_INVENTED_DATES" in res.checks_failed


def test_fail_19_fabricated_financial_metric(qa_engine, valid_lead):
    """FAIL 19: Fabricated financial metric -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds savings",
        body="Hi Sandeep,\n\nWe saved $500K for AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=22,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "NO_FABRICATED_METRICS" in res.checks_failed


def test_fail_20_fabricated_partnership(qa_engine, valid_lead):
    """FAIL 20: Fabricated partnership -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds partnership",
        body="Hi Sandeep,\n\nWe partnered with Microsoft Corporation for AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=24,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "NO_FABRICATED_PARTNERSHIPS" in res.checks_failed


def test_fail_21_unsupported_announcement(qa_engine, valid_lead):
    """FAIL 21: Unsupported announcement/congratulation claim on NO_STRONG_SIGNAL lead -> FAIL"""
    no_sig_lead = valid_lead.model_copy(update={"personalization_note_status": PersonalizationNoteStatus.NO_STRONG_SIGNAL})
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds update",
        body="Hi Sandeep,\n\nSaw your recent announcement about expanding AcmeMinds Private Limited.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=22,
        personalization_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL
    )
    res = qa_engine.validate_lead_drafts(no_sig_lead, e1)
    assert res.qa_status == "FAIL"
    assert "PERSONALIZATION_MATCHES_EVIDENCE" in res.checks_failed


def test_fail_22_wrong_icp_leakage(qa_engine, valid_lead):
    """FAIL 22: Wrong-ICP leakage (construction in software lead) -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds project",
        body="Hi Sandeep,\n\nWe handle pre-construction document control and site manpower tracking for AcmeMinds Private Limited.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=25,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "NO_CONSTRUCTION_LEAKAGE" in res.checks_failed


def test_fail_23_internal_system_status_leakage(qa_engine, valid_lead):
    """FAIL 23: Internal system status leakage -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds status",
        body="Hi Sandeep,\n\nGiven your NO_STRONG_SIGNAL status at AcmeMinds Private Limited.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=22,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "NO_INTERNAL_SYSTEM_LEAKS" in res.checks_failed


def test_fail_24_missing_signature(qa_engine, valid_lead):
    """FAIL 24: Missing required signature -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds note",
        body="Hi Sandeep,\n\nRegarding AcmeMinds Private Limited expansion in 2025.\n\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=16,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert any("SIGNATURE_PRESENT" in c for c in res.checks_failed)


def test_fail_25_missing_unsubscribe_mechanism(qa_engine, valid_lead):
    """FAIL 25: Missing unsubscribe mechanism -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds tech",
        body="Hi Sandeep,\n\nSaw AcmeMinds Private Limited expansion in 2025.\n\nBest regards,\nAlex Mitchell",
        word_count=16,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert any("UNSUBSCRIBE_PRESENT" in c for c in res.checks_failed)


def test_fail_26_unsubscribe_word_without_usable_mechanism(qa_engine, valid_lead):
    """FAIL 26: 'unsubscribe' mentioned without an actual usable mechanism -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="AcmeMinds update",
        body="Hi Sandeep,\n\nSaw AcmeMinds Private Limited expanding in 2025. Our system supports unsubscribe management in all workflows.\n\nBest regards,\nAlex Mitchell",
        word_count=24,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert any("UNSUBSCRIBE_PRESENT" in c for c in res.checks_failed)


def test_fail_27_fake_re_on_email_1(qa_engine, valid_lead):
    """FAIL 27: Fake Re: on Email 1 -> FAIL"""
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Re: AcmeMinds outreach",
        body="Hi Sandeep,\n\nRegarding AcmeMinds Private Limited in 2025.\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "NO_FAKE_RE_EMAIL_1" in res.checks_failed


def test_fail_28_excessive_email_length(qa_engine, valid_lead):
    """FAIL 28: Excessive email length (>90 words) -> FAIL"""
    long_body = "word " * 105
    e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Too long",
        body=f"Hi Sandeep,\n\nRegarding AcmeMinds Private Limited in 2025. {long_body}\n\nBest regards,\nAlex Mitchell\nTo unsubscribe, click here: https://aedrix.com/unsubscribe",
        word_count=115,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa_engine.validate_lead_drafts(valid_lead, e1)
    assert res.qa_status == "FAIL"
    assert "WORD_COUNT_EMAIL_1" in res.checks_failed


def test_fail_29_approval_engine_blocks_qa_failure():
    """FAIL 29: ApprovalEngine blocks a QA failure -> BLOCKED"""
    tmp_dir = tempfile.mkdtemp()
    store_file = os.path.join(tmp_dir, "test_approval_store.json")
    store = ApprovalStore(storage_path=store_file)
    engine = ApprovalEngine(store=store)

    rec = engine.enroll_draft(
        company="AcmeMinds",
        contact="Sandeep Mehra",
        title="Managing Director",
        email="sandeep@acmeminds.com",
        qualification_status="QUALIFIED",
        opportunity_score=85.0,
        accessibility_score=90.0,
        outreach_priority_index=87.0,
        priority="P1",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Expanding in 2025",
        voc_angle="growth",
        email_1="Bad draft",
        followup_a="",
        followup_b="",
        qa_status="FAIL",
        qa_reasons=["Personalization QA failed: Unsubscribe mechanism missing"]
    )
    assert rec.approval_status.value == "BLOCKED"
    assert rec.smartlead_eligible is False

    with pytest.raises(ValueError, match="Cannot approve delivery-blocked lead"):
        engine.approve(rec.lead_id)


def test_fail_30_approval_engine_blocks_invalid_bounced_suppressed_recipients():
    """FAIL 30: ApprovalEngine blocks invalid / bounced / suppressed recipients -> BLOCKED"""
    tmp_dir = tempfile.mkdtemp()
    store_file = os.path.join(tmp_dir, "test_approval_store2.json")
    store = ApprovalStore(storage_path=store_file)
    engine = ApprovalEngine(store=store)

    # Inconsistent/invalid syntax email
    rec = engine.enroll_draft(
        company="AcmeMinds",
        contact="Sandeep Mehra",
        title="Managing Director",
        email="invalid_email_at_acmeminds",
        qualification_status="QUALIFIED",
        opportunity_score=85.0,
        accessibility_score=90.0,
        outreach_priority_index=87.0,
        priority="P1",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Expanding in 2025",
        voc_angle="growth",
        email_1="Valid text",
        followup_a="",
        followup_b="",
        qa_status="PASS",
        qa_reasons=[]
    )
    assert rec.approval_status.value == "BLOCKED"
    assert "syntactically invalid" in rec.blocked_reason
