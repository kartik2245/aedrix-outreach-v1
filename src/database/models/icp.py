"""
icp.py
SQLAlchemy ORM models for ICPs, ICP Versions, and Human ICP Approvals.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


class ICP(Base, TimestampMixin):
    __tablename__ = "icps"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(String(128), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="PENDING_REVIEW", index=True)
    environment: Mapped[str] = mapped_column(String(32), server_default="PRODUCTION", default="PRODUCTION", index=True)
    source: Mapped[str] = mapped_column(String(32), server_default="CLAUDE_GENERATED", default="CLAUDE_GENERATED", index=True)
    current_version: Mapped[str] = mapped_column(String(32), default="1.0.0", index=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="icps")
    versions: Mapped[List["ICPVersion"]] = relationship("ICPVersion", back_populates="icp", cascade="all, delete-orphan", order_by="desc(ICPVersion.created_at)")
    approval_record: Mapped[Optional["ICPApproval"]] = relationship("ICPApproval", back_populates="icp", uselist=False, cascade="all, delete-orphan")
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="icp")
    deepline_runs: Mapped[List["DeeplineRun"]] = relationship("DeeplineRun", back_populates="icp")

    __table_args__ = (
        Index("idx_icps_campaign_status", "campaign_id", "status"),
    )


class ICPVersion(Base):
    __tablename__ = "icp_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    icp_id: Mapped[str] = mapped_column(String(128), ForeignKey("icps.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    config_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    icp: Mapped["ICP"] = relationship("ICP", back_populates="versions")

    __table_args__ = (
        Index("idx_icp_versions_icp_ver", "icp_id", "version", unique=True),
    )


class ICPApproval(Base, TimestampMixin):
    __tablename__ = "icp_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    icp_id: Mapped[str] = mapped_column(String(128), ForeignKey("icps.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", index=True)
    status: Mapped[str] = mapped_column(String(64), default="PENDING_REVIEW", index=True)
    source: Mapped[str] = mapped_column(String(32), server_default="CLAUDE_GENERATED", default="CLAUDE_GENERATED", index=True)
    original_claude_icp: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    effective_icp: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reviewer: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deepline_eligible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deepline_run_ids: Mapped[List[str]] = mapped_column(JSONB, default=list)
    edit_history: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    audit_trail: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Relationships
    icp: Mapped["ICP"] = relationship("ICP", back_populates="approval_record")
