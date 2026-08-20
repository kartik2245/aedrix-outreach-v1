"""
test_database.py
Comprehensive automated test suite for Supabase PostgreSQL database layer,
ORM models, repositories, immutability guarantees, and FastAPI health endpoints.
"""

import os
os.environ["DATABASE_ENABLED"] = "true"
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.database.connection import (
    get_db_session,
    is_database_enabled,
    check_db_health,
)
from src.database.models import (
    Campaign,
    ICP,
    ICPVersion,
    ICPApproval,
    Lead,
    EmailDraft,
    EmailApproval,
    AuditLog,
)
from src.database.repositories import (
    CampaignRepository,
    ICPRepository,
    LeadRepository,
    EmailDraftRepository,
    ApprovalRepository,
    AuditRepository,
)
from src.icp.icp_models import ICPConfig, ICPStatus
from src.approval.approval_models import ApprovalStatus
from src.database.migrate_json_to_db import migrate_all


@pytest.fixture(scope="module")
def run_id():
    return uuid.uuid4().hex[:6]


@pytest.fixture
def db_session():
    if not is_database_enabled():
        pytest.skip("Database is not enabled in environment.")
    with get_db_session() as session:
        yield session


def test_database_connection_and_health():
    """Test 1: Verifies check_db_health returns valid status and numeric latency."""
    health = check_db_health()
    assert health["database"] == "supabase_postgresql"
    assert health["database_enabled"] is True
    assert health["connected"] is True
    assert health["latency_ms"] is not None
    assert health["latency_ms"] >= 0.0
    assert health["status"] == "HEALTHY"


def test_campaign_repository_crud(db_session, run_id):
    """Test 2: Campaign repository upsert, get_by_id, and list."""
    repo = CampaignRepository(db_session)
    c_id = f"test_camp_{run_id}"
    camp = repo.upsert(
        campaign_id=c_id,
        name="Unit Test Campaign",
        objective="Validate DB CRUD",
        target_geography="United Kingdom",
    )
    assert camp.id == c_id
    assert camp.name == "Unit Test Campaign"

    fetched = repo.get_by_id(c_id)
    assert fetched is not None
    assert fetched.name == "Unit Test Campaign"

    camps = repo.list_campaigns()
    assert len(camps) >= 1
    assert any(c.id == c_id for c in camps)


def test_icp_enrollment_and_approval(db_session, run_id):
    """Test 3: Enrolling an ICPConfig and approving it."""
    repo = ICPRepository(db_session)
    c_id = f"test_camp_{run_id}"
    i_id = f"test_icp_{run_id}"
    icp = ICPConfig(
        id=i_id,
        campaign_id=c_id,
        name="Unit Test ICP",
        version="1.0.0",
        campaign_description="Test campaign",
        industries=["Construction"],
        positive_signals=["Growing"],
        status=ICPStatus.PENDING_REVIEW,
    )

    app_rec = repo.enroll_icp(icp)
    assert app_rec.icp_id == i_id
    assert app_rec.status == "PENDING_REVIEW"
    assert app_rec.deepline_eligible is False

    approved = repo.approve_icp(i_id, reviewer="TEST_OPERATOR")
    assert approved.status == "APPROVED"
    assert approved.deepline_eligible is True
    assert approved.reviewer == "TEST_OPERATOR"


def test_icp_edit_creates_new_version_and_invalidates_approval(db_session, run_id):
    """Test 4: Editing an ICP creates a new version and invalidates deepline eligibility."""
    repo = ICPRepository(db_session)
    i_id = f"test_icp_{run_id}"
    updated = repo.edit_icp(
        i_id,
        updated_data={"industries": ["Commercial Building", "Infrastructure"]},
        reviewer="TEST_EDITOR",
    )
    assert updated.version == "1.1.0"
    assert updated.status == "EDITED"
    assert updated.deepline_eligible is False  # Must be re-approved!
    assert "Commercial Building" in updated.effective_icp["industries"]

    # Verify version record was stored
    versions = db_session.query(ICPVersion).filter_by(icp_id=i_id).all()
    assert len(versions) >= 2


def test_icp_rejection(db_session, run_id):
    """Test 5: Rejecting an ICP sets REJECTED status and ineligible."""
    repo = ICPRepository(db_session)
    i_id = f"test_icp_{run_id}"
    rejected = repo.reject_icp(i_id, reason="Out of market scope", reviewer="TEST_OPERATOR")
    assert rejected.status == "REJECTED"
    assert rejected.deepline_eligible is False
    assert rejected.rejection_reason == "Out of market scope"


def test_lead_repository_upsert_and_filters(db_session, run_id):
    """Test 6: Lead repository upsert and multi-field indexed query."""
    repo = LeadRepository(db_session)
    c_id = f"test_camp_{run_id}"
    l_id = f"test_lead_{run_id}"
    lead = repo.upsert_lead(
        lead_id=l_id,
        campaign_id=c_id,
        company_name=f"Acme Construction {run_id}",
        company_domain=f"acme-{run_id}.co.uk",
        contact_name="John Doe",
        job_title="Managing Director",
        email=f"john@{run_id}.co.uk",
        opportunity_score=85.0,
        accessibility_score=90.0,
        outreach_priority_index=87.5,
        priority_level="P1",
        qualification_status="QUALIFIED",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Won £15M hospital project.",
    )
    assert lead.id == l_id

    # Query with search
    results, total = repo.list_leads(search=run_id, priority="P1")
    assert total >= 1
    assert any(l.id == l_id for l in results)


