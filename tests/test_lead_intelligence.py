"""
test_lead_intelligence.py
Pytest unit tests for Lead Intelligence Engine (Python 3.12).
"""

import json
import os
import pytest
from src.lead_intelligence import LeadIntelligenceEngine
from src.models import EvidenceLevel, EmailStatus, DisqualificationStatus, PersonalizationNoteStatus, PriorityLevel


@pytest.fixture
def engine():
    return LeadIntelligenceEngine()


@pytest.fixture
def sample_leads():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    leads_path = os.path.join(base_dir, "data", "sample_leads.json")
    with open(leads_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_standard_5_pilot_leads(engine, sample_leads):
    for i, lead in enumerate(sample_leads):
        result = engine.process_lead(lead)
        assert result.opportunity_score >= 70, f"Lead {i+1} opportunity score >= 70"
        assert result.disqualification_status == DisqualificationStatus.QUALIFIED
        assert result.outreach_priority_index > 0
        assert result.priority_level in [PriorityLevel.P1, PriorityLevel.P2]


def test_hard_disqualification_non_uk(engine):
    non_uk_lead = {
        "company_name": "US Civil MegaCorp",
        "company_domain": "uscivil.com",
        "contact_name": "John Smith",
        "job_title": "CIO",
        "email": "jsmith@uscivil.com",
        "company_size": "10,000+ employees",
        "industry": "Commercial Construction",
        "is_uk_operating": False,
        "country": "USA"
    }
    result = engine.process_lead(non_uk_lead)
    assert result.disqualification_status == DisqualificationStatus.HARD_DISQUALIFIED
    assert result.opportunity_score == 0
    assert "Non-UK geography" in result.disqualification_reason


def test_hard_disqualification_non_construction(engine):
    tech_lead = {
        "company_name": "SaaS Enterprise Ltd",
        "company_domain": "saasenterprise.co.uk",
        "contact_name": "Alice Johnson",
        "job_title": "VP Sales",
        "email": "alice@saasenterprise.co.uk",
        "company_size": "500 employees",
        "industry": "Software & Technology",
        "is_uk_operating": True,
        "country": "UK",
        "is_construction_sector": False
    }
    result = engine.process_lead(tech_lead)
    assert result.disqualification_status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "Non-construction sector" in result.disqualification_reason


def test_campaign_exclusion_active_crm(engine):
    active_client_lead = {
        "company_name": "Kier Group plc",
        "company_domain": "kier.co.uk",
        "contact_name": "Colin Bell",
        "job_title": "Digital Director",
        "email": "c.bell@kier.co.uk",
        "company_size": "10,000+ employees",
        "industry": "Commercial Construction",
        "is_uk_operating": True,
        "country": "UK",
        "is_active_crm_deal": True
    }
    result = engine.process_lead(active_client_lead)
    assert result.disqualification_status == DisqualificationStatus.CAMPAIGN_EXCLUDED
    assert result.opportunity_score > 0
    assert "Active sales deal" in result.disqualification_reason


def test_campaign_exclusion_invalid_email(engine):
    bounced_lead = {
        "company_name": "Bowmer & Kirkland",
        "company_domain": "bandk.co.uk",
        "contact_name": "John Foster",
        "job_title": "Business Improvement Director",
        "email": "invalid-user-bounce@bandk.co.uk",
        "company_size": "1,500+ employees",
        "industry": "Commercial Construction",
        "is_uk_operating": True,
        "country": "UK",
        "is_hard_bounce": True
    }
    result = engine.process_lead(bounced_lead)
    assert result.email_status == EmailStatus.INVALID_BOUNCED
    assert result.disqualification_status == DisqualificationStatus.CAMPAIGN_EXCLUDED


def test_no_strong_signal_fallback(engine):
    no_signal_lead = {
        "company_name": "Unknown Regional Builders Ltd",
        "company_domain": "unknownregional.co.uk",
        "contact_name": "Dave Miller",
        "job_title": "Operations Director",
        "email": "d.miller@unknownregional.co.uk",
        "company_size": "200 employees",
        "industry": "Commercial Construction",
        "is_uk_operating": True,
        "country": "UK",
        "relevant_signal": "NO_STRONG_SIGNAL",
        "relevant_signal_evidence": EvidenceLevel.UNKNOWN
    }
    result = engine.process_lead(no_signal_lead)
    assert result.personalization_note_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL
    assert "Given your role leading operations" in result.personalization_note


def test_edge_case_high_opp_low_acc(engine):
    high_opp_low_acc_lead = {
        "company_name": "Balfour Beatty Megadeal",
        "company_domain": "balfourbeatty.com",
        "contact_name": "Group CIO Target",
        "job_title": "Chief Information Officer (CIO)",
        "email": "info@balfourbeatty.com",
        "email_status_input": "CATCHALL_UNVERIFIED",
        "company_size": "26,000 global",
        "industry": "Major Infrastructure & Civil Engineering",
        "relevant_signal": "Appointed Group CIO to lead digital delivery engine",
        "relevant_signal_evidence": "VERIFIED",
        "is_uk_operating": True,
        "country": "UK",
        "ownership_type": "PUBLIC_PLC"
    }
    result = engine.process_lead(high_opp_low_acc_lead)
    assert result.opportunity_score >= 75
    assert result.accessibility_score < 60
    assert result.outreach_priority_index < result.opportunity_score
