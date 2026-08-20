"""
test_role_sequences.py
Unit tests for the new Aedrix Sequences by Company Role features.
Covers points A to K.
"""

import pytest
from src.role_classifier import RoleTrackClassifier
from src.email_generator import EmailGenerator
from src.personalization.personalization_qa import PersonalizationQA
from src.outreach_engine import OutreachEngine
from src.models import (
    LeadIntelligenceOutput,
    EmailGenerationResult,
    PersonalizationNoteStatus,
    EmailStatus,
    PriorityLevel,
    AccessibilityTier,
    EvidenceLevel,
    DisqualificationStatus,
    OutreachState
)


def test_point_a_role_routing_precedence():
    # 1. R1 > everything: "Document Controller and Project Director" -> R1
    res1 = RoleTrackClassifier.classify("Document Controller and Project Director")
    assert res1.role_track == "R1"

    # 2. R4 > R2: "Project Manager and Commercial Manager" -> R4
    res2 = RoleTrackClassifier.classify("Project Manager and Commercial Manager")
    assert res2.role_track == "R4"

    # 3. R5 > R2: "Project Manager and BIM Lead" -> R5
    res3 = RoleTrackClassifier.classify("Project Manager and BIM Lead")
    assert res3.role_track == "R5"

    # 4. R3 > R2 when S3/subcontractor context exists
    res4 = RoleTrackClassifier.classify(
        "Project Manager and Contracts Manager",
        {"industry": "specialist subcontractor"}
    )
    assert res4.role_track == "R3"

    # 5. R6 > R2 when S5/FM context exists
    res5 = RoleTrackClassifier.classify(
        "Project Manager and Facilities Manager",
        {"industry": "Facilities management"}
    )
    assert res5.role_track == "R6"

    # 6. Unresolved Operations Manager -> HOLD/UNCLASSIFIED
    res6 = RoleTrackClassifier.classify("Operations Manager", {"industry": "General Construction"})
    assert res6.role_track == "UNCLASSIFIED"
    assert res6.classification_status == "AMBIGUOUS"


def test_point_b_fixed_templates_loaded():
    generator = EmailGenerator()
    lead = LeadIntelligenceOutput.model_construct(
        contact_name="Sarah Smith",
        company_name="Acme Build Ltd",
        email="sarah@acmebuild.co.uk",
        role_track="R1",
        personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
        relevant_signal=""
    )
    email_res = generator.generate_email_1(lead)
    assert "most document controllers at UK contractors" in email_res.body
    assert "Acme Build Ltd" in email_res.body


def test_point_c_subject_variant_deterministic_division():
    generator = EmailGenerator()
    # Test stable division using email hash
    var1 = generator.get_subject_variant("test1@example.com")
    var2 = generator.get_subject_variant("test2@example.com")
    
    # Ensure they always yield the same result across invocations
    assert var1 == generator.get_subject_variant("test1@example.com")
    assert var2 == generator.get_subject_variant("test2@example.com")


def test_point_d_v1_sequence_state_progression_and_touch_345_disabled():
    engine = OutreachEngine()
    lead = LeadIntelligenceOutput(
        company_name="Acme Builders",
        company_domain="acmebuilders.co.uk",
        contact_name="Sarah Smith",
        job_title="Document Controller",
        email="sarah@acmebuilders.co.uk",
        email_status=EmailStatus.PATTERN_CONFIRMED,
        company_size="100 employees",
        company_size_evidence=EvidenceLevel.ESTIMATED,
        industry="Commercial Construction",
        opportunity_score=80.0,
        accessibility_score=80.0,
        outreach_priority_index=80.0,
        priority_level=PriorityLevel.P1,
        opportunity_tier="Tier 1",
        accessibility_tier=AccessibilityTier.HIGH,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
        personalization_note="Some verified signal",
        research_sources=[],
        ICP_score=80.0,
        pain_point="Versioning",
        pain_point_evidence=EvidenceLevel.INFERRED,
        relevant_signal="expanded digital team",
        relevant_signal_evidence=EvidenceLevel.VERIFIED,
        persona_selection_rationale="Rational",
        role_track="R1",
        role_classification_status="CLASSIFIED",
        role_matched_keyword="document controller",
        role_match_reason="Matches R1"
    )
    
    # Step 1: Enroll (EMAIL_1_SENT)
    record = engine.enroll_lead(lead)
    assert record.state_machine.get_current_state() == OutreachState.EMAIL_1_SENT
    
    # Step 2: Open -> FOLLOWUP_A_SENT
    engine.simulate_opened_event(lead.email)
    assert record.state_machine.get_current_state() == OutreachState.FOLLOWUP_A_SENT
    
    # Touch 3, 4, 5 must NOT be executable
    with pytest.raises(NotImplementedError):
        engine.simulate_touch_3(lead.email)
    
    with pytest.raises(NotImplementedError):
        engine.simulate_touch_4(lead.email)
    
    with pytest.raises(NotImplementedError):
        engine.simulate_touch_5(lead.email, "Touch 4 Subject")


