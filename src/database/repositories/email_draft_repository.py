"""
email_draft_repository.py
Repository for Email Draft operations in PostgreSQL with Immutability Guarantees.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.database.models.email import EmailDraft


class EmailDraftRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_lead_id(self, lead_id: str) -> Optional[EmailDraft]:
        return self.session.scalar(select(EmailDraft).where(EmailDraft.lead_id == lead_id))

    def upsert_draft(
        self,
        lead_id: str,
        ai_original_email_1: str,
        ai_original_followup_a: str,
        ai_original_followup_b: str,
        edited_email_1: Optional[str] = None,
        edited_followup_a: Optional[str] = None,
        edited_followup_b: Optional[str] = None,
        qa_status: str = "PASS",
        qa_reasons: Optional[List[str]] = None,
    ) -> EmailDraft:
        existing = self.get_by_lead_id(lead_id)
        if existing:
            # Immutability Guarantee: Never overwrite original AI drafts if already present
            if not existing.ai_original_email_1:
                existing.ai_original_email_1 = ai_original_email_1
            if not existing.ai_original_followup_a:
                existing.ai_original_followup_a = ai_original_followup_a
            if not existing.ai_original_followup_b:
                existing.ai_original_followup_b = ai_original_followup_b

            if edited_email_1 is not None:
                existing.edited_email_1 = edited_email_1
            if edited_followup_a is not None:
                existing.edited_followup_a = edited_followup_a
            if edited_followup_b is not None:
                existing.edited_followup_b = edited_followup_b

            existing.qa_status = qa_status
            if qa_reasons is not None:
                existing.qa_reasons = qa_reasons
            self.session.flush()
            return existing

        draft = EmailDraft(
            lead_id=lead_id,
            ai_original_email_1=ai_original_email_1,
            ai_original_followup_a=ai_original_followup_a,
            ai_original_followup_b=ai_original_followup_b,
            edited_email_1=edited_email_1,
            edited_followup_a=edited_followup_a,
            edited_followup_b=edited_followup_b,
            qa_status=qa_status,
            qa_reasons=qa_reasons or [],
        )
        self.session.add(draft)
        self.session.flush()
        return draft
