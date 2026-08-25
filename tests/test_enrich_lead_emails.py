"""
test_enrich_lead_emails.py
==========================
Targeted unit tests for Part 1 Deepline Play person-linkedin-to-email enrichment
and status classification in DeeplineClient.

Verified test requirements:
1. Verified Email:
   Input: linkedin_url exists, mock play returns email_validated=True, email_found_and_valid=True
   Expected: email = person@company.com, email_status = VERIFIED

2. Unverified Email:
   Input: linkedin_url exists, mock play returns email_validated=False, email_found_and_valid=False
   Expected: email = person@company.com, email_status = UNVERIFIED

3. No Email:
   Input: linkedin_url exists, mock play returns email=None
   Expected: email_status = NO_EMAIL

4. Missing / Invalid LinkedIn URL:
   Expected: no Deepline call, deterministic result, no crash

5. Deepline Failure:
   Expected: pipeline does not crash, email is not falsely marked VERIFIED
"""

import pytest
from unittest.mock import MagicMock, patch


def _make_client(live=False, api_key="test_key"):
    """Return a DeeplineClient without touching the filesystem or network."""
    from src.integrations.deepline_client import DeeplineClient
    return DeeplineClient(api_key=api_key, live_mode=live)


# ---------------------------------------------------------------------------
# Test Group 1: Verification that old Email Finder methods are absent
# ---------------------------------------------------------------------------

class TestEmailFinderArchitectureRemoved:
    """Explicitly verifies that Email Finder methods and webhook dependencies do not exist."""

    def test_get_email_finder_statistics_method_removed(self):
        client = _make_client(live=False)
        assert not hasattr(client, "get_email_finder_statistics"), (
            "get_email_finder_statistics method must be completely removed from DeeplineClient"
        )

    def test_get_email_finder_results_method_removed(self):
        client = _make_client(live=False)
        assert not hasattr(client, "get_email_finder_results"), (
            "get_email_finder_results method must be completely removed from DeeplineClient"
        )


# ---------------------------------------------------------------------------
# Test Group 2: Play Person-LinkedIn-to-Email Status Rules & Logic
# ---------------------------------------------------------------------------

