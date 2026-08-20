"""
test_smartlead_client.py
Comprehensive test suite for SmartleadClient REST API client, error handling, safety gating, and webhook normalization.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import urllib.error

from src.integrations.smartlead_client import (
    SmartleadClient,
    SmartleadError,
    SmartleadConfigError,
    SmartleadAuthError,
    SmartleadAPIError,
)
from src.models import (
    SmartleadWebhookEventType,
    SmartleadWebhookEvent,
)


def test_1_missing_api_key_in_live_mode_raises_config_error():
    """SmartleadClient in live mode with missing API key must raise SmartleadConfigError."""
    client = SmartleadClient(api_key="", live=True, dry_run=False)
    with pytest.raises(SmartleadConfigError) as exc_info:
        client.create_campaign("Test Campaign")
    assert "SMARTLEAD_API_KEY is not configured" in str(exc_info.value)


def test_2_dry_run_mode_does_not_call_api():
    """Dry-run mode returns mock response with 0 network calls."""
    client = SmartleadClient(api_key="mock_key", live=False, dry_run=True)
    res = client.create_campaign("UK Construction High Priority")
    assert res["ok"] is True
    assert res["status"] == "DRAFT"
    assert "dry-run mode" in res["message"]


def test_3_api_key_masking():
    """API key should be safely masked in logs."""
    assert SmartleadClient.mask_api_key(None) == "[NOT_SET]"
    assert SmartleadClient.mask_api_key("") == "[NOT_SET]"
    assert SmartleadClient.mask_api_key("1234") == "********"
    assert SmartleadClient.mask_api_key("abcdef1234567890") == "************7890"


def test_4_send_emails_false_prevents_campaign_resume():
    """Calling resume_campaign when SEND_EMAILS=false must raise SmartleadConfigError."""
    client = SmartleadClient(api_key="test_key", live=True, dry_run=False, send_emails=False)
    with pytest.raises(SmartleadConfigError) as exc_info:
        client.resume_campaign(12345)
    assert "SEND_EMAILS=false" in str(exc_info.value)


@patch("urllib.request.urlopen")
def test_5_mocked_successful_campaign_creation(mock_urlopen):
    """Test live campaign creation with mocked successful HTTP response."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({
        "ok": True,
        "id": 554433,
        "name": "Live Campaign",
        "status": "DRAFT"
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = SmartleadClient(api_key="valid_key", live=True, dry_run=False)
    res = client.create_campaign("Live Campaign")

    assert res["ok"] is True
    assert res["id"] == 554433
    assert res["status"] == "DRAFT"


@patch("urllib.request.urlopen")
def test_6_http_401_raises_smartlead_auth_error(mock_urlopen):
    """HTTP 401 response from Smartlead must raise SmartleadAuthError."""
    fp = MagicMock()
    fp.read.return_value = json.dumps({"error": "Unauthorized API key"}).encode("utf-8")
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://server.smartlead.ai/api/v1/campaigns/create",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=fp
    )

    client = SmartleadClient(api_key="invalid_key", live=True, dry_run=False)
    with pytest.raises(SmartleadAuthError) as exc_info:
        client.create_campaign("Test")
    assert "authentication failed" in str(exc_info.value)


@patch("urllib.request.urlopen")
def test_7_http_500_raises_smartlead_api_error(mock_urlopen):
    """HTTP 500 server error from Smartlead must raise SmartleadAPIError."""
    fp = MagicMock()
    fp.read.return_value = json.dumps({"error": "Internal Server Error"}).encode("utf-8")
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://server.smartlead.ai/api/v1/campaigns/123",
        code=500,
        msg="Internal Error",
        hdrs={},
        fp=fp
    )

    client = SmartleadClient(api_key="valid_key", live=True, dry_run=False)
    with pytest.raises(SmartleadAPIError) as exc_info:
        client.get_campaign(123)
    assert exc_info.value.status_code == 500


@patch("urllib.request.urlopen")
def test_8_network_timeout_or_urlerror_raises_smartlead_api_error(mock_urlopen):
    """Network connection failure raises SmartleadAPIError."""
    mock_urlopen.side_effect = urllib.error.URLError(reason="Connection timed out")

    client = SmartleadClient(api_key="valid_key", live=True, dry_run=False)
    with pytest.raises(SmartleadAPIError) as exc_info:
        client.get_campaign(123)
    assert "Network error" in str(exc_info.value)


def test_9_campaign_operations_dry_run():
    """All campaign operations return structured mock payloads in dry-run mode."""
    client = SmartleadClient(dry_run=True, live=False)

    add_res = client.add_leads_to_campaign(123, [{"email": "test@domain.com"}])
    assert add_res["ok"] is True
    assert add_res["leads_added"] == 1

    seq_res = client.update_campaign_sequence(123, [{"subject": "Hi", "body": "Body"}])
    assert seq_res["ok"] is True
    assert "2-day initial wait enforced" in seq_res["message"]

    pause_res = client.pause_campaign(123)
    assert pause_res["ok"] is True
    assert pause_res["status"] == "PAUSED"

    analytics = client.get_campaign_analytics(123)
    assert analytics["sent_count"] == 0

    webhook = client.register_webhook(123, "https://my-webhook.com/event")
    assert webhook["webhook_id"] == "wh_mock_12345"


def test_10_webhook_normalization_open_event():
    """Normalizes incoming email open webhook."""
    client = SmartleadClient()
    raw = {
        "event_type": "email_open",
        "lead_email": "john.foster@bandk.co.uk",
        "campaign_id": "12345",
        "timestamp": "2026-08-17T10:00:00Z"
    }
    event = client.normalize_webhook_event(raw)
    assert event.event_type == SmartleadWebhookEventType.EMAIL_OPENED
    assert event.lead_email == "john.foster@bandk.co.uk"
    assert event.campaign_id == "12345"


def test_11_webhook_normalization_reply_event():
    """Normalizes incoming email reply webhook with body text."""
    client = SmartleadClient()
    raw = {
        "event": "EMAIL_REPLIED",
        "to_email": "c.bell@kier.co.uk",
        "campaign": {"id": 9988},
        "reply_text": "Hi, I am interested in seeing a 2-minute demo."
    }
    event = client.normalize_webhook_event(raw)
    assert event.event_type == SmartleadWebhookEventType.EMAIL_REPLIED
    assert event.lead_email == "c.bell@kier.co.uk"
    assert event.campaign_id == "9988"
    assert "demo" in event.details.get("reply_text", "")


def test_12_webhook_normalization_bounce_event():
    """Normalizes incoming email bounce webhook."""
    client = SmartleadClient()
    raw = {
        "event_name": "email_bounce",
        "email": "invalid@fake-contractor.co.uk"
    }
    event = client.normalize_webhook_event(raw)
    assert event.event_type == SmartleadWebhookEventType.EMAIL_BOUNCED
    assert event.lead_email == "invalid@fake-contractor.co.uk"


def test_13_webhook_normalization_unsubscribe_event():
    """Normalizes incoming unsubscribe webhook."""
    client = SmartleadClient()
    raw = {
        "event_type": "email_unsubscribe",
        "lead": {"email": "optout@company.com"}
    }
    event = client.normalize_webhook_event(raw)
    assert event.event_type == SmartleadWebhookEventType.EMAIL_UNSUBSCRIBED
    assert event.lead_email == "optout@company.com"
