"""
test_icp_approval.py
Unit tests for the Human ICP Approval & Safety Gate layer.
Verifies state machine transitions, immutable original copies, edit invalidations, and audit trails.
"""

import pytest
from src.icp.icp_models import ICPConfig, ICPStatus
from src.icp.icp_approval_engine import ICPApprovalEngine
from src.icp.icp_approval_store import ICPApprovalStore
from src.icp.icp_designer import ICPDesigner


@pytest.fixture
def isolated_engine(tmp_path):
    storage_file = tmp_path / "test_icp_queue.json"
    store = ICPApprovalStore(storage_path=str(storage_file))
    return ICPApprovalEngine(store=store)


def test_1_new_icp_starts_pending_review(isolated_engine):
    """Verify newly designed ICP starts as PENDING_REVIEW with deepline_eligible=False."""
    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="Test Enterprise ICP",
        campaign_objective="Target Tier-1 contractors"
    )

    record = isolated_engine.enroll_icp(icp)
    assert record.status == ICPStatus.PENDING_REVIEW
    assert record.deepline_eligible is False
    assert record.reviewer is None
    assert record.original_claude_icp.name == "Test Enterprise ICP"
    assert len(record.audit_trail) == 1
    assert record.audit_trail[0].action == "ENROLLED_FOR_REVIEW"


def test_2_approve_icp_enables_deepline(isolated_engine):
    """Verify approving an ICP enables deepline_eligible=True and records reviewer."""
    designer = ICPDesigner()
    icp = designer.design_icp(campaign_name="Approve Test", campaign_objective="Test")
    record = isolated_engine.enroll_icp(icp)

    approved = isolated_engine.approve_icp(record.icp_id, reviewer="Sarah Campaign Director")
    assert approved.status == ICPStatus.APPROVED
    assert approved.deepline_eligible is True
    assert approved.reviewer == "Sarah Campaign Director"
    assert approved.reviewed_at is not None
    assert approved.effective_icp.status == ICPStatus.APPROVED

    # Verify audit entry
    assert any(a.action == "ICP_APPROVED" for a in approved.audit_trail)


def test_3_reject_and_block_icp(isolated_engine):
    """Verify Reject and Block state transitions."""
    designer = ICPDesigner()
    icp = designer.design_icp(campaign_name="Reject Test", campaign_objective="Test")
    record = isolated_engine.enroll_icp(icp)

    # Reject
    rejected = isolated_engine.reject_icp(record.icp_id, reason="Persona criteria too broad", reviewer="Auditor")
    assert rejected.status == ICPStatus.REJECTED
    assert rejected.deepline_eligible is False
    assert rejected.rejection_reason == "Persona criteria too broad"

    # Block
    blocked = isolated_engine.block_icp(record.icp_id, reason="Strategic freeze", reviewer="Admin")
    assert blocked.status == ICPStatus.BLOCKED
    assert blocked.deepline_eligible is False
    assert blocked.blocked_reason == "Strategic freeze"

    # Blocked ICP cannot be approved directly
    with pytest.raises(ValueError, match="Cannot directly approve blocked ICP"):
        isolated_engine.approve_icp(record.icp_id, reviewer="Admin")


def test_4_editing_invalidates_approval_and_increments_version(isolated_engine):
    """
    CRITICAL SAFETY RULE: Editing an approved ICP must invalidate prior approval,
    set status to EDITED, set deepline_eligible=False, and increment version.
    """
    designer = ICPDesigner()
    icp = designer.design_icp(campaign_name="Edit Test", campaign_objective="Test")
    record = isolated_engine.enroll_icp(icp)

    # 1. Approve ICP
    isolated_engine.approve_icp(record.icp_id, reviewer="Lead")

    # 2. Human Operator edits size threshold
    edited = isolated_engine.edit_icp(
        record.icp_id,
        updated_data={"minimum_employees": 150, "minimum_revenue": 25.0},
        reviewer="Operator John"
    )

    assert edited.status == ICPStatus.EDITED
    assert edited.deepline_eligible is False  # Must require re-approval!
    assert edited.version == "1.1.0"
    assert edited.effective_icp.minimum_employees == 150
    assert edited.effective_icp.minimum_revenue == 25.0
    assert len(edited.edit_history) == 1
    assert "minimum_employees" in edited.edit_history[0]["fields_modified"]

    # 3. Re-approve edited ICP
    reapproved = isolated_engine.approve_icp(record.icp_id, reviewer="Lead")
    assert reapproved.status == ICPStatus.APPROVED
    assert reapproved.deepline_eligible is True


def test_5_original_claude_icp_remains_immutable_across_edits(isolated_engine):
    """Verify original Claude-generated copy is never overwritten."""
    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="Immutable Original Test",
        campaign_objective="Test immutability",
        minimum_employees=50
    )
    record = isolated_engine.enroll_icp(icp)

    # Edit multiple times
    isolated_engine.edit_icp(record.icp_id, {"minimum_employees": 200}, reviewer="Editor 1")
    isolated_engine.edit_icp(record.icp_id, {"minimum_employees": 500}, reviewer="Editor 2")

    stored = isolated_engine.store.get_record(record.icp_id)
    assert stored.original_claude_icp.minimum_employees == 50  # Original remains intact!
    assert stored.effective_icp.minimum_employees == 500
    assert stored.version == "1.2.0"
    assert len(stored.edit_history) == 2
