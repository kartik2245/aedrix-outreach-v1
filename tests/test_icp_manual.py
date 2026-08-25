"""
test_icp_manual.py
Automated tests for the Manual ICP Creation Flow in Aedrix AI Cold Outreach System (Python 3.12).

Verifies:
- POST /api/icp/manual input validation and schema requirements
- ICPConfig creation with source=MANUAL
- Immediate enrollment into Human Approval Queue as PENDING_REVIEW (deepline_eligible=False)
- Approval gate execution (unlocks deepline_eligible=True)
- Safety invariant: Editing an approved manual ICP invalidates approval, transitions to EDITED, and requires re-approval
- Deepline Discovery preview and run compatibility with approved manual ICPs
- DEMO vs PRODUCTION environment isolation
- Backward compatibility with existing Claude ICP flows
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.config.app_mode import ModeService, AppMode
from src.icp.icp_models import ICPSource, ICPStatus
from src.database.connection import is_database_enabled, get_db_session
from src.database.models import Lead, Campaign, ICP, ICPApproval

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Ensure tests run in clean DEMO mode with safe dry-run defaults."""
    import os
    old_db = os.environ.get("DATABASE_ENABLED")
    os.environ["DATABASE_ENABLED"] = "false"
    ModeService.get_instance().set_mode(AppMode.DEMO)
    yield
    if old_db is not None:
        os.environ["DATABASE_ENABLED"] = old_db
    else:
        os.environ.pop("DATABASE_ENABLED", None)


def test_1_manual_icp_validation_failures():
    """Test validation errors when required fields are missing or invalid."""
    # Missing campaign_name
    res = client.post("/api/icp/manual", json={
        "campaign_objective": "Test objective with sufficient detail",
    })
    assert res.status_code == 422

    # Empty campaign_name (below min_length)
    res = client.post("/api/icp/manual", json={
        "campaign_name": "A",
        "campaign_objective": "Test objective with sufficient detail",
    })
    assert res.status_code == 422

    # Missing campaign_objective
    res = client.post("/api/icp/manual", json={
        "campaign_name": "Valid Name",
    })
    assert res.status_code == 422


