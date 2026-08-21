"""
test_personalization_cleanliness.py
Regression tests for zero internal system placeholder / label leaks in generated email copy.

Verifies:
  1. NO_STRONG_SIGNAL never appears in generated customer-facing copy.
  2. SIGNAL_VERIFIED and internal status codes never appear in customer-facing copy.
  3. A lead without a strong verified signal produces natural, professional copy.
  4. Existing verified signals continue to be rendered correctly.
  5. PersonalizationQA fails if any internal system placeholder leaks into email copy.
  6. BedrockClient prompt JSON never passes raw internal status enum codes to LLM.
"""

import pytest
from src.models import (
    LeadIntelligenceOutput,
    DisqualificationStatus,
    EmailStatus,
    PriorityLevel,
    AccessibilityTier,
    PersonalizationNoteStatus,
    EvidenceLevel,
    EmailGenerationResult,
)
from src.lead_intelligence import LeadIntelligenceEngine
from src.personalization.voc_engine import VoCEngine
from src.integrations.bedrock_client import BedrockClient
from src.personalization.personalization_qa import PersonalizationQA


def test_1_no_strong_signal_never_appears_in_offline_generated_copy():
    """Verifies offline generator produces clean copy without NO_STRONG_SIGNAL string."""
    engine = LeadIntelligenceEngine()
    voc_engine = VoCEngine()
    client = BedrockClient(dry_run=True)

    raw_lead = {
        "company_name": "Barkers Security Engineering",
        "company_domain": "barkersfencing.com",
        "company_location": "United Kingdom",
        "country": "United Kingdom",
        "is_uk_operating": True,
        "industry": "Commercial Construction",
        "is_construction_sector": True,
        "company_size": "85 employees",
        "employee_count": 85,
        "contact_name": "Sarah Lawton Clewlow",
        "job_title": "Operations Director",
        "email": "s.clewlow@barkersfencing.com",
        "email_status": "PATTERN_CONFIRMED",
        "relevant_signal": "NO_STRONG_SIGNAL",
    }

    lead_intel = engine.process_lead(raw_lead)
    voc_ctx = voc_engine.map_lead_voc(lead_intel)

    result = client.generate_email_1(lead_intel, voc_ctx)

    assert "NO_STRONG_SIGNAL" not in result.body, "NO_STRONG_SIGNAL must not appear in email body"
    assert "NO_STRONG_SIGNAL" not in result.subject, "NO_STRONG_SIGNAL must not appear in email subject"
    assert "SIGNAL_VERIFIED" not in result.body, "SIGNAL_VERIFIED must not appear in email body"
    assert "QUALIFIED" not in result.body, "QUALIFIED must not appear in email body"
    assert "P2" not in result.body, "Internal priority P2 must not appear in email body"
    assert len(result.body.split()) <= 120, "Word count must be under 120 words"
    assert "Aedrix" in result.body, "Must contain company name"


def test_2_bedrock_prompt_sanitizes_internal_status_codes():
    """Verifies that Bedrock prompt builder sanitizes NO_STRONG_SIGNAL out of JSON prompt."""
    engine = LeadIntelligenceEngine()
    voc_engine = VoCEngine()
    client = BedrockClient(dry_run=True)

    raw_lead = {
        "company_name": "Skanska UK",
        "company_domain": "skanska.co.uk",
        "company_location": "United Kingdom",
        "country": "United Kingdom",
        "is_uk_operating": True,
        "industry": "Commercial Construction",
        "is_construction_sector": True,
        "company_size": "500 employees",
        "employee_count": 500,
        "contact_name": "John Smith",
        "job_title": "Digital Director",
        "email": "j.smith@skanska.co.uk",
        "email_status": "PATTERN_CONFIRMED",
        "relevant_signal": "NO_STRONG_SIGNAL",
    }

    lead_intel = engine.process_lead(raw_lead)
    voc_ctx = voc_engine.map_lead_voc(lead_intel)

    prompt = client._build_email_1_prompt(lead_intel, voc_ctx)
    user_prompt = prompt["user"]

    assert "NO_STRONG_SIGNAL" not in user_prompt, "JSON prompt must sanitize NO_STRONG_SIGNAL out of prompt text"
    assert "SIGNAL_VERIFIED" not in user_prompt, "JSON prompt must not contain internal status enum strings"


