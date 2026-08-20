"""
audit.py
SQLAlchemy ORM models for Immutable Audit Logs and Outreach State Machine Events.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), default="SYSTEM", index=True)
    environment: Mapped[str] = mapped_column(String(32), server_default="PRODUCTION", default="PRODUCTION", index=True)
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(128), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="outreach_events")

    __table_args__ = (
        Index("idx_outreach_events_lead_time", "lead_id", "occurred_at"),
    )
