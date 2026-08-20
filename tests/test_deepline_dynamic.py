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
from src.icp.icp_approval_store import ICPApprovalStore
from src.integrations.deepline_client import DeeplineClient, DeeplineAuthError, DeeplineAPIError
from src.deepline_discovery_runner import DeeplineDiscoveryRunner
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
    icp = designer.design_icp(campaign_name="Dry Run 100 Leads", campaign_objective="Test")
    record = test_setup["icp_engine"].enroll_icp(icp)
    approved_record = test_setup["icp_engine"].approve_icp(record.icp_id, reviewer="Admin")

    runner = DeeplineDiscoveryRunner(
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

    # Verify leads enrolled into approval queue
    approval_records = test_setup["app_engine"].store.load_queue()
    assert len(approval_records) == res["summary"]["qualified"]
    assert all(r.metadata.get("campaign_id") == icp.campaign_id for r in approval_records)


def test_4_live_mode_blocked_without_api_key(monkeypatch):
    """Verify live Deepline mode without API key raises DeeplineAuthError."""
    monkeypatch.setenv("DEEPLINE_LIVE", "true")
    monkeypatch.delenv("DEEPLINE_API_KEY", raising=False)

    client = DeeplineClient(live_mode=True, api_key="")
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
