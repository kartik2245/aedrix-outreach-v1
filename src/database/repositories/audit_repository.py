"""
audit_repository.py
Repository for immutable audit logs and outreach state machine events in PostgreSQL.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from src.database.models.audit import AuditLog, OutreachEvent


class AuditRepository:
    def __init__(self, session: Session):
        self.session = session

    def log_action(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str = "SYSTEM",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            details=details or {},
        )
        self.session.add(log)
        self.session.flush()
        return log

    def list_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditLog]:
        stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        return list(self.session.scalars(stmt).all())

    def record_outreach_event(
        self,
        lead_id: str,
        campaign_id: str,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> OutreachEvent:
        event = OutreachEvent(
            lead_id=lead_id,
            campaign_id=campaign_id,
            event_type=event_type,
            payload=payload or {},
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_events_for_lead(self, lead_id: str) -> List[OutreachEvent]:
        stmt = select(OutreachEvent).where(OutreachEvent.lead_id == lead_id).order_by(desc(OutreachEvent.occurred_at))
        return list(self.session.scalars(stmt).all())
