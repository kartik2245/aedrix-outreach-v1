"""
test_icp_api.py
Automated tests for FastAPI endpoints in app/api/icp.py.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from src.icp.icp_approval_store import ICPApprovalStore
from src.icp.icp_approval_engine import ICPApprovalEngine
from src.icp.icp_designer import ICPDesigner


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_isolated_icp_queue(tmp_path, monkeypatch):
    """Ensures test queue is isolated for API testing."""
    monkeypatch.setenv("DATABASE_ENABLED", "false")
    test_icp_file = tmp_path / "test_api_icp_queue.json"
    test_approval_file = tmp_path / "test_api_app_queue.json"

    # Pre-populate sample ICP
    store = ICPApprovalStore(storage_path=str(test_icp_file))
    engine = ICPApprovalEngine(store=store)
    designer = ICPDesigner()
    sample_icp = designer.design_icp(
        campaign_name="UK Building Contractors",
        campaign_objective="Target main contractors in England and Scotland",
        minimum_employees=50,
        minimum_revenue=10.0
    )
    engine.enroll_icp(sample_icp)

    monkeypatch.setattr(
        "src.icp.icp_approval_store.ICPApprovalStore.__init__",
        lambda self, storage_path=None: setattr(self, "storage_path", str(test_icp_file))
    )
    monkeypatch.setattr(
        "src.approval.approval_store.ApprovalStore.__init__",
        lambda self, storage_path=None: setattr(self, "storage_path", str(test_approval_file))
    )


def test_1_generate_icp_endpoint(client):
    """POST /api/icp/generate creates new ICP in PENDING_REVIEW status."""
    payload = {
        "campaign_name": "API Generated ICP",
        "campaign_objective": "Target UK construction leaders",
        "geography": "United Kingdom",
        "minimum_employees": 75,
        "minimum_revenue": 15.0,
        "target_personas": ["Digital Director", "CIO"]
    }
    res = client.post("/api/icp/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["status"] == "PENDING_REVIEW"
    assert data["icp"]["minimum_employees"] == 75


def test_2_list_and_get_icps(client):
    """GET /api/icp and GET /api/icp/{icp_id} return records and details."""
    list_res = client.get("/api/icp")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1

    icp_id = items[0]["icp_id"]
    get_res = client.get(f"/api/icp/{icp_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["icp_id"] == icp_id
    assert "original_claude_icp" in data
    assert "effective_icp" in data
    assert "audit_trail" in data


def test_3_approve_reject_edit_workflow(client):
    """Test full approval lifecycle: Approve -> Edit (invalidates approval) -> Reject."""
    list_res = client.get("/api/icp")
    icp_id = list_res.json()[0]["icp_id"]

    # 1. Approve
    app_res = client.post(f"/api/icp/{icp_id}/approve", json={"reviewer": "Director Sarah"})
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVED"
    assert app_res.json()["deepline_eligible"] is True

    # 2. Edit (must invalidate approval)
    edit_res = client.put(
        f"/api/icp/{icp_id}",
        json={"updated_data": {"minimum_employees": 120}, "reviewer": "Editor John"}
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["status"] == "EDITED"
    assert edit_res.json()["deepline_eligible"] is False
    assert edit_res.json()["effective_icp"]["minimum_employees"] == 120

    # 3. Reject
    rej_res = client.post(f"/api/icp/{icp_id}/reject", json={"reason": "Out of scope", "reviewer": "Director"})
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "REJECTED"


def test_4_deepline_preview_and_run_endpoints(client):
    """Test /deepline-preview and /deepline-run with safety gate enforcement."""
    list_res = client.get("/api/icp")
    icp_id = list_res.json()[0]["icp_id"]

    # Preview works even while pending
    prev_res = client.post(f"/api/icp/{icp_id}/deepline-preview", json={"requested_count": 50})
    assert prev_res.status_code == 200
    assert prev_res.json()["discovery_request"]["requested_lead_count"] == 50

    # Run fails when ICP is unapproved
    run_fail_res = client.post(f"/api/icp/{icp_id}/deepline-run", json={"requested_count": 50})
    assert run_fail_res.status_code == 400

    # Approve ICP
    client.post(f"/api/icp/{icp_id}/approve", json={"reviewer": "Lead"})

    # Run succeeds when approved
    run_succ_res = client.post(f"/api/icp/{icp_id}/deepline-run", json={"requested_count": 50})
    assert run_succ_res.status_code == 200
    data = run_succ_res.json()
    assert data["ok"] is True
    assert data["result"]["summary"]["discovered"] == 50
    assert data["result"]["summary"]["qualified"] > 0
