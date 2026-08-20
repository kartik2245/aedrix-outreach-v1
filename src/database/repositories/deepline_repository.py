"""
deepline_repository.py
Repository for Deepline discovery runs and run-leads association in PostgreSQL.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from src.database.models.deepline import DeeplineRun, DeeplineRunLead


class DeeplineRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, run_id: str) -> Optional[DeeplineRun]:
        return self.session.scalar(select(DeeplineRun).where(DeeplineRun.id == run_id))

    def list_runs(self, campaign_id: Optional[str] = None, icp_id: Optional[str] = None) -> List[DeeplineRun]:
        stmt = select(DeeplineRun).order_by(desc(DeeplineRun.created_at))
        if campaign_id:
            stmt = stmt.where(DeeplineRun.campaign_id == campaign_id)
        if icp_id:
            stmt = stmt.where(DeeplineRun.icp_id == icp_id)
        return list(self.session.scalars(stmt).all())

    def record_run(
        self,
        run_id: str,
        icp_id: str,
        campaign_id: str,
        requested_count: int,
        discovered_count: int,
        valid_count: int,
        qualified_count: int,
        hard_disqualified_count: int,
        campaign_excluded_count: int,
        p1_count: int,
        p2_count: int,
        p3_count: int,
        mode: str = "DRY_RUN_SIMULATION",
        artifacts_path: Optional[str] = None,
    ) -> DeeplineRun:
        existing = self.get_by_id(run_id)
        if existing:
            return existing

        run = DeeplineRun(
            id=run_id,
            icp_id=icp_id,
            campaign_id=campaign_id,
            requested_count=requested_count,
            discovered_count=discovered_count,
            valid_count=valid_count,
            qualified_count=qualified_count,
            hard_disqualified_count=hard_disqualified_count,
            campaign_excluded_count=campaign_excluded_count,
            p1_count=p1_count,
            p2_count=p2_count,
            p3_count=p3_count,
            mode=mode,
            artifacts_path=artifacts_path,
        )
        self.session.add(run)
        self.session.flush()
        return run
