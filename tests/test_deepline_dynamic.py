"""
test_deepline_dynamic.py
Integration tests for Deepline Dynamic Lead Discovery, safety gates, artifact persistence, and end-to-end pipeline execution.
"""

import os
import json
import pytest
from unittest.mock import MagicMock

from src.icp.icp_models import ICPConfig, ICPStatus, DeeplineDiscoveryRequest
from src.icp.icp_designer import ICPDesigner
from src.icp.icp_approval_engine import ICPApprovalEngine
from src.icp.icp_engine import ICPEngine
from src.icp.icp_approval_store import ICPApprovalStore
from src.integrations.deepline_client import DeeplineClient, DeeplineAuthError, DeeplineAPIError
from src.deepline_discovery_runner import DeeplineDiscoveryRunner
from src.deepline_export_adapter import DeeplineExportAdapter
from src.approval.approval_store import ApprovalStore
from src.approval.approval_engine import ApprovalEngine


@pytest.fixture
def test_setup(tmp_path):
    icp_queue_file = tmp_path / "test_icp_queue.json"
    approval_queue_file = tmp_path / "test_approval_queue.json"

    icp_store = ICPApprovalStore(storage_path=str(icp_queue_file))
    icp_engine = ICPApprovalEngine(store=icp_store)

    app_store = ApprovalStore(storage_path=str(approval_queue_file))
    app_engine = ApprovalEngine(store=app_store)

    return {
        "icp_engine": icp_engine,
        "app_engine": app_engine,
        "tmp_path": tmp_path
    }


def test_1_deepline_request_mapping_from_icp():
    """Verify ICPConfig maps cleanly to DeeplineDiscoveryRequest."""
    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="UK Civil Infrastructure",
        campaign_objective="Target civil contractors",
        industry="Civil Engineering, Rail, Highway",
        target_personas=["Head of BIM", "Digital Engineering Lead"],
        positive_signals=["Rail infrastructure project award"]
    )

    req = DeeplineDiscoveryRequest(
        icp_id=icp.id,
        campaign_id=icp.campaign_id,
        campaign_name=icp.name,
        geography=icp.geography.allowed_country_keywords,
        industries=icp.industries,
        company_size=icp.company_size,
        personas=icp.target_personas,
        positive_signals=icp.positive_signals,
        exclusions=[c.description for c in icp.campaign_exclusions],
        requested_lead_count=100
    )

    assert req.icp_id == icp.id
    assert req.requested_lead_count == 100
    assert "Civil Engineering" in req.industries[0]
    assert "Head of BIM" in req.personas


def test_2_unapproved_icp_blocks_deepline_execution(test_setup):
    """CRITICAL SAFETY: Cannot execute Deepline discovery on unapproved ICP."""
    designer = ICPDesigner()
    icp = designer.design_icp(campaign_name="Unapproved Test", campaign_objective="Test")
    test_setup["icp_engine"].enroll_icp(icp)

    runner = DeeplineDiscoveryRunner(
        icp_approval_engine=test_setup["icp_engine"],
        approval_engine=test_setup["app_engine"]
    )

    with pytest.raises(ValueError, match="Cannot execute Deepline discovery on unapproved ICP"):
        runner.run_discovery_pipeline(icp=icp, requested_count=100)


def test_3_dry_run_discovery_multi_lead_simulation(test_setup):
    """Verify dry-run Deepline discovery generates 100 simulated leads without API calls."""
    designer = ICPDesigner()
    icp = designer.design_icp(campaign_name="Dry Run 100 Leads", campaign_objective="Test", geography="United Kingdom", industry="Construction")
    record = test_setup["icp_engine"].enroll_icp(icp)
    approved_record = test_setup["icp_engine"].approve_icp(record.icp_id, reviewer="Admin")

    deepline_client = DeeplineClient(live_mode=False)

    runner = DeeplineDiscoveryRunner(
        deepline_client=deepline_client,
        icp_approval_engine=test_setup["icp_engine"],
        approval_engine=test_setup["app_engine"]
    )

    res = runner.run_discovery_pipeline(icp=approved_record.effective_icp, requested_count=100)

    assert res["summary"]["discovered"] == 100
    assert res["summary"]["qualified"] > 0
    assert "run_id" in res
    assert os.path.exists(res["run_artifacts_path"])

    # Verify run artifacts
    artifacts = os.listdir(res["run_artifacts_path"])
    assert "icp.json" in artifacts
    assert "discovery_request.json" in artifacts
    assert "export.json" in artifacts
    assert "run_metadata.json" in artifacts

    # Verify leads enrolled into approval queue (10 unique companies simulated across 100 leads)
    approval_records = test_setup["app_engine"].store.load_queue()
    assert len(approval_records) == 10
    assert all(r.metadata.get("campaign_id") == icp.campaign_id for r in approval_records)


