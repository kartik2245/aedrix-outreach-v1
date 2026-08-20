"""
campaign_repository.py
Repository for Campaign entity operations in PostgreSQL.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from src.database.models.campaign import Campaign


class CampaignRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, campaign_id: str) -> Optional[Campaign]:
        return self.session.scalar(select(Campaign).where(Campaign.id == campaign_id))

    def list_campaigns(self, status: Optional[str] = None) -> List[Campaign]:
        stmt = select(Campaign).order_by(desc(Campaign.created_at))
        if status:
            stmt = stmt.where(Campaign.status == status)
        return list(self.session.scalars(stmt).all())

    def upsert(
        self,
        campaign_id: str,
        name: str,
        objective: Optional[str] = None,
        status: str = "ACTIVE",
        target_geography: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Campaign:
        existing = self.get_by_id(campaign_id)
        if existing:
            existing.name = name
            if objective is not None:
                existing.objective = objective
            existing.status = status
            if target_geography is not None:
                existing.target_geography = target_geography
            if settings is not None:
                existing.settings = settings
            self.session.flush()
            return existing

        campaign = Campaign(
            id=campaign_id,
            name=name,
            objective=objective,
            status=status,
            target_geography=target_geography,
            settings=settings or {},
        )
        self.session.add(campaign)
        self.session.flush()
        return campaign
