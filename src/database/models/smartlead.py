"""
smartlead.py
SQLAlchemy ORM models for Smartlead Staged Campaigns and Leads.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class SmartleadCampaign(Base):
    __tablename__ = "smartlead_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(String(128), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    smartlead_campaign_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="DRAFT", index=True)
    track_settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="smartlead_campaigns")
    staged_leads: Mapped[List["SmartleadLead"]] = relationship("SmartleadLead", back_populates="smartlead_campaign", cascade="all, delete-orphan")


class SmartleadLead(Base):
    __tablename__ = "smartlead_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    smartlead_campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("smartlead_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id: Mapped[str] = mapped_column(String(128), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_index: Mapped[int] = mapped_column(Integer, default=1, index=True)
    status: Mapped[str] = mapped_column(String(64), default="STAGED", index=True)
    custom_fields: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    staged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    smartlead_campaign: Mapped["SmartleadCampaign"] = relationship("SmartleadCampaign", back_populates="staged_leads")
