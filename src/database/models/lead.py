"""
lead.py
SQLAlchemy ORM models for Leads, Lead Research, Evidence, and Voice-of-Customer context.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(String(128), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    icp_id: Mapped[Optional[str]] = mapped_column(String(128), ForeignKey("icps.id", ondelete="SET NULL"), nullable=True, index=True)
    icp_version: Mapped[str] = mapped_column(String(32), default="1.0.0", index=True)
    environment: Mapped[str] = mapped_column(String(32), server_default="PRODUCTION", default="PRODUCTION", index=True)

    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email_status: Mapped[str] = mapped_column(String(64), default="PATTERN_CONFIRMED", index=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="DEEPLINE_DISCOVERY")

    # Scores & Priority
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    accessibility_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    outreach_priority_index: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    priority_level: Mapped[str] = mapped_column(String(32), default="P3", index=True)

    # Qualification & Personalization
    qualification_status: Mapped[str] = mapped_column(String(64), default="QUALIFIED", index=True)
    disqualification_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personalization_status: Mapped[str] = mapped_column(String(64), default="SIGNAL_VERIFIED", index=True)
    personalization_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voc_angle: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="leads")
    icp: Mapped[Optional["ICP"]] = relationship("ICP", back_populates="leads")
    research: Mapped[Optional["LeadResearch"]] = relationship("LeadResearch", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    evidence_items: Mapped[List["LeadEvidence"]] = relationship("LeadEvidence", back_populates="lead", cascade="all, delete-orphan")
    voc: Mapped[Optional["VoCContext"]] = relationship("VoCContext", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    email_draft: Mapped[Optional["EmailDraft"]] = relationship("EmailDraft", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    email_approval: Mapped[Optional["EmailApproval"]] = relationship("EmailApproval", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    outreach_events: Mapped[List["OutreachEvent"]] = relationship("OutreachEvent", back_populates="lead", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_leads_campaign_priority", "campaign_id", "priority_level"),
        Index("idx_leads_campaign_qual", "campaign_id", "qualification_status"),
        Index("idx_leads_opi_desc", "outreach_priority_index"),
    )


class LeadResearch(Base, TimestampMixin):
    __tablename__ = "lead_research"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(128), ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    raw_research: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    sources: Mapped[List[str]] = mapped_column(JSONB, default=list)
    pain_point: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevant_signal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="research")


class LeadEvidence(Base):
    __tablename__ = "lead_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(128), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_type: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_level: Mapped[str] = mapped_column(String(32), default="VERIFIED", index=True)
    source_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="evidence_items")


class VoCContext(Base, TimestampMixin):
    __tablename__ = "voc_context"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(128), ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    voc_angle: Mapped[str] = mapped_column(String(255), nullable=False)
    pain_point: Mapped[str] = mapped_column(Text, nullable=False)
    messaging_angle: Mapped[str] = mapped_column(Text, nullable=False)
    aedrix_value_prop: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="voc")
