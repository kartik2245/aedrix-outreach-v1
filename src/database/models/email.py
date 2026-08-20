"""
email.py
SQLAlchemy ORM models for Email Drafts and Human Email Approvals.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


class EmailDraft(Base, TimestampMixin):
    __tablename__ = "email_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(128), ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Immutability Guarantee: AI originals are NEVER overwritten
    ai_original_email_1: Mapped[str] = mapped_column(Text, nullable=False)
    ai_original_followup_a: Mapped[str] = mapped_column(Text, nullable=False)
    ai_original_followup_b: Mapped[str] = mapped_column(Text, nullable=False)

    # Human edits
    edited_email_1: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edited_followup_a: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edited_followup_b: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # QA Protection
    qa_status: Mapped[str] = mapped_column(String(32), default="PASS", index=True)
    qa_reasons: Mapped[List[str]] = mapped_column(JSONB, default=list)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="email_draft")


class EmailApproval(Base, TimestampMixin):
    __tablename__ = "email_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(128), ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    approval_status: Mapped[str] = mapped_column(String(64), default="PENDING_REVIEW", index=True)
    reviewer: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    smartlead_eligible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flag_no_strong_signal: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="email_approval")

    __table_args__ = (
        Index("idx_email_approvals_status_eligible", "approval_status", "smartlead_eligible"),
    )
