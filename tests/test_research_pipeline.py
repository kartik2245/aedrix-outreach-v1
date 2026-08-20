"""
test_research_pipeline.py
Pytest unit tests for Research Ingestion Pipeline (Python 3.12).
"""

import json
import os
import pytest
from src.research_pipeline import ResearchPipeline
from src.models import EvidenceLevel, DisqualificationStatus, PersonalizationNoteStatus


@pytest.fixture
def pipeline():
    return ResearchPipeline()


def test_normal_valid_record(pipeline):
    record = {
        "company_name": "Bowmer & Kirkland",
        "company_domain": "bandk.co.uk",
        "is_uk_operating": True,
        "is_construction_sector": True,
        "contact_name": "John Foster",
        "job_title": "Business Improvement Director",
        "email": "j.foster@bandk.co.uk",
        "relevant_signal": "Published sustainability & digital strategy overview",
        "relevant_signal_evidence": "VERIFIED",
        "research_sources": ["https://bandk.co.uk/news/digital-strategy"]
    }
    result = pipeline.process_dataset([record])[0]
    assert result.relevant_signal_evidence == EvidenceLevel.VERIFIED


def test_missing_evidence_handling(pipeline):
    record = {
        "company_name": "Test Builders",
        "company_domain": "testbuilders.co.uk",
        "contact_name": "Bob Builder",
        "job_title": "Director",
        "email": "bob@testbuilders.co.uk"
    }
    norm = pipeline.normalizer.normalize_record(record)
    assert norm["relevant_signal_evidence"] == EvidenceLevel.UNKNOWN
    assert norm["company_size_evidence"] == EvidenceLevel.ESTIMATED


def test_unknown_evidence_preservation(pipeline):
    record = {
        "company_name": "Morgan Sindall",
        "company_domain": "morgansindall.com",
        "contact_name": "Lee Ramsey",
        "job_title": "Director",
        "email": "l.ramsey@morgansindall.com",
        "relevant_signal": "NO_STRONG_SIGNAL",
        "relevant_signal_evidence": "UNKNOWN"
    }
    result = pipeline.process_dataset([record])[0]
    assert result.personalization_note_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL
    assert result.relevant_signal_evidence == EvidenceLevel.UNKNOWN


def test_inferred_evidence_preservation(pipeline):
    record = {
        "company_name": "Laing O'Rourke",
        "company_domain": "laingorourke.com",
        "contact_name": "Adrian Spragg",
        "job_title": "Head of Digital",
        "email": "a.spragg@laingorourke.com",
        "pain_point": "High subcontractor coordination overhead",
        "pain_point_evidence": "INFERRED"
    }
    result = pipeline.process_dataset([record])[0]
    assert result.pain_point_evidence == EvidenceLevel.INFERRED


def test_unsupported_claim_downgrade(pipeline):
    record = {
        "company_name": "Balfour Beatty",
        "company_domain": "balfourbeatty.com",
        "contact_name": "Jon Ozanne",
        "job_title": "CIO",
        "email": "j.ozanne@balfourbeatty.com",
        "relevant_signal": "Claims AI transformation launch without proof",
        "relevant_signal_evidence": "VERIFIED",
        "research_sources": []
    }
    result = pipeline.process_dataset([record])[0]
    assert result.relevant_signal_evidence == EvidenceLevel.INFERRED


def test_no_strong_signal_fallback(pipeline):
    record = {
        "company_name": "Morgan Sindall Group plc",
        "company_domain": "morgansindall.com",
        "contact_name": "Lee Ramsey",
        "job_title": "BIM Director",
        "email": "l.ramsey@morgansindall.com",
        "relevant_signal": "NO_STRONG_SIGNAL"
    }
    result = pipeline.process_dataset([record])[0]
    assert result.personalization_note_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL
    assert "Given your role leading operations" in result.personalization_note


def test_qualified_lead_pipeline_execution(pipeline):
    record = {
        "company_name": "Bowmer & Kirkland (B&K)",
        "company_domain": "bandk.co.uk",
        "country": "UK",
        "is_uk_operating": True,
        "industry": "Commercial Construction",
        "is_construction_sector": True,
        "company_size": "1,500 employees",
        "employee_count": 1500,
        "contact_name": "John Foster",
        "job_title": "Business Improvement Director",
        "email": "j.foster@bandk.co.uk",
        "relevant_signal": "DigitALL initiative for site document control",
        "relevant_signal_evidence": "VERIFIED",
        "research_sources": ["https://bandk.co.uk/news"]
    }
    result = pipeline.process_dataset([record])[0]
    assert result.disqualification_status == DisqualificationStatus.QUALIFIED
    assert result.opportunity_score >= 70
    assert result.personalization_note_status == PersonalizationNoteStatus.SIGNAL_VERIFIED


def test_campaign_excluded_lead_execution(pipeline):
    record = {
        "company_name": "Kier Group plc",
        "company_domain": "kier.co.uk",
        "contact_name": "Colin Bell",
        "job_title": "Digital Director",
        "email": "c.bell@kier.co.uk",
        "is_uk_operating": True,
        "is_active_crm_deal": True
    }
    result = pipeline.process_dataset([record])[0]
    assert result.disqualification_status == DisqualificationStatus.CAMPAIGN_EXCLUDED
    assert result.opportunity_score > 0


def test_hard_disqualified_lead_execution(pipeline):
    record = {
        "company_name": "US Non-Const Firm",
        "company_domain": "usfirm.com",
        "contact_name": "John Doe",
        "job_title": "CEO",
        "email": "jdoe@usfirm.com",
        "country": "USA",
        "is_uk_operating": False
    }
    result = pipeline.process_dataset([record])[0]
    assert result.disqualification_status == DisqualificationStatus.HARD_DISQUALIFIED
    assert result.opportunity_score == 0


def test_full_5_pilot_leads_processing(pipeline):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    export_path = os.path.join(base_dir, "data", "deepline_export_sample.json")
    buffer_path = os.path.join(base_dir, "data", "research_leads.json")
    final_output_path = os.path.join(base_dir, "data", "final_lead_intelligence.json")

    results = pipeline.run_and_save(export_path, buffer_path, final_output_path)
    assert len(results) == 5
    assert os.path.exists(final_output_path)
