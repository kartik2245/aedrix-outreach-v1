"""
campaign.py
SQLAlchemy ORM model for Campaigns.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="ACTIVE", index=True)
    environment: Mapped[str] = mapped_column(String(32), server_default="PRODUCTION", default="PRODUCTION", index=True)
    target_geography: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Relationships
    icps: Mapped[List["ICP"]] = relationship("ICP", back_populates="campaign", cascade="all, delete-orphan")
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="campaign", cascade="all, delete-orphan")
    deepline_runs: Mapped[List["DeeplineRun"]] = relationship("DeeplineRun", back_populates="campaign", cascade="all, delete-orphan")
    smartlead_campaigns: Mapped[List["SmartleadCampaign"]] = relationship("SmartleadCampaign", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_campaigns_created_at", "created_at"),
    )
