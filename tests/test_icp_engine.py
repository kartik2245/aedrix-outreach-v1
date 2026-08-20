"""
test_icp_engine.py
Unit tests for Configurable ICP Engine in Aedrix Cold Outreach System (Python 3.12).
Covers Test Cases:
A. ICP Qualified Lead
B. ICP Hard Disqualification (Non-UK, Non-Construction, Under-size threshold)
C. Campaign Exclusion (Active CRM, Global Opt-Out, 60-day contact, Invalid Bounce)
"""

import json
import os
import pytest
from src.icp.icp_engine import ICPEngine
from src.models import DisqualificationStatus


@pytest.fixture
def icp_engine():
    return ICPEngine()


# --- Test Case A: ICP Qualified Lead ---

def test_a_icp_qualified_uk_commercial_contractor(icp_engine):
    """Test A: Verified UK commercial main contractor >=50 employees qualifies for ICP."""
    lead = {
        "company_name": "Bowmer & Kirkland (B&K)",
        "company_domain": "bandk.co.uk",
        "company_location": "UK",
        "industry": "Commercial Construction",
        "company_size": "1,500+ employees",
        "revenue": "£1.1B+",
        "contact_name": "John Foster",
        "job_title": "Business Improvement Director",
        "email": "j.foster@bandk.co.uk",
        "is_uk_operating": True,
        "is_construction_sector": True,
    }
    result = icp_engine.evaluate_lead(lead)
    assert result.status == DisqualificationStatus.QUALIFIED
    assert result.disqualification_reason is None
    assert result.rule_code == "ICP_QUALIFIED"


def test_a_icp_qualified_revenue_threshold(icp_engine):
    """Test A: UK Contractor with <50 employees but >=£10M revenue qualifies."""
    lead = {
        "company_name": "Specialist High-Rev Civils Ltd",
        "company_domain": "highrevcivils.co.uk",
        "company_location": "UK",
        "industry": "Civil Engineering & Infrastructure",
        "employee_count": 35,
        "revenue": "£15M",
        "contact_name": "Sarah Evans",
        "job_title": "Operations Director",
        "email": "s.evans@highrevcivils.co.uk",
        "is_uk_operating": True,
        "is_construction_sector": True,
    }
    result = icp_engine.evaluate_lead(lead)
    assert result.status == DisqualificationStatus.QUALIFIED


# --- Test Case B: ICP Hard Disqualification ---

def test_b_hard_disqualification_non_uk(icp_engine):
    """Test B: Non-UK geography is hard disqualified."""
    lead = {
        "company_name": "US Mega Builders Inc",
        "company_domain": "usmegabuilders.com",
        "country": "USA",
        "industry": "Commercial Construction",
        "company_size": "5,000 employees",
        "contact_name": "Bob Taylor",
        "job_title": "CIO",
        "email": "btaylor@usmegabuilders.com",
        "is_uk_operating": False,
    }
    result = icp_engine.evaluate_lead(lead)
    assert result.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "Non-UK geography" in (result.disqualification_reason or "")
    assert result.rule_code == "OUTSIDE_UK"


def test_b_hard_disqualification_non_construction(icp_engine):
    """Test B: Non-construction sector is hard disqualified."""
    lead = {
        "company_name": "Fintech Global Payments Ltd",
        "company_domain": "fintechglobal.co.uk",
        "country": "UK",
        "industry": "Financial Software & Banking",
        "company_size": "2,000 employees",
        "contact_name": "Alice Smith",
        "job_title": "Head of IT",
        "email": "alice@fintechglobal.co.uk",
        "is_uk_operating": True,
        "is_construction_sector": False,
    }
    result = icp_engine.evaluate_lead(lead)
    assert result.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "Non-construction sector" in (result.disqualification_reason or "")
    assert result.rule_code == "NON_CONSTRUCTION"


