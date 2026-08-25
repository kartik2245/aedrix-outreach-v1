"""
test_bedrock_integration.py
Unit tests for AWS Bedrock DeepSeek V3.2 integration and Production Batch Runner.
Covers:
1. Bedrock configuration & initialization
2. Dry-run mode email generation
3. Response JSON parsing
4. Mocked AWS Bedrock Converse API invocation
5. Production batch runner integration
"""

import json
import os
import pytest
from unittest.mock import MagicMock
from src.integrations.bedrock_client import BedrockClient
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


def test_bedrock_client_initialization_defaults():
    """Verify BedrockClient loads environment defaults correctly."""
    client = BedrockClient(dry_run=True)
    assert client.provider == "aws_bedrock"
    assert client.region in ("eu-north-1", "ap-south-1")
    assert client.model == "deepseek.v3.2"
    assert client.dry_run is True


def test_bedrock_dry_run_mode(sample_lead):
    """Verify Bedrock dry run mode generates compliant email drafts without network calls."""
    client = BedrockClient(dry_run=True)
    e1 = client.generate_email_1(sample_lead)
    fa = client.generate_followup_a(sample_lead, e1)
    fb = client.generate_followup_b(sample_lead)

    assert e1.generation_mode == "DRY_RUN_TEMPLATE"
    assert fa.generation_mode == "DRY_RUN_TEMPLATE"
    assert fb.generation_mode == "DRY_RUN_TEMPLATE"
    assert e1.word_count <= 120
    assert fa.word_count <= 90
    assert fb.word_count <= 90


def test_bedrock_json_response_parsing():
    """Verify Bedrock JSON response parser extracts clean JSON from markdown code blocks or raw strings."""
    client = BedrockClient(dry_run=True)

    raw_markdown = '```json\n{\n  "subject": "Document control for Kier",\n  "body": "Hi Colin,\\n\\nSaw your Digital by Default strategy."\n}\n```'
    parsed = client.parse_json_response(raw_markdown)
    assert parsed["subject"] == "Document control for Kier"
    assert "Digital by Default" in parsed["body"]

    raw_json = '{"subject": "Follow-up regarding Kier", "body": "Hi Colin, checking in."}'
    parsed2 = client.parse_json_response(raw_json)
    assert parsed2["subject"] == "Follow-up regarding Kier"
    assert parsed2["body"] == "Hi Colin, checking in."


def test_mocked_bedrock_converse_api_call(sample_lead):
    """Verify mocked AWS Bedrock Converse API call with DeepSeek V3.2 returns BEDROCK_DEEPSEEK_API result."""
    mock_boto_client = MagicMock()
    mock_boto_client.converse.return_value = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": json.dumps({
                            "subject": "Pre-construction control for Kier Group",
                            "body": "Hi Colin,\n\nSaw Kier's official Digital by Default strategy. Aedrix unifies document control directly with real-time site manpower tracking.\n\nOpen to a brief 2-minute overview?\n\nBest regards,\nAedrix Team"
                        })
                    }
                ]
            }
        }
    }

    client = BedrockClient(dry_run=False, bedrock_client=mock_boto_client)
    e1 = client.generate_email_1(sample_lead)

    assert e1.generation_mode == "BEDROCK_DEEPSEEK_API"
    assert e1.subject == "Pre-construction control for Kier Group"
    assert "Digital by Default" in e1.body
    assert mock_boto_client.converse.called


def test_production_batch_runner_uses_bedrock_by_default(tmp_path):
    """Verify ProductionBatchRunner defaults to BedrockClient."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_export = os.path.join(base_dir, "data", "deepline_export_sample.json")
    output_path = str(tmp_path / "test_bedrock_personalization_drafts.json")

    runner = ProductionBatchRunner()
    assert isinstance(runner.llm_client, BedrockClient)
    results = runner.run_batch(sample_export, output_path)

    assert os.path.exists(output_path)
    assert len(results) >= 5


def test_bedrock_client_explicit_env_credentials(monkeypatch):
    """Verify BedrockClient uses explicit environment credentials when provided."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "mock_key_id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "mock_secret_key")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "mock_token")

    mock_boto3 = MagicMock()
    monkeypatch.setattr("boto3.client", mock_boto3)

    client = BedrockClient(dry_run=False)
    client._init_bedrock_client()

    mock_boto3.assert_called_with(
        "bedrock-runtime",
        region_name=client.region,
        aws_access_key_id="mock_key_id",
        aws_secret_access_key="mock_secret_key",
        aws_session_token="mock_token",
    )


def test_bedrock_client_shared_credential_chain(monkeypatch):
    """Verify BedrockClient resolves shared credential chain via boto3.Session when env vars are absent."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)

    mock_frozen = MagicMock()
    mock_frozen.access_key = "shared_key_id"
    mock_frozen.secret_key = "shared_secret_key"
    mock_frozen.token = None

    mock_creds = MagicMock()
    mock_creds.get_frozen_credentials.return_value = mock_frozen

    mock_session_instance = MagicMock()
    mock_session_instance.get_credentials.return_value = mock_creds

    mock_session_cls = MagicMock(return_value=mock_session_instance)
    mock_boto3 = MagicMock()

    monkeypatch.setattr("boto3.Session", mock_session_cls)
    monkeypatch.setattr("boto3.client", mock_boto3)

    client = BedrockClient(dry_run=False)
    client._init_bedrock_client()

    mock_boto3.assert_called_with(
        "bedrock-runtime",
        region_name=client.region,
        aws_access_key_id="shared_key_id",
        aws_secret_access_key="shared_secret_key",
    )


def test_bedrock_client_no_credentials_safe_initialization(monkeypatch):
    """Verify BedrockClient initializes safely without crash when no credentials are found."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)

    mock_session_instance = MagicMock()
    mock_session_instance.get_credentials.return_value = None

    mock_session_cls = MagicMock(return_value=mock_session_instance)
    mock_boto3 = MagicMock()

    monkeypatch.setattr("boto3.Session", mock_session_cls)
    monkeypatch.setattr("boto3.client", mock_boto3)

    client = BedrockClient(dry_run=False)
    res = client._init_bedrock_client()

    assert res is not None
    mock_boto3.assert_called_with("bedrock-runtime", region_name=client.region)

