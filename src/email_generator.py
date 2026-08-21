"""
email_generator.py
Production Email Generation Engine for Aedrix Cold Outreach System (Python 3.12).
Conforms strictly to the "Aedrix Sequences by Company Role" document.
Grounds copy in fixed templates rather than LLM-generated text.
"""

import hashlib
import re
from typing import Dict, Any, List, Optional, Tuple

from src.models import (
    LeadIntelligenceOutput,
    EmailGenerationResult,
    PersonalizationNoteStatus,
    VoCContext,
    PersonalizationQAResult,
)
from src.templates import TEMPLATES
from src.personalization.voc_engine import VoCEngine
from src.personalization.personalization_qa import PersonalizationQA


class EmailGenerator:
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        claude_client: Optional[Any] = None,
        voc_engine: Optional[VoCEngine] = None,
        qa_engine: Optional[PersonalizationQA] = None,
    ):
        self.llm_client = llm_client or claude_client
        self.claude_client = self.llm_client
        self.voc_engine = voc_engine or VoCEngine()
        self.qa_engine = qa_engine or PersonalizationQA()

    def get_subject_variant(self, email: str) -> str:
        """Deterministically resolves Subject Variant A or B based on email hash."""
        h = hashlib.md5(email.lower().strip().encode("utf-8")).hexdigest()
        return "A" if int(h, 16) % 2 == 0 else "B"

    def format_copy(self, template_body: str, lead_intel: LeadIntelligenceOutput) -> str:
        """Formats the template body with parsed variables and light spintax."""
        names = lead_intel.contact_name.strip().split()
        first_name = names[0].capitalize() if names else ""
        
        # Guard: Never generate fallback like "Hi there"
        if not first_name:
            first_name = ""

        body = template_body.replace("{{first_name}}", first_name)
        body = body.replace("{{company}}", lead_intel.company_name)

        # Apply opener spintax if body starts with "Hi "
        if body.startswith("Hi "):
            body = "{Hi|Hello} " + body[3:]

        # Append closer & signature with spintax
        unsubscribe_url = f"https://aedrix.com/unsubscribe?email={lead_intel.email}"
        sig = (
            "\n\n{Best|All the best|Best regards},\n\n"
            "Alex Mitchell\n"
            "Outreach Manager, Aedrix\n"
            "HQ: Panchkula, Haryana, India\n"
            f"To unsubscribe, click here: {unsubscribe_url}"
        )

        if "Alex Mitchell" not in body:
            body += sig

        # Resolve spintax deterministically based on email hash + token content
        def replace_spin(match):
            options = match.group(1).split("|")
            h = hashlib.md5((lead_intel.email.lower().strip() + match.group(0)).encode("utf-8")).hexdigest()
            idx = int(h, 16) % len(options)
            return options[idx]

        body = re.sub(r"\{([^{}]+)\}", replace_spin, body)
        return body

    def generate_email_1(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext] = None,
    ) -> EmailGenerationResult:
        """Generates Email 1 using active LLM provider or fixed template fallback."""
        if self.llm_client and hasattr(self.llm_client, "generate_email_1"):
            return self.llm_client.generate_email_1(lead_intel, voc_context)

        track = lead_intel.role_track
        if track not in TEMPLATES:
            track = "R2"

        variant = self.get_subject_variant(lead_intel.email)
        tmpl = TEMPLATES[track]["email_1"]
        
        subject = tmpl["subject_a"] if variant == "A" else tmpl["subject_b"]
        body = self.format_copy(tmpl["body"], lead_intel)
        word_count = len(body.split())

        return EmailGenerationResult(
            email_type="EMAIL_1",
            subject=subject,
            body=body,
            word_count=word_count,
            personalization_status=lead_intel.personalization_note_status,
            evidence_used=[lead_intel.relevant_signal or "Fixed role track template"],
            generation_mode="DRY_RUN_TEMPLATE"
        )

    def generate_followup_a(
        self,
        lead_intel: LeadIntelligenceOutput,
        email_1: EmailGenerationResult,
        voc_context: Optional[VoCContext] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up A using active LLM provider or fixed template fallback."""
        if self.llm_client and hasattr(self.llm_client, "generate_followup_a"):
            return self.llm_client.generate_followup_a(lead_intel, email_1, voc_context)

        track = lead_intel.role_track
        if track not in TEMPLATES:
            track = "R2"

        tmpl = TEMPLATES[track]["followup_a"]
        body = self.format_copy(tmpl["body"], lead_intel)
        word_count = len(body.split())

        return EmailGenerationResult(
            email_type="FOLLOWUP_A",
            subject=f"Re: {email_1.subject}",
            body=body,
            word_count=word_count,
            personalization_status=lead_intel.personalization_note_status,
            evidence_used=["Same-thread follow-up"],
            generation_mode="DRY_RUN_TEMPLATE"
        )

    def generate_followup_b(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up B using active LLM provider or fixed template fallback."""
        if self.llm_client and hasattr(self.llm_client, "generate_followup_b"):
            return self.llm_client.generate_followup_b(lead_intel, voc_context)

        track = lead_intel.role_track
        if track not in TEMPLATES:
            track = "R2"

        is_hrb = False
        if track in ("R2", "R5"):
            ctx = lead_intel.relevant_signal or ""
            company_name = lead_intel.company_name.lower()
            industry = lead_intel.industry.lower() if lead_intel.industry else ""
            if "hrb" in ctx.lower() or "residential" in ctx.lower() or "building safety" in ctx.lower() or "golden thread" in ctx.lower() or "residential" in industry:
                is_hrb = True

        variant = self.get_subject_variant(lead_intel.email)
        
        if is_hrb and "followup_b_hrb" in TEMPLATES[track]:
            tmpl = TEMPLATES[track]["followup_b_hrb"]
        else:
            tmpl = TEMPLATES[track]["followup_b"]

        subject = tmpl["subject_a"] if variant == "A" else tmpl["subject_b"]
        body = self.format_copy(tmpl["body"], lead_intel)
        word_count = len(body.split())

        return EmailGenerationResult(
            email_type="FOLLOWUP_B",
            subject=subject,
            body=body,
            word_count=word_count,
            personalization_status=lead_intel.personalization_note_status,
            evidence_used=["Unopened follow-up branch"],
            generation_mode="DRY_RUN_TEMPLATE"
        )

    def generate_touch_3(self, lead_intel: LeadIntelligenceOutput) -> EmailGenerationResult:
        """Touch 3 generation is non-executable in AEDRIX V1 sequence."""
        raise NotImplementedError("Touch 3 generation is non-executable in AEDRIX V1 sequence (Email 1, Follow-up A, Follow-up B only).")

    def generate_touch_4(self, lead_intel: LeadIntelligenceOutput) -> EmailGenerationResult:
        """Touch 4 generation is non-executable in AEDRIX V1 sequence."""
        raise NotImplementedError("Touch 4 generation is non-executable in AEDRIX V1 sequence (Email 1, Follow-up A, Follow-up B only).")

    def generate_touch_5(self, lead_intel: LeadIntelligenceOutput, touch_4_subject: str) -> EmailGenerationResult:
        """Touch 5 generation is non-executable in AEDRIX V1 sequence."""
        raise NotImplementedError("Touch 5 generation is non-executable in AEDRIX V1 sequence (Email 1, Follow-up A, Follow-up B only).")

    def generate_and_validate_all(
        self,
        lead_intel: LeadIntelligenceOutput
    ) -> Tuple[EmailGenerationResult, EmailGenerationResult, EmailGenerationResult, VoCContext, PersonalizationQAResult]:
        """
        Generates 3-step email sequence (Email 1, Follow-up A, Follow-up B) and runs QA check.
        Returns 5-tuple: (e1, fa, fb, voc_context, qa_result).
        """
        voc_context = self.voc_engine.map_lead_voc(lead_intel)
        e1 = self.generate_email_1(lead_intel, voc_context)
        fa = self.generate_followup_a(lead_intel, e1, voc_context)
        fb = self.generate_followup_b(lead_intel, voc_context)

        # QA engine checks active sequence steps (Email 1, Follow-up A, Follow-up B)
        qa_result = self.qa_engine.validate_lead_drafts(
            lead_intel, e1, fa, fb
        )

        return e1, fa, fb, voc_context, qa_result