class TestPlayEmailEnrichmentStatusRules:
    """Unit tests for the 3 logical states: VERIFIED, UNVERIFIED, NO_EMAIL."""

    def test_verified_email_from_play(self):
        """1. Verified email: email exists + validated=True + found_and_valid=True -> VERIFIED"""
        client = _make_client(live=False)
        lead = {
            "linkedin_url": "https://www.linkedin.com/in/gurwinder",
            "mock_play_response": {
                "email": "gurwinder@fkointech.com",
                "email_source": "prospeo_verified_email",
                "email_validated": True,
                "email_found_and_valid": True,
                "miss_reason": None
            }
        }
        res = client.enrich_single_lead_email(lead)
        assert res["email"] == "gurwinder@fkointech.com"
        assert res["email_status"] == "VERIFIED"
        assert res["email_validated"] is True
        assert res["email_found_and_valid"] is True
        assert res["email_source"] == "prospeo_verified_email"
        assert res["enrichment_status"] == "SUCCESS"

    def test_unverified_email_from_play(self):
        """2. Unverified email: email exists but email_validated=False -> UNVERIFIED"""
        client = _make_client(live=False)
        lead = {
            "linkedin_url": "https://www.linkedin.com/in/john-doe",
            "mock_play_response": {
                "email": "john.doe@company.com",
                "email_source": "guessed",
                "email_validated": False,
                "email_found_and_valid": False,
                "miss_reason": "unconfirmed_pattern"
            }
        }
        res = client.enrich_single_lead_email(lead)
        assert res["email"] == "john.doe@company.com"
        assert res["email_status"] == "UNVERIFIED"
        assert res["email_validated"] is False
        assert res["email_found_and_valid"] is False
        assert res["enrichment_status"] == "UNVERIFIED_EMAIL_FOUND"

    def test_no_email_returned_from_play(self):
        """3. No email: Play returns email=None -> NO_EMAIL"""
        client = _make_client(live=False)
        lead = {
            "linkedin_url": "https://www.linkedin.com/in/no-email-user",
            "mock_play_response": {
                "email": None,
                "email_validated": False,
                "email_found_and_valid": False,
                "miss_reason": "no_email_found"
            }
        }
        res = client.enrich_single_lead_email(lead)
        assert res["email"] == ""
        assert res["email_status"] == "NO_EMAIL"
        assert res["enrichment_status"] == "NO_EMAIL_FOUND"

    def test_missing_linkedin_url(self):
        """4. Missing LinkedIn URL -> deterministic NO_EMAIL, zero network call, no crash."""
        client = _make_client(live=True)
        lead = {"contact_name": "No LinkedIn", "company_domain": "nurl.com"}

        with patch("subprocess.run", side_effect=AssertionError("Subprocess must not be called")):
            res = client.enrich_single_lead_email(lead)

        assert res["email"] == ""
        assert res["email_status"] == "NO_EMAIL"
        assert res["enrichment_status"] == "MISSING_LINKEDIN_URL"

    def test_invalid_linkedin_url_string(self):
        """Invalid LinkedIn URL (not containing linkedin.com) -> deterministic NO_EMAIL, no crash."""
        client = _make_client(live=True)
        lead = {"linkedin_url": "https://twitter.com/someuser"}

        with patch("subprocess.run", side_effect=AssertionError("Subprocess must not be called")):
            res = client.enrich_single_lead_email(lead)

        assert res["email_status"] == "NO_EMAIL"
        assert res["enrichment_status"] == "INVALID_LINKEDIN_URL"

    def test_deepline_play_failure_graceful_handling(self):
        """5. Deepline failure: CLI subprocess error -> pipeline does not crash, email NOT marked VERIFIED."""
        client = _make_client(live=True)
        client.run_confirmed = True
        lead = {"linkedin_url": "https://www.linkedin.com/in/error-user"}

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "API connection error"

        with patch("subprocess.run", return_value=mock_proc):
            res = client.enrich_single_lead_email(lead)

        assert res["email"] == ""
        assert res["email_status"] == "NO_EMAIL"
        assert res["email_status"] != "VERIFIED"
        assert "enrichment_error" in res

    def test_deepline_play_timeout_graceful_handling(self):
        """Deepline timeout -> pipeline does not crash, email NOT marked VERIFIED."""
        import subprocess
        client = _make_client(live=True)
        client.run_confirmed = True
        lead = {"linkedin_url": "https://www.linkedin.com/in/timeout-user"}

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="deepline", timeout=35)):
            res = client.enrich_single_lead_email(lead)

        assert res["email"] == ""
        assert res["email_status"] == "NO_EMAIL"
        assert res["enrichment_error"] == "PLAY_TIMEOUT"

    def test_batch_idempotency_same_linkedin_url(self):
        """Avoids duplicate Play executions for same LinkedIn URL in batch."""
        client = _make_client(live=False)
        leads = [
            {
                "linkedin_url": "https://www.linkedin.com/in/dup-user",
                "mock_play_response": {"email": "dup@co.com", "email_validated": True, "email_found_and_valid": True}
            },
            {
                "linkedin_url": "https://www.linkedin.com/in/dup-user",
                "contact_name": "Second Instance"
            }
        ]

        with patch.object(client, "enrich_single_lead_email", wraps=client.enrich_single_lead_email) as mock_single:
            enriched = client.enrich_lead_emails(leads)

        assert len(enriched) == 2
        assert mock_single.call_count == 1  # Called only once due to idempotency cache!
        assert enriched[0]["email"] == "dup@co.com"
        assert enriched[1]["email"] == "dup@co.com"


# ---------------------------------------------------------------------------
# Test Group 3: Quality Gate & DeepSeek Execution Safety
# ---------------------------------------------------------------------------

