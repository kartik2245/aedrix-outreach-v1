"""
test_voc_and_qa.py
Unit tests for Voice-of-Customer (VoC) Engine and Personalization QA Layer in Aedrix Cold Outreach System.
Covers Test Cases:
D. Missing Evidence
E. NO_STRONG_SIGNAL Fallback
I. Personalization QA Pass
J. Personalization QA Failure
K. Email Word Limits
L. No Fabricated Facts
"""

import pytest
from src.personalization.voc_engine import VoCEngine
from src.personalization.personalization_qa import PersonalizationQA
from src.evidence_validator import EvidenceValidator
from src.email_generator import EmailGenerator
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
def voc_engine():
    return VoCEngine()


@pytest.fixture
def qa_engine():
    return PersonalizationQA()


@pytest.fixture
def evidence_validator():
    return EvidenceValidator()


@pytest.fixture
def valid_lead():
    return LeadIntelligenceOutput(
        company_name="Bowmer & Kirkland (B&K)",
        company_domain="bandk.co.uk",
        contact_name="John Foster",
        job_title="Business Improvement Director",
        email="j.foster@bandk.co.uk",
        email_status=EmailStatus.PATTERN_CONFIRMED,
        company_size="1,500+ employees",
        company_size_evidence=EvidenceLevel.ESTIMATED,
        industry="Commercial Construction",
        opportunity_score=92.0,
        accessibility_score=84.0,
        outreach_priority_index=88.8,
        priority_level=PriorityLevel.P1,
        opportunity_tier="Tier 1 — Mid-Market High Intent",
        accessibility_tier=AccessibilityTier.HIGH,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
        personalization_note="Saw Bowmer & Kirkland's recent initiative expanding their digital construction team to 12 members. Aedrix delivers a fast-to-deploy cloud platform.",
        research_sources=["https://www.bandk.co.uk/news/2025"],
        ICP_score=92.0,
        pain_point="Managing subcontractor document versions across regional sites.",
        pain_point_evidence=EvidenceLevel.INFERRED,
        relevant_signal="expanded digital construction team to 12 members in October 2025",
        relevant_signal_evidence=EvidenceLevel.VERIFIED,
        persona_selection_rationale="Selected Business Improvement Director for direct budget authority."
    )


# --- Test Case D: Missing Evidence ---

def test_d_missing_evidence_downgrades_to_inferred(evidence_validator):
    """Test D: Claim marked VERIFIED without research sources is downgraded."""
    record = {
        "company_name": "Test Builder Ltd",
        "company_domain": "testbuilder.co.uk",
        "relevant_signal": "Claiming huge new contract without links",
        "relevant_signal_evidence": EvidenceLevel.VERIFIED,
        "company_size": "500 employees",
        "company_size_evidence": EvidenceLevel.VERIFIED,
        "research_sources": []  # Empty sources
    }
    validated = evidence_validator.validate_record(record)
    assert validated["relevant_signal_evidence"] == EvidenceLevel.INFERRED
    assert validated["company_size_evidence"] == EvidenceLevel.ESTIMATED
    assert len(validated["validation_audit"]["warnings"]) >= 2


# --- Test Case E: NO_STRONG_SIGNAL Fallback ---

def test_e_no_strong_signal_uses_baseline_value_prop(voc_engine):
    """Test E: Missing or weak signal falls back cleanly to baseline Aedrix value proposition."""
    lead = {
        "company_name": "Generic Construction Ltd",
        "job_title": "Operations Director",
        "relevant_signal": "NO_STRONG_SIGNAL",
        "relevant_signal_evidence": EvidenceLevel.UNKNOWN,
        "personalization_note_status": PersonalizationNoteStatus.NO_STRONG_SIGNAL
    }
    voc_ctx = voc_engine.map_lead_voc(lead)
    assert voc_ctx.personalization_note_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL
    assert "Given your role leading operations across UK building projects" in voc_ctx.personalization_note
    assert "unifies pre-construction document control" in voc_ctx.aedrix_value_prop


# --- Test Case I: Personalization QA Pass ---