def test_2_manual_icp_successful_creation():
    """Test successful manual ICP creation with structured fields."""
    payload = {
        "campaign_name": "UK Tier 1 Commercial Contractors",
        "campaign_objective": "Target commercial contractors with digital roadmap for Aedrix document control",
        "industry": "Commercial Construction, Civil Engineering",
        "industries": ["Commercial Construction", "Civil Engineering"],
        "geography": "United Kingdom",
        "minimum_employees": 100,
        "maximum_employees": 1000,
        "minimum_revenue": 25.0,
        "maximum_revenue": 200.0,
        "company_size": "100-1000 employees or £25M-£200M revenue",
        "target_personas": ["Head of Pre-Construction", "Commercial Director", "Operations Director"],
        "seniority_levels": ["Director", "Head", "C-Level"],
        "technologies": ["BIM", "Procore", "Autodesk Construction Cloud"],
        "qualification_rules": [
            "Active multi-site commercial pipeline",
            "Tier 1 or Tier 2 scale",
            "Document versioning challenges",
        ],
        "hard_disqualification_rules": [
            "Operating outside United Kingdom",
            "Non-construction sector or pure residential micro-builder",
            "Under 100 employees and under £25M turnover",
        ],
        "campaign_exclusion_rules": [
            "Active deal in CRM pipeline",
            "Global suppression opt-out",
            "Contacted within past 60 days",
        ],
        "additional_notes": "Operator manual authoring test",
        "voc_context": "Drawing revision risk and subcontractor billing control",
    }

    res = client.post("/api/icp/manual", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["ok"] is True
    assert data["status"] == "PENDING_REVIEW"
    assert data["source"] == "MANUAL"

    icp = data["icp"]
    assert icp["name"] == "UK Tier 1 Commercial Contractors"
    assert icp["source"] == "MANUAL"
    assert icp["minimum_employees"] == 100
    assert icp["minimum_revenue"] == 25.0
    assert len(icp["target_personas"]) == 3
    assert len(icp["hard_disqualifiers"]) == 3
    assert len(icp["campaign_exclusions"]) == 3

    record = data["record"]
    assert record["status"] == "PENDING_REVIEW"
    assert record["source"] == "MANUAL"
    assert record["deepline_eligible"] is False
    assert record["original_claude_icp"] is None


def test_3_manual_icp_approval_workflow():
    """Test approval of manual ICP unlocks deepline eligibility."""
    # 1. Create Manual ICP
    create_res = client.post("/api/icp/manual", json={
        "campaign_name": "UK Infrastructure Civil Specialists",
        "campaign_objective": "Target civil engineering main contractors for drawing management",
        "industry": "Civil Engineering, Infrastructure",
        "geography": "United Kingdom",
        "minimum_employees": 50,
        "minimum_revenue": 10.0,
        "target_personas": ["Commercial Director", "Operations Director"],
    })
    assert create_res.status_code == 200
    icp_id = create_res.json()["icp_id"]

    # 2. Verify starts PENDING_REVIEW
    get_res = client.get(f"/api/icp/{icp_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "PENDING_REVIEW"
    assert get_res.json()["deepline_eligible"] is False
    assert get_res.json()["source"] == "MANUAL"

    # 3. Approve ICP
    app_res = client.post(f"/api/icp/{icp_id}/approve", json={"reviewer": "TEST_OPERATOR"})
    assert app_res.status_code == 200
    approved_record = app_res.json()
    assert approved_record["status"] == "APPROVED"
    assert approved_record["deepline_eligible"] is True
    assert approved_record["reviewer"] == "TEST_OPERATOR"


def test_4_editing_approved_manual_icp_invalidates_approval():
    """Test editing an approved manual ICP resets status to EDITED and requires re-approval."""
    # 1. Create and Approve
    create_res = client.post("/api/icp/manual", json={
        "campaign_name": "UK Regional Main Contractors",
        "campaign_objective": "Target regional commercial builders in the Midlands and North",
        "minimum_employees": 50,
        "minimum_revenue": 10.0,
        "target_personas": ["Managing Director", "Commercial Director"],
    })
    icp_id = create_res.json()["icp_id"]
    client.post(f"/api/icp/{icp_id}/approve", json={"reviewer": "TEST_OPERATOR"})

    # 2. Edit the criteria
    edit_res = client.put(f"/api/icp/{icp_id}", json={
        "updated_data": {
            "minimum_employees": 75,
            "minimum_revenue": 15.0,
            "target_personas": ["Managing Director", "Commercial Director", "Head of Pre-Construction"],
        },
        "reviewer": "TEST_OPERATOR_2",
    })
    assert edit_res.status_code == 200
    edited = edit_res.json()

    assert edited["status"] == "EDITED"
    assert edited["deepline_eligible"] is False
    assert edited["version"] == "1.1.0"
    assert edited["effective_icp"]["minimum_employees"] == 75
    assert len(edited["effective_icp"]["target_personas"]) == 3

    # 3. Re-approve
    reapp_res = client.post(f"/api/icp/{icp_id}/approve", json={"reviewer": "TEST_OPERATOR_2"})
    assert reapp_res.status_code == 200
    assert reapp_res.json()["status"] == "APPROVED"
    assert reapp_res.json()["deepline_eligible"] is True


def test_5_deepline_discovery_on_manual_icp():
    """Test Deepline preview and discovery run against approved manual ICP."""
    # 1. Create & Approve Manual ICP
    create_res = client.post("/api/icp/manual", json={
        "campaign_name": "UK Main Contractor Deepline Test",
        "campaign_objective": "Test Deepline discovery integration with manual ICP",
        "geography": "United Kingdom",
        "industry": "Commercial Construction",
        "minimum_employees": 50,
        "minimum_revenue": 10.0,
        "target_personas": ["Commercial Director", "IT Director"],
    })
    icp_id = create_res.json()["icp_id"]
    client.post(f"/api/icp/{icp_id}/approve", json={"reviewer": "OPERATOR"})

    # 2. Preview Deepline Run
    prev_res = client.post(f"/api/icp/{icp_id}/deepline-preview", json={"requested_count": 5})
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["deepline_eligible"] is True
    assert prev_data["discovery_request"]["icp_id"] == icp_id
    assert prev_data["discovery_request"]["requested_lead_count"] == 5

    # 3. Run Deepline Discovery
    run_res = client.post(f"/api/icp/{icp_id}/deepline-run", json={"requested_count": 5})
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["ok"] is True
    assert run_data["result"]["summary"]["discovered"] > 0
    assert run_data["result"]["icp_id"] == icp_id


def test_6_environment_isolation_and_production_data_safety():
    """Verify manual ICP operates in active DEMO mode without touching PRODUCTION records."""
    ModeService.get_instance().set_mode(AppMode.DEMO)

    # Count production records prior to test
    if is_database_enabled():
        with get_db_session() as session:
            initial_prod_leads = session.query(Lead).filter(Lead.environment == "PRODUCTION").count()
            initial_prod_campaigns = session.query(Campaign).filter(Campaign.environment == "PRODUCTION").count()

    # Create manual ICP in DEMO mode
    res = client.post("/api/icp/manual", json={
        "campaign_name": "Demo Mode Isolated Manual Campaign",
        "campaign_objective": "Ensure demo environment tagging",
        "minimum_employees": 50,
    })
    assert res.status_code == 200
    icp_id = res.json()["icp_id"]

    # Verify record in DB has environment='DEMO' and source='MANUAL'
    if is_database_enabled():
        with get_db_session() as session:
            db_icp = session.query(ICP).filter(ICP.id == icp_id).first()
            assert db_icp is not None
            assert db_icp.environment == "DEMO"
            assert db_icp.source == "MANUAL"

            db_app = session.query(ICPApproval).filter(ICPApproval.icp_id == icp_id).first()
            assert db_app is not None
            assert db_app.source == "MANUAL"

            # Verify production records were not modified
            final_prod_leads = session.query(Lead).filter(Lead.environment == "PRODUCTION").count()
            final_prod_campaigns = session.query(Campaign).filter(Campaign.environment == "PRODUCTION").count()
            assert final_prod_leads == initial_prod_leads
            assert final_prod_campaigns == initial_prod_campaigns


def test_7_claude_icp_designer_backward_compatibility():
    """Verify existing Claude ICP generation endpoint continues working with source=CLAUDE_GENERATED."""
    res = client.post("/api/icp/generate", json={
        "campaign_name": "Claude AI Targeted Outreach",
        "campaign_objective": "Test that Claude generated flow outputs source=CLAUDE_GENERATED",
        "minimum_employees": 50,
        "minimum_revenue": 10.0,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["source"] == "CLAUDE_GENERATED"
    assert data["icp"]["source"] == "CLAUDE_GENERATED"
    assert data["record"]["source"] == "CLAUDE_GENERATED"
    assert data["record"]["original_claude_icp"] is not None
