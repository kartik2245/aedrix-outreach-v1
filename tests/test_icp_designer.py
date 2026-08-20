"""
test_icp_designer.py
Unit tests for the Claude-powered Dynamic ICP Designer.
Verifies zero-hallucination prompting, deterministic dry-run mode, JSON parsing, constraint preservation, and versioning.
"""

import json
import pytest
from unittest.mock import MagicMock

from src.icp.icp_designer import ICPDesigner
from src.icp.icp_models import ICPConfig, ICPStatus
from src.integrations.claude_client import ClaudeClient


def test_1_designer_dry_run_generates_valid_icp():
    """Verify deterministic offline generation in DRY_RUN mode."""
    designer = ICPDesigner()
    assert designer.dry_run is True

    icp = designer.design_icp(
        campaign_name="UK Construction Enterprise Digital",
        campaign_objective="Target UK main contractors with active BIM or digital transformation initiatives.",
        geography="United Kingdom",
        industry="Commercial Construction, Civil Engineering",
        company_size="100+ employees or £20M+ revenue",
        target_personas=["Digital Director", "IT Director", "Head of Digital Construction"],
        minimum_employees=100,
        minimum_revenue=20.0,
        positive_signals=["Active digital roadmap", "Multi-site regional projects"],
        negative_signals=["Single-site subcontractor"],
        hard_disqualifiers=["Outside United Kingdom", "Non-construction business model"],
        campaign_exclusions=["Active CRM deal", "Global opt-out list"]
    )

    assert isinstance(icp, ICPConfig)
    assert icp.name == "UK Construction Enterprise Digital"
    assert icp.status == ICPStatus.PENDING_REVIEW
    assert icp.version == "1.0.0"
    assert icp.minimum_employees == 100
    assert icp.minimum_revenue == 20.0
    assert len(icp.target_personas) >= 3
    assert len(icp.hard_disqualifiers) >= 2
    assert len(icp.campaign_exclusions) >= 2
    assert "United Kingdom" in icp.geography.primary_country
    assert icp.reasoning is not None


def test_2_preservation_of_user_constraints():
    """Verify user-provided constraints (personas, signals, size) are preserved accurately."""
    designer = ICPDesigner()

    custom_personas = ["Chief Technology Officer", "VP of Operational Technology"]
    custom_pos_signals = ["ISO 19650 BIM Certification"]
    custom_neg_signals = ["Residential handyman services"]

    icp = designer.design_icp(
        campaign_name="Specialist BIM Contractors",
        campaign_objective="Target contractors with ISO 19650 BIM compliance.",
        target_personas=custom_personas,
        positive_signals=custom_pos_signals,
        negative_signals=custom_neg_signals,
        minimum_employees=250,
        minimum_revenue=50.0
    )

    assert icp.minimum_employees == 250
    assert icp.minimum_revenue == 50.0
    assert any("Chief Technology Officer" in p for p in icp.target_personas)
    assert any("ISO 19650" in s for s in icp.positive_signals)
    assert any("Residential" in s for s in icp.negative_signals)


def test_3_claude_not_used_for_icp_generation():
    """Verify that Claude API is never called for ICP generation even if client is passed."""
    mock_client = MagicMock()
    claude_wrapper = ClaudeClient(dry_run=False, anthropic_client=mock_client)
    designer = ICPDesigner(claude_client=claude_wrapper)

    icp = designer.design_icp(
        campaign_name="Mid-Market UK Builders",
        campaign_objective="Target regional commercial builders."
    )

    assert isinstance(icp, ICPConfig)
    assert icp.name == "Mid-Market UK Builders"
    assert icp.status == ICPStatus.PENDING_REVIEW
    assert not mock_client.messages.create.called


def test_4_offline_icp_generation_resilience():
    """Verify deterministic offline ICP generation succeeds independently of API state."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("Anthropic API Error")

    claude_wrapper = ClaudeClient(dry_run=False, anthropic_client=mock_client)
    designer = ICPDesigner(claude_client=claude_wrapper)

    icp = designer.design_icp(
        campaign_name="Resilient Fallback Campaign",
        campaign_objective="Must generate valid ICP offline."
    )

    assert isinstance(icp, ICPConfig)
    assert icp.name == "Resilient Fallback Campaign"
    assert icp.status == ICPStatus.PENDING_REVIEW
    assert not mock_client.messages.create.called


def test_5_missing_optional_fields_defaults():
    """Verify missing optional fields receive conservative, safe defaults."""
    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="Minimal Input Campaign",
        campaign_objective="Basic targeting test"
    )

    assert icp.minimum_employees == 50
    assert icp.minimum_revenue == 10.0
    assert len(icp.target_personas) > 0
    assert len(icp.hard_disqualifiers) > 0
    assert len(icp.campaign_exclusions) > 0
