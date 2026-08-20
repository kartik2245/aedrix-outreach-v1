"""
test_claude_integration.py
Unit tests for Anthropic Claude Client integration and Production Batch Runner.
Covers Test Cases:
F. Claude Configuration Missing
G. Claude Dry-Run Mode
H. Claude Response Parsing
M. Production Batch Execution
"""

import json
import os
import pytest
from unittest.mock import MagicMock
from src.integrations.claude_client import ClaudeClient
from src.production_batch_runner import ProductionBatchRunner
from src.models import (
    LeadIntelligenceOutput,
    EvidenceLevel,
    EmailStatus,
    DisqualificationStatus,
    PersonalizationNoteStatus,
    PriorityLevel,
    AccessibilityTier,
)


@pytest.fixture
def sample_lead():
    return LeadIntelligenceOutput(
        company_name="Kier Group plc",
        company_domain="kier.co.uk",
        contact_name="Colin Bell",
        job_title="Digital Director (Kier Construction)",
        email="c.bell@kier.co.uk",
        email_status=EmailStatus.PATTERN_CONFIRMED,
        company_size="10,000+ employees",
        company_size_evidence=EvidenceLevel.VERIFIED,
        industry="Infrastructure Services & Regional Building",
        opportunity_score=85.0,
        accessibility_score=72.0,
        outreach_priority_index=79.8,
        priority_level=PriorityLevel.P2,
        opportunity_tier="Tier 1 — Enterprise Strategic / Megadeal",
        accessibility_tier=AccessibilityTier.MEDIUM,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
        personalization_note="Saw Kier's official 'Digital by Default' strategy and restructured digital leadership. Aedrix bridges legacy systems with modern site data.",
        research_sources=["https://www.kier.co.uk/media/digital-by-default-strategy"],
        ICP_score=85.0,
        pain_point="Managing drawing revisions across multi-site regional teams.",
        pain_point_evidence=EvidenceLevel.INFERRED,
        relevant_signal="Operates an official 'Digital by Default' strategy",
        relevant_signal_evidence=EvidenceLevel.VERIFIED,
        persona_selection_rationale="Selected Digital Director for direct control over construction division digital systems."
    )


# --- Test Case F: Claude Configuration Missing ---

def test_f_claude_missing_config_falls_back_cleanly(sample_lead):
    """Test F: Missing API key does not crash and falls back safely to offline generation."""
    client = ClaudeClient(api_key="", dry_run=False)
    e1 = client.generate_email_1(sample_lead)
    assert e1 is not None
    assert e1.generation_mode == "DRY_RUN_TEMPLATE"
    assert "Kier" in e1.body
    assert e1.word_count <= 120


# --- Test Case G: Claude Dry-Run Mode ---

def test_g_claude_dry_run_mode(sample_lead):
    """Test G: Dry run mode generates compliant drafts without network calls."""
    client = ClaudeClient(dry_run=True)
    e1 = client.generate_email_1(sample_lead)
    fa = client.generate_followup_a(sample_lead, e1)
    fb = client.generate_followup_b(sample_lead)

    assert e1.generation_mode == "DRY_RUN_TEMPLATE"
    assert fa.generation_mode == "DRY_RUN_TEMPLATE"
    assert fb.generation_mode == "DRY_RUN_TEMPLATE"
    assert e1.word_count <= 120
    assert fa.word_count <= 90
    assert fb.word_count <= 90


# --- Test Case H: Claude Response Parsing ---

def test_h_claude_response_parsing():
    """Test H: Response parser extracts clean JSON from markdown code blocks or raw strings."""
    client = ClaudeClient(dry_run=True)

    # 1. Wrapped in ```json ... ```
    raw_markdown = '```json\n{\n  "subject": "Document control for Kier",\n  "body": "Hi Colin,\\n\\nSaw your Digital by Default strategy."\n}\n```'
    parsed = client.parse_claude_json_response(raw_markdown)
    assert parsed["subject"] == "Document control for Kier"
    assert "Digital by Default" in parsed["body"]

    # 2. Raw JSON string
    raw_json = '{"subject": "Follow-up regarding Kier", "body": "Hi Colin, checking in."}'
    parsed2 = client.parse_claude_json_response(raw_json)
    assert parsed2["subject"] == "Follow-up regarding Kier"
    assert parsed2["body"] == "Hi Colin, checking in."

    # 3. Surrounding prose
    prose_json = 'Here is the draft:\n{"subject": "Hello", "body": "Message body"}\nLet me know!'
    parsed3 = client.parse_claude_json_response(prose_json)
    assert parsed3["subject"] == "Hello"
    assert parsed3["body"] == "Message body"


def test_h_mocked_claude_api_call(sample_lead):
    """Test H: Mocked Anthropic SDK client parses LLM generated response."""
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = json.dumps({
        "subject": "Pre-construction document control at Kier Group plc",
        "body": "Hi Colin,\n\nSaw Kier's official Digital by Default strategy. Aedrix unifies document control directly with real-time site manpower tracking.\n\nOpen to a brief 2-minute overview?\n\nBest,\nAedrix Team"
    })
    mock_response.content = [mock_content]
    mock_anthropic.messages.create.return_value = mock_response

    client = ClaudeClient(api_key="test_mock_key", dry_run=False, anthropic_client=mock_anthropic)
    e1 = client.generate_email_1(sample_lead)

    assert e1.generation_mode == "CLAUDE_API"
    assert e1.subject == "Pre-construction document control at Kier Group plc"
    assert "Digital by Default" in e1.body
    assert e1.word_count <= 120
    assert mock_anthropic.messages.create.called


# --- Test Case M: Production Batch Execution ---

def test_m_production_batch_execution(tmp_path):
    """Test M: Production batch runner processes full dataset to local JSON output."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_export = os.path.join(base_dir, "data", "deepline_export_sample.json")
    output_path = str(tmp_path / "test_claude_personalization_drafts.json")

    runner = ProductionBatchRunner()
    results = runner.run_batch(sample_export, output_path)

    assert os.path.exists(output_path)
    assert len(results) >= 5

    with open(output_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    assert len(saved_data) == len(results)
    for record in saved_data:
        assert "company" in record
        assert "contact" in record
        assert "qualification_status" in record
        assert "opportunity_score" in record
        assert "accessibility_score" in record
        assert "outreach_priority_index" in record
        assert "priority" in record
        assert "personalization_note_status" in record
        assert "voc_angle" in record
        assert "email_1" in record
        assert "followup_a" in record
        assert "followup_b" in record
        assert "qa_status" in record
        assert "qa_reasons" in record
        assert record["qa_status"] in ("PASS", "FAIL", "SKIPPED")
