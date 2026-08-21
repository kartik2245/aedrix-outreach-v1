"""
icp_repository.py
Repository for ICPs, ICP Versions, and Human ICP Approval operations in PostgreSQL.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from src.database.models.campaign import Campaign
from src.database.models.icp import ICP, ICPVersion, ICPApproval
from src.database.models.audit import AuditLog
from src.icp.icp_models import ICPConfig, ICPStatus


class ICPRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, icp_id: str) -> Optional[ICP]:
        return self.session.scalar(select(ICP).where(ICP.id == icp_id))

    def get_approval_record(self, icp_id: str) -> Optional[ICPApproval]:
        return self.session.scalar(select(ICPApproval).where(ICPApproval.icp_id == icp_id))

    def list_icps(
        self,
        status: Optional[str] = None,
        campaign_id: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> List[ICP]:
        stmt = select(ICP).order_by(desc(ICP.created_at))
        if status:
            stmt = stmt.where(ICP.status == status.upper())
        if campaign_id:
            stmt = stmt.where(ICP.campaign_id == campaign_id)
        if environment:
            stmt = stmt.where(ICP.environment == environment.upper())
        return list(self.session.scalars(stmt).all())

    def list_approvals(
        self,
        status: Optional[str] = None,
        campaign_id: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> List[ICPApproval]:
        stmt = select(ICPApproval).join(ICP, ICPApproval.icp_id == ICP.id).order_by(desc(ICPApproval.created_at))
        if status:
            stmt = stmt.where(ICPApproval.status == status.upper())
        if campaign_id:
            stmt = stmt.where(ICP.campaign_id == campaign_id)
        if environment:
            stmt = stmt.where(ICP.environment == environment.upper())
        return list(self.session.scalars(stmt).all())

    def enroll_icp(self, icp: ICPConfig, environment: str = "PRODUCTION", source: str = "CLAUDE_GENERATED") -> ICPApproval:
        """Enrolls a newly designed ICP into PostgreSQL with an immutable original copy and v1.0.0 record."""
        # 1. Ensure parent campaign exists
        campaign = self.session.scalar(select(Campaign).where(Campaign.id == icp.campaign_id))
        if not campaign:
            campaign = Campaign(
                id=icp.campaign_id,
                name=icp.name,
                objective=icp.campaign_description,
                status="ACTIVE",
                environment=environment,
                target_geography=icp.geography.primary_country if icp.geography else "United Kingdom",
            )
            self.session.add(campaign)
            self.session.flush()
        else:
            campaign.name = icp.name
            campaign.objective = icp.campaign_description
            campaign.environment = environment

        # 2. Upsert ICP root record
        db_icp = self.get_by_id(icp.id)
        if not db_icp:
            db_icp = ICP(
                id=icp.id,
                campaign_id=icp.campaign_id,
                name=icp.name,
                status=ICPStatus.PENDING_REVIEW.value,
                environment=environment,
                source=source,
                current_version=icp.version or "1.0.0",
            )
            self.session.add(db_icp)
            self.session.flush()
        else:
            db_icp.campaign_id = icp.campaign_id
            db_icp.name = icp.name
            db_icp.environment = environment
            db_icp.source = source

        # 3. Add initial ICP Version if not present
        existing_version = self.session.scalar(
            select(ICPVersion).where(ICPVersion.icp_id == icp.id, ICPVersion.version == (icp.version or "1.0.0"))
        )
        if not existing_version:
            version_obj = ICPVersion(
                icp_id=icp.id,
                version=icp.version or "1.0.0",
                config_data=icp.model_dump(mode="json"),
                reasoning=icp.reasoning,
            )
            self.session.add(version_obj)

        # 4. Upsert ICP Approval record
        now_dt = datetime.now(timezone.utc)
        actor_name = "OPERATOR_MANUAL" if source == "MANUAL" else "SYSTEM_CLAUDE_DESIGNER"
        approval = self.get_approval_record(icp.id)
        if not approval:
            approval = ICPApproval(
                icp_id=icp.id,
                version=icp.version or "1.0.0",
                status=ICPStatus.PENDING_REVIEW.value,
                source=source,
                original_claude_icp=icp.model_dump(mode="json") if source == "CLAUDE_GENERATED" else None,
                effective_icp=icp.model_dump(mode="json"),
                reviewer=None,
                reviewed_at=None,
                deepline_eligible=False,
                deepline_run_ids=[],
                edit_history=[],
                audit_trail=[
                    {
                        "timestamp": now_dt.isoformat(),
                        "action": "ENROLLED_FOR_REVIEW",
                        "reviewer": actor_name,
                        "details": {"campaign_id": icp.campaign_id, "initial_version": icp.version or "1.0.0", "source": source}
                    }
                ]
            )
            self.session.add(approval)
        else:
            approval.version = icp.version or "1.0.0"
            approval.status = ICPStatus.PENDING_REVIEW.value
            approval.source = source
            approval.effective_icp = icp.model_dump(mode="json")
            approval.deepline_eligible = False

        # 5. Audit Log
        audit = AuditLog(
            entity_type="ICP",
            entity_id=icp.id,
            action="ENROLLED_FOR_REVIEW",
            actor=actor_name,
            details={"campaign_id": icp.campaign_id, "version": icp.version or "1.0.0", "source": source}
        )
        self.session.add(audit)
        self.session.flush()

        return approval

    def approve_icp(self, icp_id: str, reviewer: str = "HUMAN_OPERATOR") -> ICPApproval:
        approval = self.get_approval_record(icp_id)
        if not approval:
            raise ValueError(f"ICP '{icp_id}' not found in database.")

        if approval.status == ICPStatus.BLOCKED.value:
            raise ValueError(f"Cannot directly approve blocked ICP '{icp_id}'. Unblock or edit first.")

        now_dt = datetime.now(timezone.utc)
        now_str = now_dt.isoformat()

        approval.status = ICPStatus.APPROVED.value
        approval.deepline_eligible = True
        approval.reviewer = reviewer
        approval.reviewed_at = now_dt

        # Update effective copy
        eff = dict(approval.effective_icp)
        eff["status"] = ICPStatus.APPROVED.value
        eff["updated_at"] = now_str
        approval.effective_icp = eff

        # Update root ICP status
        db_icp = self.get_by_id(icp_id)
        if db_icp:
            db_icp.status = ICPStatus.APPROVED.value

        audit_entry = {
            "timestamp": now_str,
            "action": "ICP_APPROVED",
            "reviewer": reviewer,
            "details": {"deepline_eligible": True, "version": approval.version}
        }
        trail = list(approval.audit_trail or [])
        trail.append(audit_entry)
        approval.audit_trail = trail

        audit = AuditLog(
            entity_type="ICP",
            entity_id=icp_id,
            action="ICP_APPROVED",
            actor=reviewer,
            details=audit_entry
        )
        self.session.add(audit)
        self.session.flush()
        return approval

    def edit_icp(self, icp_id: str, updated_data: Dict[str, Any], reviewer: str = "HUMAN_OPERATOR") -> ICPApproval:
        approval = self.get_approval_record(icp_id)
        if not approval:
            raise ValueError(f"ICP '{icp_id}' not found in database.")

        now_dt = datetime.now(timezone.utc)
        now_str = now_dt.isoformat()
        old_version = approval.version

        try:
            parts = [int(p) for p in old_version.split(".")]
            if len(parts) == 3:
                parts[1] += 1
                new_version = f"{parts[0]}.{parts[1]}.{parts[2]}"
            else:
                new_version = f"{old_version}.1"
        except Exception:
            new_version = f"{old_version}-edited"

        current_dump = dict(approval.effective_icp)
        current_dump.update(updated_data)
        current_dump["version"] = new_version
        current_dump["updated_at"] = now_str
        current_dump["status"] = ICPStatus.EDITED.value

        approval.version = new_version
        approval.effective_icp = current_dump
        approval.status = ICPStatus.EDITED.value
        approval.deepline_eligible = False  # Invalidate prior approval
        approval.reviewer = reviewer
        approval.reviewed_at = now_dt

        # Update root ICP record
        db_icp = self.get_by_id(icp_id)
        if db_icp:
            db_icp.status = ICPStatus.EDITED.value
            db_icp.current_version = new_version

        # Insert new version record
        version_obj = ICPVersion(
            icp_id=icp_id,
            version=new_version,
            config_data=current_dump,
            reasoning=f"Operator edit by {reviewer}",
        )
        self.session.add(version_obj)

        edit_entry = {
            "timestamp": now_str,
            "editor": reviewer,
            "previous_version": old_version,
            "new_version": new_version,
            "fields_modified": list(updated_data.keys())
        }
        history = list(approval.edit_history or [])
        history.append(edit_entry)
        approval.edit_history = history

        audit_entry = {
            "timestamp": now_str,
            "action": "ICP_EDITED",
            "reviewer": reviewer,
            "details": edit_entry
        }
        trail = list(approval.audit_trail or [])
        trail.append(audit_entry)
        approval.audit_trail = trail

        audit = AuditLog(
            entity_type="ICP",
            entity_id=icp_id,
            action="ICP_EDITED",
            actor=reviewer,
            details=edit_entry
        )
        self.session.add(audit)
        self.session.flush()
        return approval

    def reject_icp(self, icp_id: str, reason: str, reviewer: str = "HUMAN_OPERATOR") -> ICPApproval:
        approval = self.get_approval_record(icp_id)
        if not approval:
            raise ValueError(f"ICP '{icp_id}' not found in database.")

        now_dt = datetime.now(timezone.utc)
        now_str = now_dt.isoformat()

        approval.status = ICPStatus.REJECTED.value
        approval.deepline_eligible = False
        approval.rejection_reason = reason
        approval.reviewer = reviewer
        approval.reviewed_at = now_dt

        eff = dict(approval.effective_icp)
        eff["status"] = ICPStatus.REJECTED.value
        approval.effective_icp = eff

        db_icp = self.get_by_id(icp_id)
        if db_icp:
            db_icp.status = ICPStatus.REJECTED.value

        audit_entry = {
            "timestamp": now_str,
            "action": "ICP_REJECTED",
            "reviewer": reviewer,
            "details": {"reason": reason}
        }
        trail = list(approval.audit_trail or [])
        trail.append(audit_entry)
        approval.audit_trail = trail

        audit = AuditLog(
            entity_type="ICP",
            entity_id=icp_id,
            action="ICP_REJECTED",
            actor=reviewer,
            details={"reason": reason}
        )
        self.session.add(audit)
        self.session.flush()
        return approval

    def record_deepline_run(self, icp_id: str, run_id: str) -> None:
        approval = self.get_approval_record(icp_id)
        if approval:
            runs = list(approval.deepline_run_ids or [])
            if run_id not in runs:
                runs.append(run_id)
                approval.deepline_run_ids = runs
                self.session.flush()