def test_i_personalization_qa_pass_on_valid_sequence(qa_engine, valid_lead):
    """Test I: Compliant email sequence passes all 10 QA checks."""
    email_1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="superseded drawings on site?",
        body=(
            "Hi John,\n\n"
            "Saw Bowmer & Kirkland's recent initiative expanding their digital construction team to 12 members.\n\n"
            "Aedrix unifies pre-construction document control directly with real-time site manpower tracking "
            "so your operational teams operate from a single source of truth.\n\n"
            "Are you open to a brief 2-minute overview this week?\n\nBest regards,\nAedrix Team\nTo unsubscribe click here"
        ),
        word_count=52,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    followup_a = EmailGenerationResult(
        email_type="FOLLOWUP_A",
        subject="Re: superseded drawings on site?",
        body=(
            "Hi John,\n\n"
            "Following up on my previous note regarding pre-construction document control for Bowmer & Kirkland.\n\n"
            "Given your operational focus, Aedrix specifically reduces document versioning errors across multi-site teams.\n\n"
            "Would Thursday afternoon work for a quick conversation?\n\nBest regards,\nAedrix Team\nTo unsubscribe click here"
        ),
        word_count=42,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    followup_b = EmailGenerationResult(
        email_type="FOLLOWUP_B",
        subject="rework from wrong revision",
        body=(
            "Hi John,\n\n"
            "Pivoting from my earlier message, many contractors face challenges reconciling estimates against live site manpower.\n\n"
            "Aedrix gives leadership real-time labor productivity visibility without complex IT overhauls.\n\n"
            "Open to exploring how this fits your digital roadmap?\n\nBest regards,\nAedrix Team\nTo unsubscribe click here"
        ),
        word_count=39,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )

    qa_res = qa_engine.validate_lead_drafts(valid_lead, email_1, followup_a, followup_b)
    assert qa_res.qa_status == "PASS"
    assert len(qa_res.qa_reasons) == 0
    assert "WORD_COUNT_EMAIL_1" in qa_res.checks_passed
    assert "NO_INVENTED_DATES" in qa_res.checks_passed


# --- Test Case J: Personalization QA Failure ---

def test_j_personalization_qa_failure_on_hallucinated_year_and_partner(qa_engine, valid_lead):
    """Test J: QA fails when draft invents dates or unverified partnerships."""
    hallucinated_e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Construction Tech",
        body=(
            "Hi John,\n\n"
            "In 2029 your company will face huge challenges. We partnered with MegaCorp International "
            "to save £500M on construction document control.\n\n"
            "Are you open to a call?\n\nBest,\nAedrix\nTo unsubscribe click here"
        ),
        word_count=28,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    qa_res = qa_engine.validate_lead_drafts(valid_lead, hallucinated_e1)
    assert qa_res.qa_status == "FAIL"
    assert any("Invented date/year '2029'" in r for r in qa_res.qa_reasons)
    assert any("Fabricated partnership" in r or "Fabricated financial metric" in r for r in qa_res.qa_reasons)


# --- Test Case K: Email Word Limits ---

def test_k_email_word_limits_enforced(qa_engine, valid_lead):
    """Test K: Over-length emails are strictly flagged by QA."""
    long_body = "word " * 130  # 130 words exceeds 120 limit
    overlong_e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Too Long",
        body=long_body + "\n\nBest,\nAedrix\nTo unsubscribe click here",
        word_count=130,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    qa_res = qa_engine.validate_lead_drafts(valid_lead, overlong_e1)
    assert qa_res.qa_status == "FAIL"
    assert any("Email 1 exceeds limit" in r for r in qa_res.qa_reasons)


# --- Test Case L: No Fabricated Facts ---

def test_l_no_fabricated_personalization_on_no_signal_lead(qa_engine, valid_lead):
    """Test L: QA fails if fake personalization is manufactured for a NO_STRONG_SIGNAL lead."""
    no_sig_lead = valid_lead.model_copy(update={
        "personalization_note_status": PersonalizationNoteStatus.NO_STRONG_SIGNAL,
        "relevant_signal": "NO_STRONG_SIGNAL"
    })
    fake_personalized_e1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Pre-construction document control",
        body="Hi John,\n\nSaw your recent announcement about acquiring 50 new cranes.\n\nAedrix provides document control for site teams.\n\nBest,\nAedrix\nTo unsubscribe click here",
        word_count=22,
        personalization_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL
    )
    qa_res = qa_engine.validate_lead_drafts(no_sig_lead, fake_personalized_e1)
    assert qa_res.qa_status == "FAIL"
    assert any("Fabricated personalization note" in r for r in qa_res.qa_reasons)