class TestQualityGateAndDeepSeekSafety:
    """Quality Gate accepts VERIFIED, rejects UNVERIFIED and NO_EMAIL."""

    @pytest.fixture
    def tmp_stores(self, tmp_path):
        from src.approval.approval_store import ApprovalStore
        from src.approval.approval_engine import ApprovalEngine
        from src.icp.icp_approval_store import ICPApprovalStore
        from src.icp.icp_approval_engine import ICPApprovalEngine
        app_store = ApprovalStore(storage_path=str(tmp_path / "app_q.json"))
        app_engine = ApprovalEngine(store=app_store)
        icp_store = ICPApprovalStore(storage_path=str(tmp_path / "icp_q.json"))
        icp_engine = ICPApprovalEngine(store=icp_store)
        return app_engine, icp_engine

    @pytest.fixture
    def minimal_icp(self):
        from src.icp.icp_models import ICPConfig, ICPStatus, GeographyConfig
        return ICPConfig(
            id="icp_no_email",
            campaign_id="camp_no_email",
            name="No Email Test",
            campaign_description="No verified email test",
            status=ICPStatus.APPROVED,
            geography=GeographyConfig(
                primary_country="India",
                allowed_country_keywords=["India", "Chandigarh"]
            ),
        )

    def test_unverified_email_skipped_by_quality_gate(self, tmp_stores, minimal_icp):
        """UNVERIFIED email is produced cleanly but skipped by strict quality gate -> no LLM call."""
        from src.deepline_discovery_runner import DeeplineDiscoveryRunner
        app_engine, icp_engine = tmp_stores

        mock_client = MagicMock()
        mock_client.discover_leads.return_value = {
            "status": "SUCCESS",
            "leads": [
                {"linkedin_url": "https://www.linkedin.com/in/unverified", "email": "guess@co.in", "email_status": "UNVERIFIED", "contact_name": "Unverified User", "company_name": "Co", "city": "Chandigarh", "country": "India", "job_title": "CEO"}
            ]
        }
        mock_client.enrich_lead_emails.side_effect = lambda leads: leads

        runner = DeeplineDiscoveryRunner(
            deepline_client=mock_client,
            approval_engine=app_engine,
            icp_approval_engine=icp_engine,
        )

        with patch("src.integrations.bedrock_client.BedrockClient.generate_email_1",
                   side_effect=AssertionError("DeepSeek must not be called for UNVERIFIED email")):
            result = runner.run_discovery_pipeline(icp=minimal_icp, requested_count=5)

        assert result["summary"]["created"] == 1
        queue = app_engine.store.load_queue()
        assert len(queue) == 1
        assert queue[0].email_status == "UNVERIFIED"
        assert queue[0].approval_stage == "EMAIL_STATUS_APPROVAL"

    def test_verified_email_passes_quality_gate(self, tmp_stores, minimal_icp):
        """VERIFIED email passes quality gate into downstream pipeline."""
        from src.deepline_discovery_runner import DeeplineDiscoveryRunner
        app_engine, icp_engine = tmp_stores

        mock_client = MagicMock()
        mock_client.discover_leads.return_value = {
            "status": "SUCCESS",
            "leads": [
                {"linkedin_url": "https://www.linkedin.com/in/verified", "email": "verified@co.in", "email_status": "VERIFIED", "contact_name": "Verified User", "company_name": "Co", "city": "Chandigarh", "country": "India", "job_title": "CEO"}
            ]
        }
        mock_client.enrich_lead_emails.side_effect = lambda leads: leads

        runner = DeeplineDiscoveryRunner(
            deepline_client=mock_client,
            approval_engine=app_engine,
            icp_approval_engine=icp_engine,
        )

        mock_llm_obj = MagicMock()
        mock_llm_obj.body = "Sample Email Body Text"
        mock_llm_obj.subject = "Sample Subject"

        with patch("src.integrations.bedrock_client.BedrockClient.generate_email_1", return_value=mock_llm_obj):
            with patch("src.integrations.bedrock_client.BedrockClient.generate_followup_a", return_value=mock_llm_obj):
                with patch("src.integrations.bedrock_client.BedrockClient.generate_followup_b", return_value=mock_llm_obj):
                    result = runner.run_discovery_pipeline(icp=minimal_icp, requested_count=5)

        assert result["summary"]["created"] == 1
        assert len(app_engine.store.load_queue()) == 1


# ---------------------------------------------------------------------------
# Test Group 3: Cross-Platform Executable Resolution & Subprocess Execution
# ---------------------------------------------------------------------------

