"""
smartlead_repository.py
Repository for Smartlead campaigns and staged leads in PostgreSQL.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.database.models.smartlead import SmartleadCampaign, SmartleadLead


class SmartleadRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_campaign(
        self,
        campaign_id: str,
        name: str,
        smartlead_campaign_id: Optional[str] = None,
        status: str = "DRAFT",
        track_settings: Optional[Dict[str, Any]] = None,
    ) -> SmartleadCampaign:
        stmt = select(SmartleadCampaign).where(SmartleadCampaign.campaign_id == campaign_id)
        existing = self.session.scalar(stmt)
        if existing:
            return existing

        camp = SmartleadCampaign(
            campaign_id=campaign_id,
            name=name,
            smartlead_campaign_id=smartlead_campaign_id,
            status=status,
            track_settings=track_settings or {"open_tracking": True, "click_tracking": True},
        )
        self.session.add(camp)
        self.session.flush()
        return camp

    def stage_lead(
        self,
        smartlead_campaign_id: int,
        lead_id: str,
        batch_index: int,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> SmartleadLead:
        stmt = select(SmartleadLead).where(
            SmartleadLead.smartlead_campaign_id == smartlead_campaign_id,
            SmartleadLead.lead_id == lead_id,
        )
        existing = self.session.scalar(stmt)
        if existing:
            existing.batch_index = batch_index
            if custom_fields:
                existing.custom_fields = custom_fields
            self.session.flush()
            return existing

        lead = SmartleadLead(
            smartlead_campaign_id=smartlead_campaign_id,
            lead_id=lead_id,
            batch_index=batch_index,
            status="STAGED",
            custom_fields=custom_fields or {},
        )
        self.session.add(lead)
        self.session.flush()
        return lead
