"""
deepline.py
SQLAlchemy ORM models for Deepline Lead Discovery Runs.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class DeeplineRun(Base):
    __tablename__ = "deepline_runs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    icp_id: Mapped[str] = mapped_column(String(128), ForeignKey("icps.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(String(128), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)

    requested_count: Mapped[int] = mapped_column(Integer, default=100)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_count: Mapped[int] = mapped_column(Integer, default=0)
    qualified_count: Mapped[int] = mapped_column(Integer, default=0)
    hard_disqualified_count: Mapped[int] = mapped_column(Integer, default=0)
    campaign_excluded_count: Mapped[int] = mapped_column(Integer, default=0)
    p1_count: Mapped[int] = mapped_column(Integer, default=0)
    p2_count: Mapped[int] = mapped_column(Integer, default=0)
    p3_count: Mapped[int] = mapped_column(Integer, default=0)

    mode: Mapped[str] = mapped_column(String(64), default="DRY_RUN_SIMULATION")
    artifacts_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="deepline_runs")
    icp: Mapped["ICP"] = relationship("ICP", back_populates="deepline_runs")
    run_leads: Mapped[List["DeeplineRunLead"]] = relationship("DeeplineRunLead", back_populates="run", cascade="all, delete-orphan")


class DeeplineRunLead(Base):
    __tablename__ = "deepline_run_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), ForeignKey("deepline_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id: Mapped[str] = mapped_column(String(128), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="QUALIFIED", index=True)
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Relationships
    run: Mapped["DeeplineRun"] = relationship("DeeplineRun", back_populates="run_leads")
