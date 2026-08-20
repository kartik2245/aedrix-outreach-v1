"""
test_deepline_export_adapter.py
Pytest unit tests for Deepline Export Adapter (Python 3.12).
"""

import json
import os
import pytest
from src.deepline_export_adapter import DeeplineExportAdapter
from src.models import EvidenceLevel, EmailStatus


@pytest.fixture
def adapter():
    return DeeplineExportAdapter()


def test_valid_record_adaptation(adapter):
    raw = {
        "company_name": "Bowmer & Kirkland (B&K)",
        "company_domain": "https://www.bandk.co.uk",
        "company_location": "United Kingdom",
        "industry": "Commercial Construction",
        "company_size": "1,500 employees",
        "contact_name": "John Foster",
        "job_title": "Business Improvement Director",
        "email": "j.foster@bandk.co.uk",
        "email_status": "PATTERN_CONFIRMED",
        "research_signals": ["DigitALL initiative"],
        "evidence_levels": {"signal": "VERIFIED"},
        "research_sources": ["https://bandk.co.uk/news"]
    }
    adapted = adapter.adapt_record(raw)
    assert adapted["company_name"] == "Bowmer & Kirkland (B&K)"
    assert adapted["company_domain"] == "bandk.co.uk"
    assert adapted["relevant_signal_evidence"] == EvidenceLevel.VERIFIED
    assert adapted["adapter_audit"]["is_valid"] is True


def test_missing_company_domain_handling(adapter):
    raw = {
        "company_name": "No Domain Construction Ltd",
        "company_location": "UK",
        "contact_name": "John Smith",
        "job_title": "Director",
        "email": "jsmith@nodomain.co.uk"
    }
    adapted = adapter.adapt_record(raw)
    assert adapted["company_domain"] == "unknown.com"
    assert any("MISSING_COMPANY_DOMAIN" in w for w in adapted["adapter_audit"]["warnings"])


def test_missing_evidence_defaults(adapter):
    raw = {
        "company_name": "Kier Group plc",
        "contact_name": "Colin Bell",
        "job_title": "Digital Director",
        "email": "c.bell@kier.co.uk"
    }
    adapted = adapter.adapt_record(raw)
    assert adapted["company_size_evidence"] == EvidenceLevel.ESTIMATED
    assert adapted["relevant_signal_evidence"] == EvidenceLevel.UNKNOWN


def test_unknown_evidence_preservation(adapter):
    raw = {
        "company_name": "Morgan Sindall",
        "contact_name": "Lee Ramsey",
        "job_title": "BIM Director",
        "email": "l.ramsey@morgansindall.com",
        "relevant_signal": "NO_STRONG_SIGNAL",
        "evidence_levels": {"signal": "UNKNOWN"}
    }
    adapted = adapter.adapt_record(raw)
    assert adapted["relevant_signal"] == "NO_STRONG_SIGNAL"
    assert adapted["relevant_signal_evidence"] == EvidenceLevel.UNKNOWN


def test_inferred_evidence_preservation(adapter):
    raw = {
        "company_name": "Laing O'Rourke",
        "contact_name": "Adrian Spragg",
        "job_title": "Head of Digital",
        "email": "a.spragg@laingorourke.com",
        "pain_point": "High subcontractor coordination friction",
        "evidence_levels": {"pain_point": "INFERRED"}
    }
    adapted = adapter.adapt_record(raw)
    assert adapted["pain_point_evidence"] == EvidenceLevel.INFERRED


def test_unsupported_verified_claim_downgrade(adapter):
    raw = {
        "company_name": "Balfour Beatty",
        "contact_name": "Jon Ozanne",
        "job_title": "CIO",
        "email": "j.ozanne@balfourbeatty.com",
        "relevant_signal": "Claimed AI strategy without URL",
        "evidence_levels": {"signal": "VERIFIED"},
        "research_sources": []
    }
    adapted = adapter.adapt_record(raw)
    assert adapted["relevant_signal_evidence"] == EvidenceLevel.INFERRED
    assert any("UNSUPPORTED_VERIFIED_CLAIM" in w for w in adapted["adapter_audit"]["warnings"])


def test_malformed_contact_handling(adapter):
    raw = {
        "company_name": "Test Firm",
        "email": "test@testfirm.co.uk"
    }
    adapted = adapter.adapt_record(raw)
    assert adapted["contact_name"] == "UNKNOWN_CONTACT"
    assert any("MALFORMED_CONTACT" in w for w in adapted["adapter_audit"]["warnings"])


def test_invalid_email_status_handling(adapter):
    raw = {
        "company_name": "Test Firm",
        "contact_name": "Test User",
        "job_title": "Director",
        "email": "test@testfirm.co.uk",
        "email_status": "SUPER_VERIFIED_100_PERCENT"
    }
    adapted = adapter.adapt_record(raw)
    assert adapted["email_status_input"] == EmailStatus.PATTERN_CONFIRMED
    assert any("INVALID_EMAIL_STATUS" in w for w in adapted["adapter_audit"]["warnings"])


def test_ingestion_and_export_pilot_leads(adapter):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    export_path = os.path.join(base_dir, "data", "deepline_export_sample.json")
    buffer_path = os.path.join(base_dir, "data", "research_leads.json")

    results = adapter.adapt(export_path, buffer_path)
    assert len(results) == 5
    assert os.path.exists(buffer_path)
