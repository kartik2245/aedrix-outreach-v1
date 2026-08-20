"""
test_api.py
Automated test suite for FastAPI backend endpoints.
Verifies all routes, approval actions, search/filtering, safety indicators, and demo pipeline execution.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.approval.approval_store import ApprovalStore
from src.approval.approval_engine import ApprovalEngine


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_queue(tmp_path, monkeypatch):
    """Ensures test queue is isolated and populated for tests."""
    monkeypatch.setenv("DATABASE_ENABLED", "false")
    test_queue_file = tmp_path / "test_queue.json"
    store = ApprovalStore(storage_path=str(test_queue_file))
    engine = ApprovalEngine(store=store)

    # Enroll sample test leads
    engine.enroll_draft(
        company="Kier Group plc",
        contact="Colin Bell",
        title="Digital Director",
        email="c.bell@kier.co.uk",
        qualification_status="QUALIFIED",
        opportunity_score=87.0,
        accessibility_score=78.0,
        outreach_priority_index=83.4,
        priority="P2",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Digital by Default strategy.",
        voc_angle="Digital Transformation",
        email_1="Hi Colin, email 1",
        followup_a="Hi Colin, followup a",
        followup_b="Hi Colin, followup b",
        qa_status="PASS"
    )

    engine.enroll_draft(
        company="Bowmer & Kirkland",
        contact="John Foster",
        title="Business Improvement Director",
        email="j.foster@bandk.co.uk",
        qualification_status="QUALIFIED",
        opportunity_score=89.0,
        accessibility_score=88.0,
        outreach_priority_index=88.6,
        priority="P1",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Saw digital team expansion.",
        voc_angle="Pre-construction",
        email_1="Hi John, email 1",
        followup_a="Hi John, followup a",
        followup_b="Hi John, followup b",
        qa_status="PASS"
    )

    # Mock ApprovalStore in API routers to use this isolated store
    monkeypatch.setattr("src.approval.approval_store.ApprovalStore.__init__", lambda self, storage_path=None: setattr(self, "storage_path", str(test_queue_file)))


def test_1_health_check(client):
    """GET /api/health returns healthy status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["safety_guard"] == "SEND_EMAILS=false"


def test_2_dashboard_stats(client):
    """GET /api/dashboard/stats returns aggregated stats and safety flags."""
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] == 2
    assert data["qualified_leads"] == 2
    assert data["p1_leads"] == 1
    assert data["p2_leads"] == 1
    assert data["safety"]["real_emails_sent"] == 0
    assert data["safety"]["send_emails"] is False


def test_3_list_leads_and_filtering(client):
    """GET /api/leads supports pagination, priority filtering, and search."""
    # List all
    res = client.get("/api/leads")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2

    # Filter by Priority P1
    res_p1 = client.get("/api/leads?priority=P1")
    assert res_p1.status_code == 200
    assert res_p1.json()["total"] == 1
    assert res_p1.json()["items"][0]["company"] == "Bowmer & Kirkland"

    # Search
    res_search = client.get("/api/leads?search=Kier")
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["company"] == "Kier Group plc"


def test_4_get_lead_detail(client):
    """GET /api/leads/{lead_id} returns complete lead dossier."""
    res = client.get("/api/leads/lead_kier_group_plc_colin_bell")
    assert res.status_code == 200
    data = res.json()
    assert data["lead_id"] == "lead_kier_group_plc_colin_bell"
    assert data["company"] == "Kier Group plc"
    assert data["contact"] == "Colin Bell"
    assert "email_1" in data
    assert "followup_a" in data
    assert "followup_b" in data
    assert data["qa_status"] == "PASS"


def test_5_get_lead_detail_404(client):
    """GET /api/leads/{lead_id} returns 404 for nonexistent lead."""
    res = client.get("/api/leads/non_existent_lead_id")
    assert res.status_code == 404


def test_6_approval_workflow_approve_edit_reapprove(client):
    """Test full human approval workflow: Approve -> Edit (transitions to EDITED) -> Re-approve."""
    lead_id = "lead_bowmer_kirkland_john_foster"

    # 1. Approve lead
    app_res = client.post(f"/api/approvals/{lead_id}/approve", json={"reviewer": "Sarah Campaign Lead"})
    assert app_res.status_code == 200
    assert app_res.json()["record"]["approval_status"] == "APPROVED"
    assert app_res.json()["record"]["smartlead_eligible"] is True

    # 2. Edit lead draft (must revert smartlead_eligible to False and status to EDITED)
    edit_res = client.post(
        f"/api/approvals/{lead_id}/edit",
        json={"email_1": "Custom human edited email copy", "reviewer": "Editor"}
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["record"]["approval_status"] == "EDITED"
    assert edit_res.json()["record"]["smartlead_eligible"] is False
    assert edit_res.json()["record"]["edited_email_1"] == "Custom human edited email copy"

    # 3. Re-approve edited draft
    reapp_res = client.post(f"/api/approvals/{lead_id}/approve", json={"reviewer": "Final Reviewer"})
    assert reapp_res.status_code == 200
    assert reapp_res.json()["record"]["approval_status"] == "APPROVED"
    assert reapp_res.json()["record"]["smartlead_eligible"] is True


def test_7_reject_and_block_lead(client):
    """Test Reject and Block actions."""
    lead_id = "lead_kier_group_plc_colin_bell"

    # Reject
    rej_res = client.post(f"/api/approvals/{lead_id}/reject", json={"reason": "Not in current focus", "reviewer": "Op"})
    assert rej_res.status_code == 200
    assert rej_res.json()["record"]["approval_status"] == "REJECTED"
    assert rej_res.json()["record"]["smartlead_eligible"] is False

    # Block
    blk_res = client.post(f"/api/approvals/{lead_id}/block", json={"reason": "Disqualified", "reviewer": "Op"})
    assert blk_res.status_code == 200
    assert blk_res.json()["record"]["approval_status"] == "BLOCKED"
    assert blk_res.json()["record"]["smartlead_eligible"] is False


def test_8_campaign_flow_endpoint(client):
    """GET /api/campaign returns flow steps, 2-day wait, and state machine definitions."""
    res = client.get("/api/campaign")
    assert res.status_code == 200
    data = res.json()
    assert len(data["steps"]) >= 4
    assert data["steps"][1]["delay_days"] == 2  # 2-day initial wait rule
    assert len(data["all_states"]) == 25


def test_9_smartlead_staging_endpoint(client):
    """GET /api/smartlead/staging returns staging plan with 0 API calls."""
    res = client.get("/api/smartlead/staging")
    assert res.status_code == 200
    data = res.json()
    assert data["safety_status"]["api_calls_made"] == 0
    assert data["safety_status"]["real_emails_sent"] == 0


def test_10_system_status_endpoint(client):
    """GET /api/system/status returns masked credentials and integration matrix."""
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert len(data["integrations"]) == 4
    assert data["safety_flags"]["SEND_EMAILS"] is False
    assert "ANTHROPIC_API_KEY" in data["masked_env"]
    assert "SMARTLEAD_API_KEY" in data["masked_env"]


def test_11_demo_run_endpoint(client):
    """POST /api/demo/run executes local demo pipeline with 0 real emails sent."""
    res = client.post("/api/demo/run")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["summary"]["real_emails_sent"] == 0
    assert data["summary"]["api_calls_made"] == 0
    assert data["summary"]["records_processed"] >= 5