def test_4_live_mode_blocked_without_api_key(monkeypatch):
    """Verify live Deepline mode without API key raises DeeplineAuthError."""
    monkeypatch.setenv("DEEPLINE_LIVE", "true")
    monkeypatch.delenv("DEEPLINE_API_KEY", raising=False)
    monkeypatch.delenv("DEEPLINE_SESSION_TOKEN", raising=False)

    client = DeeplineClient(live_mode=True, api_key="")
    client.api_key = ""
    req = DeeplineDiscoveryRequest(
        icp_id="test",
        campaign_id="test",
        campaign_name="test",
        geography=["UK"],
        industries=["Construction"],
        company_size="100+",
        personas=["CIO"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=100
    )

    with pytest.raises(DeeplineAuthError, match="DEEPLINE_API_KEY is required"):
        client.discover_leads(req)


def test_5_live_mode_requires_run_confirmation(monkeypatch):
    """Verify live Deepline mode requires explicit confirmation flag."""
    monkeypatch.setenv("DEEPLINE_LIVE", "true")
    monkeypatch.setenv("DEEPLINE_RUN_CONFIRMATION", "false")

    client = DeeplineClient(live_mode=True, api_key="dp_live_12345678")
    client.run_confirmed = False
    req = DeeplineDiscoveryRequest(
        icp_id="test",
        campaign_id="test",
        campaign_name="test",
        geography=["UK"],
        industries=["Construction"],
        company_size="100+",
        personas=["CIO"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=100
    )

    with pytest.raises(DeeplineAPIError, match="DEEPLINE_RUN_CONFIRMATION must be set to 'true'"):
        client.discover_leads(req)


def test_6_deepline_v2_payload_building_and_masking():
    """Verify Deepline V2 payload mapping and API key masking."""
    client = DeeplineClient(api_key="dp_live_secret_key_12345")
    masked = client.mask_api_key(client.api_key)
    assert masked.endswith("2345")
    assert "secret" not in masked

    req = DeeplineDiscoveryRequest(
        icp_id="icp_v2_001",
        campaign_id="camp_v2_001",
        campaign_name="Civil Construction V2",
        geography=["United Kingdom"],
        industries=["Civil Engineering"],
        company_size="500-1000 employees",
        personas=["Digital Construction Director"],
        positive_signals=["BIM Level 2 mandate"],
        exclusions=[],
        requested_lead_count=25
    )

    v2_payload = client.build_v2_payload(req)
    assert "payload" in v2_payload
    account = v2_payload["payload"]["account"]
    contact = v2_payload["payload"]["contact"]

    # Assert 1. UK geography mapping
    assert account["location"]["any"]["include"] == ["United Kingdom"]
    assert "country" not in account["location"]["any"]

    # Assert 2. Industry mapping via account.keyword
    assert account["keyword"]["any"]["include"]["content"] == ["Civil Engineering"]
    assert account["keyword"]["any"]["include"]["sources"] == [{"mode": "SMART", "source": "INDUSTRY"}]
    assert "industries" not in account

    # Assert 3. Employee range mapping (500-1000 employees)
    assert account["employeeSize"]["type"] == "RANGE"
    assert account["employeeSize"]["range"][0]["start"] == 500
    assert account["employeeSize"]["range"][0]["end"] == 1000

    # Assert 4. Persona mapping via contact.keyword
    assert contact["keyword"]["any"]["include"]["content"] == ["Digital Construction Director"]
    assert contact["keyword"]["any"]["include"]["sources"] == [{"mode": "SMART", "source": "HEADLINE"}]
    assert "title" not in contact

    # Assert 5. requested_lead_count -> size mapping
    assert v2_payload["payload"]["size"] == 25

    # Assert 6. Root page field mapping
    assert v2_payload["payload"]["page"] == 0

    # Assert 7. Root keys set
    root_keys = set(v2_payload["payload"].keys())
    assert root_keys == {"page", "size", "account", "contact"}

    # Assert 8. No unsupported fields emitted inside account
    assert "size" not in account
    assert "revenue" not in account


def test_7_mocked_deepline_v2_api_call(monkeypatch):
    """Verify mocked Deepline V2 API response parsing."""
    client = DeeplineClient(api_key="dp_live_12345678", live_mode=True)
    client.run_confirmed = True

    mock_response_data = {
        "toolExecutionResult": {
            "extractedLists": [
                {
                    "name": "content",
                    "items": [
                        {
                            "company": "Kier Group plc",
                            "domain": "kier.co.uk",
                            "location": "United Kingdom",
                            "full_name": "Colin Bell",
                            "title": "Digital Director",
                            "email": "c.bell@kier.co.uk",
                            "linkedin": "https://linkedin.com/in/colin-bell",
                            "size": "11000 employees"
                        }
                    ]
                }
            ]
        }
    }

    class MockHTTPResponse:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def read(self):
            return json.dumps(mock_response_data).encode("utf-8")

    def mock_urlopen(req, timeout=30.0):
        return MockHTTPResponse()

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    req = DeeplineDiscoveryRequest(
        icp_id="test_icp",
        campaign_id="test_camp",
        campaign_name="Test",
        geography=["UK"],
        industries=["Construction"],
        company_size="100+",
        personas=["Director"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )

    res = client.discover_leads(req)
    assert res["status"] == "SUCCESS"
    assert res["mode"] == "LIVE_API_V2"
    assert len(res["leads"]) == 1
    assert res["leads"][0]["company"] == "Kier Group plc"


def test_8_deepline_v2_api_endpoint_construction(monkeypatch):
    """Verify DeeplineClient constructs the canonical V2 API endpoint and passes required V2 headers."""
    client = DeeplineClient(api_key="dp_live_secret_key_99999", base_url="https://code.deepline.com/api/v2", live_mode=True)
    client.run_confirmed = True
    assert client.base_url == "https://code.deepline.com/api/v2"

    req = DeeplineDiscoveryRequest(
        icp_id="test_icp",
        campaign_id="test_camp",
        campaign_name="Test",
        geography=["United Kingdom"],
        industries=["Commercial Construction"],
        company_size="50+ employees",
        personas=["Digital Director", "IT Director"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )

    captured_req = []
    class MockHTTPResponse:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def read(self):
            return json.dumps({"leads": []}).encode("utf-8")

    def mock_urlopen(r, timeout=30.0):
        captured_req.append(r)
        return MockHTTPResponse()

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    client.discover_leads(req)

    # Assert 9. Final endpoint, headers, and lists field remain correct
    assert len(captured_req) == 1
    sent_req = captured_req[0]
    assert sent_req.full_url == "https://code.deepline.com/api/v2/integrations/ai_ark_people_search/execute"
    assert sent_req.get_method() == "POST"
    assert sent_req.headers.get("Authorization") == "Bearer dp_live_secret_key_99999"
    assert sent_req.headers.get("X-deepline-execute-response-contract") == "v2-tool-response"
    assert sent_req.headers.get("X-deepline-tool-error-schema") == "1"
    payload_data = json.loads(sent_req.data.decode("utf-8"))
    payload = payload_data["payload"]
    assert payload["page"] == 0
    assert payload["size"] == 1

    # Assert exact account & contact structures
    assert payload["account"]["location"]["any"]["include"] == ["United Kingdom"]
    assert "country" not in payload["account"]["location"]["any"]

    assert payload["account"]["employeeSize"] == {
        "type": "RANGE",
        "range": [{"start": 50, "end": 10000}]
    }

    assert payload["account"]["keyword"]["any"]["include"] == {
        "content": ["Commercial Construction"],
        "sources": [{"mode": "SMART", "source": "INDUSTRY"}]
    }
    assert "industries" not in payload["account"]

    assert payload["contact"]["keyword"]["any"]["include"] == {
        "content": ["Digital Director", "IT Director"],
        "sources": [{"mode": "SMART", "source": "HEADLINE"}]
    }
    assert "title" not in payload["contact"]


def test_9_deepline_v2_http_422_response_body_preservation(monkeypatch):
    """Verify DeeplineClient preserves and logs the HTTP 422 error response body when an HTTPError occurs."""
    import io
    import urllib.error

    client = DeeplineClient(api_key="dp_live_secret_key_77777", live_mode=True)
    client.run_confirmed = True

    mock_error_body = json.dumps({
        "statusCode": 422,
        "error": "Unprocessable Entity",
        "message": "Invalid schema at payload.account.location: expected object"
    })

    fp = io.BytesIO(mock_error_body.encode("utf-8"))
    mock_http_error = urllib.error.HTTPError(
        url="https://code.deepline.com/api/v2/integrations/ai_ark_people_search/execute",
        code=422,
        msg="Unprocessable Entity",
        hdrs={},
        fp=fp
    )

    def mock_urlopen_raise(req, timeout=30.0):
        raise mock_http_error

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen_raise)

    req = DeeplineDiscoveryRequest(
        icp_id="test_icp",
        campaign_id="test_camp",
        campaign_name="Test",
        geography=["UK"],
        industries=["Construction"],
        company_size="100+",
        personas=["Director"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )

    with pytest.raises(DeeplineAPIError) as exc_info:
        client.discover_leads(req)

    err_str = str(exc_info.value)
    assert "HTTP 422" in err_str
    assert "Unprocessable Entity" in err_str
    assert "Invalid schema at payload.account.location" in err_str


def test_10_deepline_v2_tool_response_raw_content_parsing(monkeypatch):
    """Verify DeeplineClient correctly extracts leads from toolResponse.raw.content V2 wrapper format."""
    client = DeeplineClient(api_key="dp_live_12345678", live_mode=True)
    client.run_confirmed = True

    mock_tool_response = {
        "toolResponse": {
            "raw": {
                "content": [
                    {
                        "full_name": "Jon Ozanne",
                        "title": "Chief Information Officer",
                        "company_name": "Balfour Beatty plc",
                        "company_domain": "balfourbeatty.com",
                        "company_location": "London, UK",
                        "email": "j.ozanne@balfourbeatty.com"
                    }
                ]
            }
        }
    }

    class MockHTTPResponse:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def read(self):
            return json.dumps(mock_tool_response).encode("utf-8")

    def mock_urlopen(req, timeout=30.0):
        return MockHTTPResponse()

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    req = DeeplineDiscoveryRequest(
        icp_id="test_icp",
        campaign_id="test_camp",
        campaign_name="Test",
        geography=["United Kingdom"],
        industries=["Commercial Construction"],
        company_size="50+ employees",
        personas=["CIO"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )

    res = client.discover_leads(req)
    assert res["status"] == "SUCCESS"
    assert res["discovered_count"] == 1
    assert len(res["leads"]) == 1
    assert res["leads"][0]["full_name"] == "Jon Ozanne"


def test_11_deepline_full_offline_pipeline_verification(monkeypatch, test_setup):
    """Verify offline end-to-end extraction, lead conversion, qualification, and approval enrollment."""
    client = DeeplineClient(api_key="dp_live_12345678", live_mode=True)
    client.run_confirmed = True

    mock_v2_response = {
        "toolResponse": {
            "raw": {
                "content": [
                    {
                        "id": "test-lead-001",
                        "profile": {
                            "first_name": "Test",
                            "last_name": "Lead",
                            "full_name": "Test Lead",
                            "title": "Digital Director"
                        },
                        "link": {
                            "linkedin": "https://linkedin.com/in/test-lead"
                        },
                        "email": "test@testconstruction.co.uk",
                        "email_status": "EVIDENCE_VERIFIED",
                        "company": {
                            "summary": {
                                "name": "Test Construction Ltd"
                            },
                            "link": {
                                "domain": "testconstruction.co.uk"
                            },
                            "location": "United Kingdom",
                            "industry": "Commercial Construction",
                            "company_size": "500 employees",
                            "is_uk_operating": True,
                            "is_construction_sector": True
                        }
                    }
                ]
            }
        }
    }

    class MockHTTPResponse:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def read(self):
            return json.dumps(mock_v2_response).encode("utf-8")

    def mock_urlopen(req, timeout=30.0):
        return MockHTTPResponse()

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # 1. DeeplineClient extracts exactly 1 lead from fixture
    req = DeeplineDiscoveryRequest(
        icp_id="icp_offline_001",
        campaign_id="camp_offline_001",
        campaign_name="Offline Test",
        geography=["United Kingdom"],
        industries=["Commercial Construction"],
        company_size="50+ employees",
        personas=["Digital Director"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )

    res = client.discover_leads(req)
    assert res["status"] == "SUCCESS"
    assert res["discovered_count"] == 1
    assert len(res["leads"]) == 1

    # 2. Extracted record converted via DeeplineExportAdapter
    adapter = DeeplineExportAdapter()
    adapted_lead = adapter.adapt_record(res["leads"][0])
    assert adapted_lead["company_name"] == "Test Construction Ltd"
    assert adapted_lead["company_domain"] == "testconstruction.co.uk"
    assert adapted_lead["contact_name"] == "Test Lead"
    assert adapted_lead["job_title"] == "Digital Director"
    assert adapted_lead["linkedin_url"] == "https://linkedin.com/in/test-lead"

    # 3. Qualification via ICPEngine
    designer = ICPDesigner()
    icp = designer.design_icp(campaign_name="Offline Verification", campaign_objective="Test", geography="United Kingdom", industry="Construction")
    icp_record = test_setup["icp_engine"].enroll_icp(icp)
    approved_icp_record = test_setup["icp_engine"].approve_icp(icp_record.icp_id, reviewer="Admin")

    icp_engine = ICPEngine(approved_icp_record.effective_icp)
    qual_res = icp_engine.evaluate_lead(adapted_lead)
    assert qual_res.status.value == "QUALIFIED"

    # 4. Approval Enrollment via DeeplineDiscoveryRunner (with mocked LLM)
    class MockLLMClient:
        def generate_email_1(self, lead, voc, icp_config=None):
            class Email: body = "Test Email Body"
            return Email()
        def generate_followup_a(self, lead, e1, voc, icp_config=None):
            class Email: body = "Test Followup A Body"
            return Email()
        def generate_followup_b(self, lead, voc, icp_config=None):
            class Email: body = "Test Followup B Body"
            return Email()

    runner = DeeplineDiscoveryRunner(
        deepline_client=client,
        approval_engine=test_setup["app_engine"],
        icp_approval_engine=test_setup["icp_engine"],
        llm_client=MockLLMClient()
    )

    pipeline_res = runner.run_discovery_pipeline(icp=approved_icp_record.effective_icp, requested_count=1)
    assert pipeline_res["summary"]["discovered"] == 1
    assert pipeline_res["summary"]["qualified"] == 1

    # Verify enrolled approval record
    enrolled = test_setup["app_engine"].store.load_queue()
    matching = [r for r in enrolled if r.contact == "Test Lead"]
    assert len(matching) == 1
    assert matching[0].company == "Test Construction Ltd"
    assert matching[0].title == "Digital Director"


def test_12_real_ai_ark_response_regression(monkeypatch, test_setup):
    """Verify complete AEDRIX pipeline using the exact real AI Ark response schema and fields."""
    client = DeeplineClient(api_key="dp_live_12345678", live_mode=True)
    client.run_confirmed = True

    # High-fidelity captured AI Ark response fixture matching toolResult metadata
    real_ai_ark_fixture = {
        "toolResponse": {
            "raw": {
                "content": [
                    {
                        "id": "ai_ark_lead_uk_001",
                        "profile": {
                            "first_name": "Jon",
                            "last_name": "Ozanne",
                            "full_name": "Jon Ozanne",
                            "title": "Chief Information Officer",
                            "headline": "Chief Information Officer at Balfour Beatty plc"
                        },
                        "link": {
                            "linkedin": "https://www.linkedin.com/in/jon-ozanne-balfourbeatty"
                        },
                        "company": {
                            "summary": {
                                "name": "Balfour Beatty plc"
                            },
                            "link": {
                                "domain": "balfourbeatty.com"
                            },
                            "location": "London, United Kingdom",
                            "industry": "Commercial Construction & Infrastructure",
                            "company_size": "26000 employees",
                            "employee_count": 26000,
                            "is_uk_operating": True,
                            "is_construction_sector": True
                        },
                        "location": "London, United Kingdom",
                        "email": "j.ozanne@balfourbeatty.com",
                        "mock_play_response": {"email": "j.ozanne@balfourbeatty.com", "email_validated": True, "email_found_and_valid": True, "email_source": "pre_indexed"},
                        "skills": ["Digital Construction", "BIM", "Enterprise IT Strategy", "Civil Infrastructure"]
                    }
                ]
            }
        }
    }

    class MockHTTPResponse:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def read(self):
            return json.dumps(real_ai_ark_fixture).encode("utf-8")

    def mock_urlopen(req, timeout=30.0):
        return MockHTTPResponse()

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # 1. DeeplineClient.discover_leads() extracts exactly 1 lead
    req = DeeplineDiscoveryRequest(
        icp_id="icp_balfour_001",
        campaign_id="camp_balfour_001",
        campaign_name="UK Civil Infrastructure",
        geography=["United Kingdom"],
        industries=["Commercial Construction"],
        company_size="50+ employees",
        personas=["Chief Information Officer"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )

    discovery_res = client.discover_leads(req)
    assert discovery_res["status"] == "SUCCESS"
    assert discovery_res["discovered_count"] == 1
    assert len(discovery_res["leads"]) == 1

    # 2. DeeplineExportAdapter converts real record into normalized Lead
    adapter = DeeplineExportAdapter()
    raw_record = discovery_res["leads"][0]
    adapted_lead = adapter.adapt_record(raw_record)

    assert adapted_lead["contact_name"] == "Jon Ozanne"
    assert adapted_lead["job_title"] == "Chief Information Officer"
    assert adapted_lead["company_name"] == "Balfour Beatty plc"
    assert adapted_lead["company_domain"] == "balfourbeatty.com"
    assert adapted_lead["linkedin_url"] == "https://www.linkedin.com/in/jon-ozanne-balfourbeatty"
    assert adapted_lead["email"] == "j.ozanne@balfourbeatty.com"
    assert adapted_lead["employee_count"] == 26000
    assert adapted_lead["country"] == "LONDON, UNITED KINGDOM"
    assert adapted_lead["is_uk_operating"] is True
    assert adapted_lead["is_construction_sector"] is True
    assert len(adapted_lead["adapter_audit"]["errors"]) == 0

    # 3. ICPEngine qualification check
    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="UK Infrastructure Campaign",
        campaign_objective="Target Tier-1 contractors",
        geography="United Kingdom",
        industry="Commercial Construction"
    )
    icp_record = test_setup["icp_engine"].enroll_icp(icp)
    approved_icp_record = test_setup["icp_engine"].approve_icp(icp_record.icp_id, reviewer="Admin")

    icp_engine = ICPEngine(approved_icp_record.effective_icp)
    qual_res = icp_engine.evaluate_lead(adapted_lead)
    assert qual_res.status.value == "QUALIFIED"

    # 4. DeeplineDiscoveryRunner & ApprovalEngine enrollment
    class MockLLMClient:
        def generate_email_1(self, lead, voc, icp_config=None):
            class Email: body = "Enterprise BIM Infrastructure Pitch"
            return Email()
        def generate_followup_a(self, lead, e1, voc, icp_config=None):
            class Email: body = "Followup A Pitch"
            return Email()
        def generate_followup_b(self, lead, voc, icp_config=None):
            class Email: body = "Followup B Pitch"
            return Email()

    runner = DeeplineDiscoveryRunner(
        deepline_client=client,
        approval_engine=test_setup["app_engine"],
        icp_approval_engine=test_setup["icp_engine"],
        llm_client=MockLLMClient()
    )

    pipeline_res = runner.run_discovery_pipeline(icp=approved_icp_record.effective_icp, requested_count=1)
    assert pipeline_res["summary"]["discovered"] == 1
    assert pipeline_res["summary"]["qualified"] == 1

    # Verify enrolled record in ApprovalEngine
    enrolled_records = test_setup["app_engine"].store.load_queue()
    matching = [r for r in enrolled_records if r.contact == "Jon Ozanne"]
    assert len(matching) == 1
    assert matching[0].company == "Balfour Beatty plc"
    assert matching[0].title == "Chief Information Officer"
    assert matching[0].email == "j.ozanne@balfourbeatty.com"


def test_13_parse_employee_range_regression():
    """Verify parse_employee_range accurately handles employee ranges, revenue strings, and defaults."""
    client = DeeplineClient()

    # 1. "50+ employees" -> start=50, end=10000
    res1 = client.parse_employee_range("50+ employees")
    assert res1 == {"type": "RANGE", "range": [{"start": 50, "end": 10000}]}

    # 2. "50-500 employees" -> start=50, end=500
    res2 = client.parse_employee_range("50-500 employees")
    assert res2 == {"type": "RANGE", "range": [{"start": 50, "end": 500}]}

    # 3. "50 to 500 employees" -> start=50, end=500
    res3 = client.parse_employee_range("50 to 500 employees")
    assert res3 == {"type": "RANGE", "range": [{"start": 50, "end": 500}]}

    # 4. "100 employees" -> start=100, end=10000
    res4 = client.parse_employee_range("100 employees")
    assert res4 == {"type": "RANGE", "range": [{"start": 100, "end": 10000}]}

    # 5. "50+ employees or £10M+ revenue" -> start=50, end=10000
    res5 = client.parse_employee_range("50+ employees or £10M+ revenue")
    assert res5 == {"type": "RANGE", "range": [{"start": 50, "end": 10000}]}

    # 6. None / Empty string -> start=50, end=10000
    res6 = client.parse_employee_range(None)
    assert res6 == {"type": "RANGE", "range": [{"start": 50, "end": 10000}]}
    res7 = client.parse_employee_range("")
    assert res7 == {"type": "RANGE", "range": [{"start": 50, "end": 10000}]}

    # 7. Controlled ICP payload generation check
    req = DeeplineDiscoveryRequest(
        icp_id="icp_ctrl_001",
        campaign_id="camp_ctrl_001",
        campaign_name="Live 1-Lead Verification Campaign",
        geography=["United Kingdom"],
        industries=["Commercial Construction"],
        company_size="50+ employees or £10M+ revenue",
        personas=["Digital Director", "IT Director"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )

    payload = client.build_v2_payload(req)
    assert payload["payload"]["account"]["employeeSize"] == {
        "type": "RANGE",
        "range": [
            {
                "start": 50,
                "end": 10000
            }
        ]
    }


def test_14_icp_engine_respects_is_construction_sector_true_for_nonstandard_sic_labels():
    """
    Regression: AI Ark returned industry='Machinery' for a construction-adjacent company.
    The adapter set is_construction_sector=True via heuristic.
    ICPEngine previously hard-disqualified this lead as NON_CONSTRUCTION because 'machinery'
    was not in allowed_industry_keywords.
    After fix: when is_construction_sector=True, allowed_keywords backstop is skipped.
    """
    from src.models import DisqualificationStatus

    # Real live run lead shape (from export.json of run_20260820_140928_77eecc3c)
    lead = {
        "company_name": "Barkers Security Engineering",
        "company_domain": "barkersfencing.com",
        "country": "UNITED KINGDOM",
        "is_uk_operating": True,
        "industry": "Machinery",        # Non-standard SIC label returned by AI Ark
        "is_construction_sector": True, # Adapter heuristically set this to True
        "company_size": "UNKNOWN",
        "employee_count": None,
        "contact_name": "Sarah Lawton Clewlow",
        "job_title": "Operations Director",
        "email": "",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://www.linkedin.com/in/sarah-clewlow-9854021a5",
        "is_active_crm_deal": False,
        "is_global_suppressed": False,
        "contacted_within_60_days": False,
    }

    icp_engine = ICPEngine()
    result = icp_engine.evaluate_lead(lead)

    # After fix: is_construction_sector=True should bypass the keyword check.
    # The lead should NOT be hard-disqualified as NON_CONSTRUCTION.
    assert result.status != DisqualificationStatus.HARD_DISQUALIFIED or result.rule_code != "NON_CONSTRUCTION", (
        f"Lead was incorrectly hard-disqualified as NON_CONSTRUCTION despite is_construction_sector=True. "
        f"rule_code={result.rule_code}, reason={result.disqualification_reason}"
    )
    # The lead has employee_count=None and company_size='UNKNOWN', so it is unknown size.
    # It should NOT be disqualified for UNDER_SIZE_THRESHOLD (unknown size is not < min).
    # Overall, it should be QUALIFIED.
    assert result.status == DisqualificationStatus.QUALIFIED, (
        f"Lead should be QUALIFIED but got {result.status} / {result.rule_code}: {result.disqualification_reason}"
    )


def test_15_deepline_export_adapter_handles_dict_location_from_ai_ark():
    """
    Regression: AI Ark returned company.location as a dict:
    {'DEFAULT': 'BLYTHE BRIDGE, ENGLAND, UNITED KINGDOM, EUROPE', 'COUNTRY': 'UNITED KINGDOM', ...}
    Previously the adapter called str() on the dict producing a Python repr as the country field.
    After fix: the adapter extracts the 'COUNTRY' key when location is a dict.
    """
    adapter = DeeplineExportAdapter()

    # Simulate AI Ark raw record with dict-type location
    ai_ark_record = {
        "profile": {
            "first_name": "Sarah",
            "last_name": "Lawton Clewlow",
            "full_name": "Sarah Lawton Clewlow",
            "title": "Operations Director",
        },
        "company": {
            "summary": {"name": "Barkers Security Engineering"},
            "link": {"domain": "barkersfencing.com"},
            "location": {
                "DEFAULT": "BLYTHE BRIDGE, ENGLAND, UNITED KINGDOM, EUROPE",
                "SHORT": "BLYTHE BRIDGE, ENGLAND",
                "COUNTRY": "UNITED KINGDOM",
                "STATE": "ENGLAND",
                "CITY": "BLYTHE BRIDGE",
                "POSITION": None,
            },
        },
        "link": {
            "linkedin": "https://www.linkedin.com/in/sarah-clewlow-9854021a5",
        },
    }

    adapted = adapter.adapt_record(ai_ark_record)

    # After fix: country should be "UNITED KINGDOM", not a Python dict repr
    assert adapted["country"] == "UNITED KINGDOM", (
        f"Expected 'UNITED KINGDOM' but got: {adapted['country']!r}"
    )
    assert adapted["is_uk_operating"] is True, (
        f"Expected is_uk_operating=True but got: {adapted['is_uk_operating']}"
    )
    # Confirm country is NOT a Python dict repr
    assert not adapted["country"].startswith("{"), (
        f"country field contains raw Python dict repr: {adapted['country']!r}"
    )


def test_18_no_external_deepline_calls_during_dry_run(monkeypatch):
    """
    REGRESSION TEST (Requirement 12):
    Proves that when executing discovery in dry-run mode (DEEPLINE_LIVE=false),
    0 external HTTP/network calls are made to Deepline, 0 credits are consumed,
    and the client returns mode='DRY_RUN_SIMULATION' with deterministic fake leads.
    """
    call_tracker = []

    def failing_urlopen(req, *args, **kwargs):
        call_tracker.append(str(req))
        raise RuntimeError("CRITICAL ERROR: Live Deepline HTTP call attempted during dry-run test!")

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", failing_urlopen)
    monkeypatch.setenv("DEEPLINE_LIVE", "false")

    client = DeeplineClient()
    assert client.live_mode is False

    req = DeeplineDiscoveryRequest(
        icp_id="test_icp_offline",
        campaign_id="test_camp_offline",
        campaign_name="Offline Test",
        geography=["United Kingdom"],
        industries=["Commercial Construction"],
        company_size="50+ employees",
        personas=["Digital Director"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=10
    )

    res = client.discover_leads(req)
    assert res["status"] == "SUCCESS"
    assert res["mode"] == "DRY_RUN_SIMULATION"
    assert res["api_calls_made"] == 0
    assert res["credits_consumed"] == 0
    assert len(res["leads"]) == 10
    assert len(call_tracker) == 0, "No external urllib HTTP calls should have been made!"

