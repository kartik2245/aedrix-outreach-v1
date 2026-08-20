"""
icp_approval_engine.py
Human Approval & Safety Engine for ICP Configurations (Python 3.12).

Guarantees:
- Newly designed ICPs start as PENDING_REVIEW (deepline_eligible=False).
- Only APPROVED ICPs can be consumed by Deepline Discovery.
- Edits invalidate prior approvals, transition to EDITED / PENDING_REVIEW, and require re-approval.
- Original Claude-generated ICP remains permanently immutable.
- Full structured audit trail recording actions, reviewers, and timestamps.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from src.icp.icp_models import ICPConfig, ICPStatus
from src.icp.icp_approval_models import ICPApprovalRecord, ICPAuditEntry
from src.icp.icp_approval_store import ICPApprovalStore


class ICPApprovalEngine:
    def __init__(self, store: Optional[ICPApprovalStore] = None):
        self.store = store or ICPApprovalStore()

    def enroll_icp(self, icp: ICPConfig, source: str = "CLAUDE_GENERATED") -> ICPApprovalRecord:
        """Enrolls a newly generated ICP into the approval queue as PENDING_REVIEW."""
        now_str = datetime.now(timezone.utc).isoformat()
        icp.status = ICPStatus.PENDING_REVIEW
        actor_name = "OPERATOR_MANUAL" if source == "MANUAL" else "SYSTEM_CLAUDE_DESIGNER"

        record = ICPApprovalRecord(
            icp_id=icp.id,
            campaign_id=icp.campaign_id,
            name=icp.name,
            version=icp.version,
            status=ICPStatus.PENDING_REVIEW,
            source=source,
            original_claude_icp=icp.model_copy(deep=True) if source == "CLAUDE_GENERATED" else None,
            effective_icp=icp.model_copy(deep=True),
            reviewer=None,
            reviewed_at=None,
            deepline_eligible=False,
            deepline_run_ids=[],
            edit_history=[],
            audit_trail=[
                ICPAuditEntry(
                    timestamp=now_str,
                    action="ENROLLED_FOR_REVIEW",
                    reviewer=actor_name,
                    details={"campaign_id": icp.campaign_id, "initial_version": icp.version, "source": source}
                )
            ]
        )

        self.store.upsert_record(record)
        return record

    def approve_icp(self, icp_id: str, reviewer: str = "HUMAN_OPERATOR") -> ICPApprovalRecord:
        """Explicitly approves an ICP configuration for Deepline discovery."""
        record = self.store.get_record(icp_id)
        if not record:
            raise ValueError(f"ICP '{icp_id}' not found in approval queue.")

        if record.status == ICPStatus.BLOCKED:
            raise ValueError(f"Cannot directly approve blocked ICP '{icp_id}'. Unblock or edit first.")

        now_str = datetime.now(timezone.utc).isoformat()
        record.status = ICPStatus.APPROVED
        record.deepline_eligible = True
        record.reviewer = reviewer
        record.reviewed_at = now_str
        record.effective_icp.status = ICPStatus.APPROVED
        record.effective_icp.updated_at = now_str

        record.audit_trail.append(
            ICPAuditEntry(
                timestamp=now_str,
                action="ICP_APPROVED",
                reviewer=reviewer,
                details={"deepline_eligible": True, "version": record.version}
            )
        )

        self.store.upsert_record(record)
        return record

    def edit_icp(
        self,
        icp_id: str,
        updated_data: Dict[str, Any],
        reviewer: str = "HUMAN_OPERATOR"
    ) -> ICPApprovalRecord:
        """
        Updates an ICP configuration while preserving the original Claude copy.
        Invalidates previous approval, transitions status to EDITED, and requires re-approval.
        """
        record = self.store.get_record(icp_id)
        if not record:
            raise ValueError(f"ICP '{icp_id}' not found in approval queue.")

        now_str = datetime.now(timezone.utc).isoformat()
        old_version = record.version
        try:
            parts = [int(p) for p in old_version.split(".")]
            if len(parts) == 3:
                parts[1] += 1  # Increment minor version e.g. 1.0.0 -> 1.1.0
                new_version = f"{parts[0]}.{parts[1]}.{parts[2]}"
            else:
                new_version = f"{old_version}.1"
        except Exception:
            new_version = f"{old_version}-edited"

        current_dump = record.effective_icp.model_dump()
        current_dump.update(updated_data)
        current_dump["version"] = new_version
        current_dump["updated_at"] = now_str
        current_dump["status"] = ICPStatus.EDITED

        updated_effective = ICPConfig.model_validate(current_dump)

        record.version = new_version
        record.effective_icp = updated_effective
        record.status = ICPStatus.EDITED
        record.deepline_eligible = False  # Invalidate prior approval!
        record.reviewer = reviewer
        record.reviewed_at = now_str

        edit_entry = {
            "timestamp": now_str,
            "editor": reviewer,
            "previous_version": old_version,
            "new_version": new_version,
            "fields_modified": list(updated_data.keys())
        }
        record.edit_history.append(edit_entry)

        record.audit_trail.append(
            ICPAuditEntry(
                timestamp=now_str,
                action="ICP_EDITED",
                reviewer=reviewer,
                details=edit_entry
            )
        )

        self.store.upsert_record(record)
        return record

    def reject_icp(self, icp_id: str, reason: str, reviewer: str = "HUMAN_OPERATOR") -> ICPApprovalRecord:
        """Marks an ICP as REJECTED."""
        record = self.store.get_record(icp_id)
        if not record:
            raise ValueError(f"ICP '{icp_id}' not found in approval queue.")

        now_str = datetime.now(timezone.utc).isoformat()
        record.status = ICPStatus.REJECTED
        record.deepline_eligible = False
        record.rejection_reason = reason
        record.reviewer = reviewer
        record.reviewed_at = now_str
        record.effective_icp.status = ICPStatus.REJECTED

        record.audit_trail.append(
            ICPAuditEntry(
                timestamp=now_str,
                action="ICP_REJECTED",
                reviewer=reviewer,
                details={"reason": reason}
            )
        )

        self.store.upsert_record(record)
        return record

    def block_icp(self, icp_id: str, reason: str, reviewer: str = "HUMAN_OPERATOR") -> ICPApprovalRecord:
        """Marks an ICP as BLOCKED."""
        record = self.store.get_record(icp_id)
        if not record:
            raise ValueError(f"ICP '{icp_id}' not found in approval queue.")

        now_str = datetime.now(timezone.utc).isoformat()
        record.status = ICPStatus.BLOCKED
        record.deepline_eligible = False
        record.blocked_reason = reason
        record.reviewer = reviewer
        record.reviewed_at = now_str
        record.effective_icp.status = ICPStatus.BLOCKED

        record.audit_trail.append(
            ICPAuditEntry(
                timestamp=now_str,
                action="ICP_BLOCKED",
                reviewer=reviewer,
                details={"reason": reason}
            )
        )

        self.store.upsert_record(record)
        return record

    def record_deepline_run(self, icp_id: str, run_id: str) -> None:
        """Appends a Deepline discovery run ID to the ICP approval record."""
        record = self.store.get_record(icp_id)
        if record and run_id not in record.deepline_run_ids:
            record.deepline_run_ids.append(run_id)
            record.audit_trail.append(
                ICPAuditEntry(
                    action="DEEPLINE_RUN_RECORDED",
                    reviewer="DEEPLINE_RUNNER",
                    details={"run_id": run_id}
                )
            )
            self.store.upsert_record(record)