def test_lead_repository_pagination(db_session):
    """Test 7: Lead repository page-based pagination."""
    repo = LeadRepository(db_session)
    p1_items, total = repo.list_leads(page=1, page_size=2)
    assert len(p1_items) <= 2
    assert total >= 1


def test_email_draft_immutability(db_session, run_id):
    """Test 8: AI Original drafts are NEVER overwritten when edited copies are stored."""
    repo = EmailDraftRepository(db_session)
    l_id = f"test_lead_immut_{run_id}"
    c_id = f"test_camp_{run_id}"

    lead_repo = LeadRepository(db_session)
    lead_repo.upsert_lead(
        lead_id=l_id,
        campaign_id=c_id,
        company_name="Immutability Test Ltd",
        company_domain="immut.co.uk",
        contact_name="Alice",
        job_title="Director",
        email=f"alice@{run_id}.co.uk",
    )

    draft = repo.upsert_draft(
        lead_id=l_id,
        ai_original_email_1="Original AI Draft Subject: Collaboration",
        ai_original_followup_a="Original Follow-up A",
        ai_original_followup_b="Original Follow-up B",
    )
    assert draft.ai_original_email_1 == "Original AI Draft Subject: Collaboration"
    assert draft.edited_email_1 is None

    # Now edit draft
    updated = repo.upsert_draft(
        lead_id=l_id,
        ai_original_email_1="ATTEMPTED OVERWRITE OF ORIGINAL",
        ai_original_followup_a="Original Follow-up A",
        ai_original_followup_b="Original Follow-up B",
        edited_email_1="Human Edited Copy: Hi Alice",
    )
    # Original AI copy MUST remain unchanged
    assert updated.ai_original_email_1 == "Original AI Draft Subject: Collaboration"
    assert updated.edited_email_1 == "Human Edited Copy: Hi Alice"


def test_approval_repository_gate_rules(db_session, run_id):
    """Test 9: Approval Gate enrolls qualified leads as PENDING_REVIEW and blocks hard disqualified."""
    c_id = f"test_camp_{run_id}"
    l_id = f"test_lead_gate_{run_id}"
    l_dq_id = f"test_lead_dq_{run_id}"

    lead_repo = LeadRepository(db_session)
    lead_repo.upsert_lead(
        lead_id=l_id,
        campaign_id=c_id,
        company_name="Qualified Main Contractor",
        company_domain="qual.co.uk",
        contact_name="David",
        job_title="Commercial Director",
        email=f"david@{run_id}.co.uk",
        qualification_status="QUALIFIED",
    )
    lead_repo.upsert_lead(
        lead_id=l_dq_id,
        campaign_id=c_id,
        company_name="Tiny Sub Ltd",
        company_domain="tinysub.co.uk",
        contact_name="Bob Small",
        job_title="Sole Trader",
        email=f"bob@{run_id}.co.uk",
        qualification_status="HARD_DISQUALIFIED",
        disqualification_reason="Subcontractor under 5 employees.",
    )

    repo = ApprovalRepository(db_session)

    # Qualified lead
    app_q = repo.enroll_draft(
        lead_id=l_id,
        qualification_status="QUALIFIED",
        qa_status="PASS",
    )
    assert app_q.approval_status == ApprovalStatus.PENDING_REVIEW.value
    assert app_q.smartlead_eligible is False

    # Approve
    approved = repo.approve_lead(l_id, reviewer="TEST_OPERATOR")
    assert approved.approval_status == ApprovalStatus.APPROVED.value
    assert approved.smartlead_eligible is True

    # Hard Disqualified lead
    app_dq = repo.enroll_draft(
        lead_id=l_dq_id,
        qualification_status="HARD_DISQUALIFIED",
        qa_status="PASS",
        disqualification_reason="Subcontractor under 5 employees.",
    )
    assert app_dq.approval_status == ApprovalStatus.BLOCKED.value
    assert app_dq.smartlead_eligible is False


def test_approval_edit_invalidates_smartlead_eligibility(db_session, run_id):
    """Test 10: Human edit of email copy resets status to EDITED and smartlead_eligible=False."""
    l_id = f"test_lead_gate_{run_id}"
    draft_repo = EmailDraftRepository(db_session)
    draft_repo.upsert_draft(
        lead_id=l_id,
        ai_original_email_1="Original copy",
        ai_original_followup_a="Followup A",
        ai_original_followup_b="Followup B",
    )

    repo = ApprovalRepository(db_session)
    edited = repo.edit_lead(
        lead_id=l_id,
        email_1="Customized opening hook",
        reviewer="TEST_OPERATOR",
    )
    assert edited.approval_status == ApprovalStatus.EDITED.value
    assert edited.smartlead_eligible is False  # Must be re-approved


def test_json_to_db_migration_idempotence():
    """Test 11: migrate_all() runs idempotently and creates 0 duplicate records."""
    _ = migrate_all()
    summary = migrate_all()
    assert summary["campaigns"] == 0
    assert summary["icps"] == 0
    assert summary["leads"] == 0
    assert summary["email_drafts"] == 0
    assert summary["email_approvals"] == 0


def test_database_health_api_endpoint():
    """Test 12: FastAPI GET /api/system/database-health endpoint."""
    client = TestClient(app)
    resp = client.get("/api/system/database-health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["database"] == "supabase_postgresql"
    assert data["connected"] is True
    assert data["database_enabled"] is True
    assert data["latency_ms"] >= 0.0
    assert data["status"] == "HEALTHY"