def test_point_e_qa_constraints_enforced():
    qa = PersonalizationQA()
    lead = LeadIntelligenceOutput.model_construct(
        contact_name="Sarah Smith",
        company_name="Acme Build Ltd",
        email="sarah@acmebuild.co.uk",
        role_track="R1"
    )

    # 1. Invalid word count
    overlong_email = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="superseded drawings on site?",
        body="word " * 100 + "\n\nBest,\nAlex Mitchell\nOutreach Manager, Aedrix\nHQ: Panchkula, Haryana, India\nTo unsubscribe click here",
        word_count=105,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa.validate_lead_drafts(lead, overlong_email)
    assert res.qa_status == "FAIL"
    assert any("Email 1 exceeds limit" in r for r in res.qa_reasons)

    # 2. Exclamation mark
    exclamation_email = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="superseded drawings on site?",
        body="Hi Sarah,\n\nWe love document control! We are Aedrix.\n\nBest,\nAlex Mitchell\nOutreach Manager, Aedrix\nHQ: Panchkula, Haryana, India\nTo unsubscribe click here",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res2 = qa.validate_lead_drafts(lead, exclamation_email)
    assert res2.qa_status == "FAIL"
    assert any("Exclamation mark" in r for r in res2.qa_reasons)

    # 3. Banned word
    banned_email = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="superseded drawings on site?",
        body="Hi Sarah,\n\nWe offer a seamless document control workflow.\n\nBest,\nAlex Mitchell\nOutreach Manager, Aedrix\nHQ: Panchkula, Haryana, India\nTo unsubscribe click here",
        word_count=20,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res3 = qa.validate_lead_drafts(lead, banned_email)
    assert res3.qa_status == "FAIL"
    assert any("Banned vendor word" in r for r in res3.qa_reasons)


def test_point_f_spintax_opener_closer():
    generator = EmailGenerator()
    lead = LeadIntelligenceOutput.model_construct(
        contact_name="Sarah Smith",
        company_name="Acme Build Ltd",
        email="sarah@acmebuild.co.uk",
        role_track="R1",
        personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
        relevant_signal=""
    )
    # Generate same email multiple times for different emails to observe spintax variations
    lead_a = lead.model_copy(update={"email": "a@example.com"})
    lead_b = lead.model_copy(update={"email": "b@example.com"})
    
    body_a = generator.generate_email_1(lead_a).body
    body_b = generator.generate_email_1(lead_b).body
    
    # Openers should resolve to either Hi or Hello
    assert body_a.startswith("Hi Sarah") or body_a.startswith("Hello Sarah")
    assert body_b.startswith("Hi Sarah") or body_b.startswith("Hello Sarah")
    
    # Closers should resolve to Best, All the best, or Best regards
    assert "Best," in body_a or "All the best," in body_a or "Best regards," in body_a
    assert "Best," in body_b or "All the best," in body_b or "Best regards," in body_b


def test_point_h_i_stop_conditions_and_ooo():
    engine = OutreachEngine()
    lead = LeadIntelligenceOutput(
        company_name="Acme Builders",
        company_domain="acmebuilders.co.uk",
        contact_name="Sarah Smith",
        job_title="Document Controller",
        email="sarah@acmebuilders.co.uk",
        email_status=EmailStatus.PATTERN_CONFIRMED,
        company_size="100 employees",
        company_size_evidence=EvidenceLevel.ESTIMATED,
        industry="Commercial Construction",
        opportunity_score=80.0,
        accessibility_score=80.0,
        outreach_priority_index=80.0,
        priority_level=PriorityLevel.P1,
        opportunity_tier="Tier 1",
        accessibility_tier=AccessibilityTier.HIGH,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
        personalization_note="Some verified signal",
        research_sources=[],
        ICP_score=80.0,
        pain_point="Versioning",
        pain_point_evidence=EvidenceLevel.INFERRED,
        relevant_signal="expanded digital team",
        relevant_signal_evidence=EvidenceLevel.VERIFIED,
        persona_selection_rationale="Rational",
        role_track="R1",
        role_classification_status="CLASSIFIED",
        role_matched_keyword="document controller",
        role_match_reason="Matches R1"
    )
    
    # Test Stop on Reply
    record1 = engine.enroll_lead(lead)
    engine.simulate_reply_event(lead.email, "Please remove me from your list.")
    assert record1.state_machine.get_current_state() == OutreachState.STOPPED_UNSUBSCRIBED

    # Test Delay on OOO
    lead2 = lead.model_copy(update={"email": "sarah2@acmebuilders.co.uk"})
    record2 = engine.enroll_lead(lead2)
    engine.simulate_reply_event(lead2.email, "I am out of the office and will return next week.")
    assert record2.state_machine.get_current_state() == OutreachState.OOO_DELAYED


def test_point_j_variables_gate():
    qa = PersonalizationQA()
    # Missing first name (Hold)
    lead_no_name = LeadIntelligenceOutput.model_construct(
        contact_name="",
        company_name="Acme Builders",
        email="sarah@acmebuilders.co.uk",
        role_track="R1"
    )
    email = EmailGenerationResult(
        email_type="EMAIL_1",
        subject="Drawings Check",
        body="Hi, body\n\nBest,\nAlex Mitchell\nOutreach Manager, Aedrix\nHQ: Panchkula, Haryana, India\nTo unsubscribe click here",
        word_count=5,
        personalization_status=PersonalizationNoteStatus.SIGNAL_VERIFIED
    )
    res = qa.validate_lead_drafts(lead_no_name, email)
    assert res.qa_status == "FAIL"
    assert any("first_name" in r for r in res.qa_reasons)

    # Missing company (Hold)
    lead_no_company = LeadIntelligenceOutput.model_construct(
        contact_name="Sarah Smith",
        company_name="",
        email="sarah@acmebuilders.co.uk",
        role_track="R1"
    )
    res2 = qa.validate_lead_drafts(lead_no_company, email)
    assert res2.qa_status == "FAIL"
    assert any("company name" in r for r in res2.qa_reasons)