def test_3_qa_engine_fails_on_internal_system_leak():
    """Verifies PersonalizationQA fails QA if forbidden internal terms appear in email copy."""
    engine = LeadIntelligenceEngine()
    qa = PersonalizationQA()

    raw_lead = {
        "company_name": "Test Company",
        "company_domain": "test.com",
        "company_location": "United Kingdom",
        "country": "United Kingdom",
        "is_uk_operating": True,
        "industry": "Commercial Construction",
        "is_construction_sector": True,
        "company_size": "100 employees",
        "employee_count": 100,
        "contact_name": "Jane Doe",
        "job_title": "Operations Director",
        "email": "jane@test.com",
        "email_status": "PATTERN_CONFIRMED",
        "relevant_signal": "NO_STRONG_SIGNAL",
    }

    lead_intel = engine.process_lead(raw_lead)

    leaked_email_1 = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Overview for Test Company",
        body="Hi Jane, Given your NO_STRONG_SIGNAL status we wanted to reach out.",
        word_count=12,
        personalization_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL,
        evidence_used=["Baseline"],
        generation_mode="TEST"
    )
    clean_followup = EmailGenerationResult(
        email_type="FOLLOWUP_A",
        subject="Re: Overview",
        body="Following up on my previous note.",
        word_count=6,
        personalization_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL,
        evidence_used=["Baseline"],
        generation_mode="TEST"
    )

    res = qa.validate_lead_drafts(lead_intel, leaked_email_1, clean_followup, clean_followup)

    assert res.qa_status == "FAIL", "QA must fail when internal system string leaks into copy"
    assert "NO_INTERNAL_SYSTEM_LEAKS" in res.checks_failed, "Check NO_INTERNAL_SYSTEM_LEAKS must be recorded as failed"


def test_4_verified_signal_rendered_correctly():
    """Verifies that leads with strong verified signals continue to render personalized copy cleanly."""
    engine = LeadIntelligenceEngine()
    client = BedrockClient(dry_run=True)

    raw_lead = {
        "company_name": "Balfour Beatty UK",
        "company_domain": "balfourbeatty.com",
        "company_location": "United Kingdom",
        "country": "United Kingdom",
        "is_uk_operating": True,
        "industry": "Commercial Construction",
        "is_construction_sector": True,
        "company_size": "1000 employees",
        "employee_count": 1000,
        "contact_name": "Mark Taylor",
        "job_title": "Head of BIM",
        "email": "m.taylor@balfourbeatty.com",
        "email_status": "PATTERN_CONFIRMED",
        "relevant_signal": "BIM Level 2 Enterprise Adoption",
        "relevant_signal_evidence": EvidenceLevel.VERIFIED,
        "personalization_note": "Saw Balfour Beatty UK's recent expansion in BIM Level 2 Enterprise Adoption.",
    }

    lead_intel = engine.process_lead(raw_lead)
    res = client.generate_email_1(lead_intel, None)

    assert "BIM Level 2 Enterprise Adoption" in res.body or "BIM" in res.body, "Verified signal must be included"
    assert "NO_STRONG_SIGNAL" not in res.body
    assert "SIGNAL_VERIFIED" not in res.body


def test_5_parser_strips_model_hallucinated_internal_placeholders():
    """Verifies parse_json_response strips out internal placeholder codes if returned by model."""
    client = BedrockClient(dry_run=True)
    raw_model_json = '{"subject": "Aedrix for Barkers NO_STRONG_SIGNAL", "body": "Hi Sarah, regarding your NO_STRONG_SIGNAL project and SIGNAL_VERIFIED roadmap."}'

    parsed = client.parse_json_response(raw_model_json)

    assert "NO_STRONG_SIGNAL" not in parsed["subject"]
    assert "NO_STRONG_SIGNAL" not in parsed["body"]
    assert "SIGNAL_VERIFIED" not in parsed["body"]
    assert parsed["subject"] == "Aedrix for Barkers"
    assert "Hi Sarah, regarding your project and roadmap." in parsed["body"]