class TestExecutableResolution:
    """Verifies resolution of 'deepline' vs 'deepline.cmd' cross-platform for subprocess execution."""

    def test_deepline_resolves_normally(self):
        from src.integrations.deepline_client import DeeplineClient
        with patch("shutil.which", side_effect=lambda x: "/usr/local/bin/deepline" if x == "deepline" else None):
            with patch("sys.platform", "linux"):
                exe, use_shell = DeeplineClient.resolve_deepline_executable()
                assert exe == "/usr/local/bin/deepline"
                assert use_shell is False

    def test_deepline_cmd_resolves_on_windows(self):
        from src.integrations.deepline_client import DeeplineClient
        def mock_which(cmd):
            if cmd == "deepline":
                return None
            if cmd == "deepline.cmd":
                return r"C:\Users\test\AppData\Roaming\npm\deepline.cmd"
            return None

        with patch("shutil.which", side_effect=mock_which):
            with patch("sys.platform", "win32"):
                exe, use_shell = DeeplineClient.resolve_deepline_executable()
                assert exe == r"C:\Users\test\AppData\Roaming\npm\deepline.cmd"
                assert use_shell is True

    def test_neither_resolves_fallback(self):
        from src.integrations.deepline_client import DeeplineClient
        with patch("shutil.which", return_value=None):
            with patch("sys.platform", "win32"):
                exe, use_shell = DeeplineClient.resolve_deepline_executable()
                assert exe == "deepline.cmd"
                assert use_shell is True

    def test_resolved_executable_passed_to_subprocess(self):
        from src.integrations.deepline_client import DeeplineClient
        client = DeeplineClient(api_key="test_key", live_mode=True)
        client.run_confirmed = True

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"email": "test@example.com", "email_validated": true, "email_found_and_valid": true}'

        with patch.object(DeeplineClient, "resolve_deepline_executable", return_value=("deepline.cmd", True)):
            with patch("subprocess.run", return_value=mock_proc) as mock_sub:
                res = client.enrich_single_lead_email({"linkedin_url": "https://www.linkedin.com/in/testuser"})
                assert res["email"] == "test@example.com"
                assert res["email_status"] == "VERIFIED"
                mock_sub.assert_called_once()
                args, kwargs = mock_sub.call_args
                cmd_list = args[0]
                assert cmd_list[0] == "deepline.cmd"
                assert kwargs.get("shell") is True


# ---------------------------------------------------------------------------
# Test Group 4: Dual Envelope Format Response Parsing
# ---------------------------------------------------------------------------

class TestEnvelopeParserFormats:
    """Verifies parsing of both Deepline outputs envelope format and direct response format."""

    def test_format_a_deepline_outputs_envelope(self):
        """Format A: outputs.email.value structure returned by Deepline CLI plays."""
        from src.integrations.deepline_client import DeeplineClient
        client = DeeplineClient(api_key="test_key", live_mode=True)
        
        lead_input = {
            "linkedin_url": "https://www.linkedin.com/in/person",
            "mock_play_response": {
                "outputs": {
                    "email": {"value": "person@company.com"},
                    "email_found_and_valid": {"value": True},
                    "email_validated": {"value": True},
                    "email_source": {"value": "prospeo_verified_email"}
                }
            }
        }
        res = client.enrich_single_lead_email(lead_input)
        assert res["email"] == "person@company.com"
        assert res["email_status"] == "VERIFIED"
        assert res["email_found_and_valid"] is True
        assert res["email_validated"] is True
        assert res["email_source"] == "prospeo_verified_email"
        assert res["enrichment_status"] == "SUCCESS"

    def test_format_b_direct_keys(self):
        """Format B: direct top-level keys structure."""
        from src.integrations.deepline_client import DeeplineClient
        client = DeeplineClient(api_key="test_key", live_mode=True)
        
        lead_input = {
            "linkedin_url": "https://www.linkedin.com/in/person",
            "mock_play_response": {
                "email": "person@company.com",
                "email_found_and_valid": True,
                "email_validated": True,
                "email_source": "existing_source"
            }
        }
        res = client.enrich_single_lead_email(lead_input)
        assert res["email"] == "person@company.com"
        assert res["email_status"] == "VERIFIED"
        assert res["email_found_and_valid"] is True
        assert res["email_validated"] is True
        assert res["email_source"] == "existing_source"

    def test_no_email_returned_safely(self):
        """No email returned in outputs envelope returns NO_EMAIL without exception."""
        from src.integrations.deepline_client import DeeplineClient
        client = DeeplineClient(api_key="test_key", live_mode=True)
        
        lead_input = {
            "linkedin_url": "https://www.linkedin.com/in/person",
            "mock_play_response": {
                "outputs": {
                    "email": {"value": ""},
                    "email_found_and_valid": {"value": False},
                    "email_validated": {"value": False}
                }
            }
        }
        res = client.enrich_single_lead_email(lead_input)
        assert res["email"] == ""
        assert res["email_status"] == "NO_EMAIL"
        assert res["enrichment_status"] == "NO_EMAIL_FOUND"

    def test_malformed_missing_outputs(self):
        """Malformed or missing outputs object does not crash parser."""
        from src.integrations.deepline_client import DeeplineClient
        client = DeeplineClient(api_key="test_key", live_mode=True)
        
        lead_input = {
            "linkedin_url": "https://www.linkedin.com/in/person",
            "mock_play_response": {
                "outputs": "invalid_type",
                "unexpected_field": True
            }
        }
        res = client.enrich_single_lead_email(lead_input)
        assert res["email"] == ""
        assert res["email_status"] == "NO_EMAIL"