def test_b_hard_disqualification_under_size_threshold(icp_engine):
    """Test B: Micro-contractor under size and revenue threshold is hard disqualified."""
    lead = {
        "company_name": "Local Handyman Renovations",
        "company_domain": "localhandyman.co.uk",
        "country": "UK",
        "industry": "Building Contractor",
        "employee_count": 5,
        "revenue": "£400k",
        "contact_name": "Dave Brown",
        "job_title": "Owner",
        "email": "dave@localhandyman.co.uk",
        "is_uk_operating": True,
        "is_construction_sector": True,
    }
    result = icp_engine.evaluate_lead(lead)
    assert result.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "Under minimum size threshold" in (result.disqualification_reason or "")
    assert result.rule_code == "UNDER_SIZE_THRESHOLD"


# --- Test Case C: Campaign Exclusion ---

def test_c_campaign_exclusion_active_crm_deal(icp_engine):
    """Test C: Lead with active CRM opportunity is campaign excluded."""
    lead = {
        "company_name": "Kier Group plc",
        "company_domain": "kier.co.uk",
        "country": "UK",
        "industry": "Commercial Construction",
        "company_size": "10,000+ employees",
        "contact_name": "Colin Bell",
        "job_title": "Digital Director",
        "email": "c.bell@kier.co.uk",
        "is_uk_operating": True,
        "is_active_crm_deal": True,
    }
    result = icp_engine.evaluate_lead(lead)
    assert result.status == DisqualificationStatus.CAMPAIGN_EXCLUDED
    assert "Active sales deal" in (result.disqualification_reason or "")
    assert result.rule_code == "ACTIVE_CRM_DEAL"


def test_c_campaign_exclusion_global_opt_out(icp_engine):
    """Test C: Global suppression / opt-out lead is excluded."""
    lead = {
        "company_name": "Laing O'Rourke",
        "company_domain": "laingorourke.com",
        "country": "UK",
        "industry": "Construction",
        "company_size": "13,000+ employees",
        "contact_name": "Gareth Rhys",
        "job_title": "Head of Digital Engineering",
        "email": "grhys@laingorourke.com",
        "is_uk_operating": True,
        "is_global_suppressed": True,
    }
    result = icp_engine.evaluate_lead(lead)
    assert result.status == DisqualificationStatus.CAMPAIGN_EXCLUDED
    assert "global suppression" in (result.disqualification_reason or "")
    assert result.rule_code == "GLOBAL_OPT_OUT"


def test_c_campaign_exclusion_contacted_within_60_days(icp_engine):
    """Test C: Lead contacted within past 60 days is campaign excluded."""
    lead = {
        "company_name": "Balfour Beatty plc",
        "company_domain": "balfourbeatty.com",
        "country": "UK",
        "industry": "Infrastructure",
        "company_size": "26,000+ employees",
        "contact_name": "Mark Harrison",
        "job_title": "Chief Information Officer",
        "email": "m.harrison@balfourbeatty.com",
        "is_uk_operating": True,
        "contacted_within_60_days": True,
    }
    result = icp_engine.evaluate_lead(lead)
    assert result.status == DisqualificationStatus.CAMPAIGN_EXCLUDED
    assert "Contacted within past 60 days" in (result.disqualification_reason or "")
    assert result.rule_code == "CONTACTED_WITHIN_60_DAYS"


def test_c_campaign_exclusion_invalid_bounced_email(icp_engine):
    """Test C: Invalid / bounced email lead is campaign excluded."""
    lead = {
        "company_name": "Morgan Sindall Group plc",
        "company_domain": "morgansindall.com",
        "country": "UK",
        "industry": "Construction",
        "company_size": "7,500+ employees",
        "contact_name": "Phil Robinson",
        "job_title": "Operations Director",
        "email": "bad-address-bounce@morgansindall.com",
        "is_uk_operating": True,
        "is_hard_bounce": True,
    }
    result = icp_engine.evaluate_lead(lead)
    assert result.status == DisqualificationStatus.CAMPAIGN_EXCLUDED
    assert "invalid or hard bounced" in (result.disqualification_reason or "")
    assert result.rule_code == "INVALID_BOUNCED_EMAIL"
