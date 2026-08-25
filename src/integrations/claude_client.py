"""
claude_client.py
Official Anthropic Claude API Integration for Aedrix Cold Outreach System (Python 3.12).

Responsibilities:
- Reads credentials from environment variables (ANTHROPIC_API_KEY, CLAUDE_MODEL, DRY_RUN, SEND_EMAILS).
- Generates structured, zero-hallucination email drafts (Email 1, Follow-up A, Follow-up B).
- Feeds structured lead intelligence, VoC angle, and evidence levels into Claude.
- Strictly instructs Claude not to fabricate any facts, metrics, or personal achievements.
- Parses and validates JSON responses cleanly.
- Seamlessly falls back to high-fidelity offline generation when DRY_RUN=true or API key is absent.
"""

import json
import os
import re
from typing import Dict, Any, Optional, Union
from src.models import (
    LeadIntelligenceOutput,
    EmailGenerationResult,
    PersonalizationNoteStatus,
    VoCContext,
    EvidenceLevel,
)
from src.utils.subject_sanitizer import sanitize_subject


def load_env_file_if_present(env_path: Optional[str] = None, override: bool = False) -> None:
    """Simple .env file loader."""
    if not env_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k:
                    if override or k not in os.environ:
                        os.environ[k] = v


class ClaudeClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dry_run: Optional[bool] = None,
        anthropic_client: Optional[Any] = None,
    ):
        load_env_file_if_present()

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        
        env_dry_run = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
        self.dry_run = dry_run if dry_run is not None else env_dry_run
        self.send_emails = os.getenv("SEND_EMAILS", "false").lower() in ("true", "1", "yes")

        # Initialise Anthropic SDK client if key exists
        self.client = anthropic_client
        if not self.client and self.api_key and not self.dry_run:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception:
                self.client = None

    def generate_email_1(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext] = None,
        icp_config: Optional[Any] = None,
    ) -> EmailGenerationResult:
        """Generates Email 1 (Max 120 words)."""
        prompt = self._build_email_1_prompt(lead_intel, voc_context, icp_config)

        if self.dry_run or not self.client:
            return self._generate_offline_email_1(lead_intel, voc_context, icp_config)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                temperature=0.2,
                system=prompt["system"],
                messages=[{"role": "user", "content": prompt["user"]}]
            )
            raw_text = response.content[0].text
            parsed = self.parse_claude_json_response(raw_text)
            raw_body = parsed.get("body", "").strip()
            body = self._post_process_copy_compliance(raw_body, lead_intel, voc_context, icp_config)
            raw_subject = parsed.get("subject", "").strip()
            voc_angle = voc_context.voc_angle if voc_context and voc_context.voc_angle else f"{lead_intel.industry} Operations"
            prod = getattr(voc_context, "product_or_service", None) or getattr(icp_config, "product_or_service", None) or lead_intel.industry
            subject = sanitize_subject(raw_subject, company_name=lead_intel.company_name, product_or_industry=prod, voc_angle=voc_angle, email_type="EMAIL_1", max_words=6)
            word_count = len(body.split())

            return EmailGenerationResult(
                email_type="EMAIL_1",
                subject=subject,
                body=body,
                word_count=word_count,
                personalization_status=lead_intel.personalization_note_status,
                evidence_used=[lead_intel.relevant_signal or "Verified corporate signal"],
                generation_mode="CLAUDE_API"
            )
        except Exception:
            return self._generate_offline_email_1(lead_intel, voc_context, icp_config)

    def generate_followup_a(
        self,
        lead_intel: LeadIntelligenceOutput,
        email_1: EmailGenerationResult,
        voc_context: Optional[VoCContext] = None,
        icp_config: Optional[Any] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up A (Opened Email 1, No Reply - Max 90 words)."""
        prompt = self._build_followup_a_prompt(lead_intel, email_1, voc_context, icp_config)

        if self.dry_run or not self.client:
            return self._generate_offline_followup_a(lead_intel, email_1, voc_context, icp_config)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.2,
                system=prompt["system"],
                messages=[{"role": "user", "content": prompt["user"]}]
            )
            raw_text = response.content[0].text
            parsed = self.parse_claude_json_response(raw_text)
            raw_body = parsed.get("body", "").strip()
            body = self._post_process_copy_compliance(raw_body, lead_intel, voc_context, icp_config)
            raw_subject = parsed.get("subject", f"Re: {email_1.subject}").strip()
            prod = getattr(voc_context, "product_or_service", None) or getattr(icp_config, "product_or_service", None) or lead_intel.industry
            subject = sanitize_subject(raw_subject, company_name=lead_intel.company_name, product_or_industry=prod, voc_angle=getattr(voc_context, "voc_angle", None), email_type="FOLLOWUP_A", max_words=6)
            word_count = len(body.split())

            return EmailGenerationResult(
                email_type="FOLLOWUP_A",
                subject=subject,
                body=body,
                word_count=word_count,
                personalization_status=lead_intel.personalization_note_status,
                evidence_used=["Email 1 Open Event Context"],
                generation_mode="CLAUDE_API"
            )
        except Exception:
            return self._generate_offline_followup_a(lead_intel, email_1, voc_context, icp_config)

    def generate_followup_b(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext] = None,
        icp_config: Optional[Any] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up B (Unopened Email 1, Pivoted Angle - Max 90 words)."""
        prompt = self._build_followup_b_prompt(lead_intel, voc_context, icp_config)

        if self.dry_run or not self.client:
            return self._generate_offline_followup_b(lead_intel, voc_context, icp_config)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.2,
                system=prompt["system"],
                messages=[{"role": "user", "content": prompt["user"]}]
            )
            raw_text = response.content[0].text
            parsed = self.parse_claude_json_response(raw_text)
            raw_body = parsed.get("body", "").strip()
            body = self._post_process_copy_compliance(raw_body, lead_intel, voc_context, icp_config)
            raw_subject = parsed.get("subject", "").strip()
            voc_angle = voc_context.voc_angle if voc_context and voc_context.voc_angle else f"{lead_intel.industry} Operations"
            prod = getattr(voc_context, "product_or_service", None) or getattr(icp_config, "product_or_service", None) or lead_intel.industry
            subject = sanitize_subject(raw_subject, company_name=lead_intel.company_name, product_or_industry=prod, voc_angle=voc_angle, email_type="FOLLOWUP_B", max_words=6)
            word_count = len(body.split())

            return EmailGenerationResult(
                email_type="FOLLOWUP_B",
                subject=subject,
                body=body,
                word_count=word_count,
                personalization_status=lead_intel.personalization_note_status,
                evidence_used=["Pivoted Angle: Operational Roadmap"],
                generation_mode="CLAUDE_API"
            )
        except Exception:
            return self._generate_offline_followup_b(lead_intel, voc_context, icp_config)

    def parse_claude_json_response(self, raw_text: str) -> Dict[str, str]:
        """Parses JSON from Claude response, safely handling markdown wrappers."""
        text = raw_text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        else:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1].strip()

        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return {
                    "subject": str(data.get("subject", "")),
                    "body": str(data.get("body", ""))
                }
        except json.JSONDecodeError:
            pass

        return {"subject": "Platform Overview", "body": raw_text.strip()}

    def _build_email_1_prompt(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext],
        icp_config: Optional[Any] = None,
    ) -> Dict[str, str]:
        """Constructs Zero-Hallucination Email 1 prompt."""
        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        prod = getattr(voc_context, "product_or_service", None) or getattr(icp_config, "product_or_service", None) or getattr(voc_context, "aedrix_value_prop", None) or f"software and services for {lead_intel.industry} organizations"
        cta_text = getattr(voc_context, "cta", None) or getattr(icp_config, "cta", None) or "Are you open to a brief 2-minute overview this week?"

        system_prompt = (
            f"You are a senior B2B cold outreach copywriter representing {brand} — {prod}.\n\n"
            "STRICT ZERO-HALLUCINATION RULES:\n"
            "1. Use ONLY the verified facts, signals, and personalization notes provided in the input JSON.\n"
            "2. NEVER invent company facts, achievements, projects, promotions, technologies, financial metrics, customer names, or dates.\n"
            "3. If a fact is not present in the supplied evidence, do NOT state it as fact.\n"
            "4. Word count MUST NOT exceed 120 words.\n"
            f"5. Tone must be concise, professional, human, relevant to {lead_intel.industry}, and free of generic AI spam.\n"
            f"6. End with a low-pressure CTA: '{cta_text}'.\n"
            "7. Return ONLY a valid JSON object with 'subject' and 'body' keys."
        )

        user_context = {
            "campaign": {
                "name": getattr(voc_context, "campaign_name", None) or getattr(icp_config, "name", None),
                "objective": getattr(voc_context, "campaign_objective", None) or getattr(icp_config, "campaign_description", None),
                "product_or_service": prod,
                "value_proposition": getattr(voc_context, "value_proposition", None) or getattr(voc_context, "aedrix_value_prop", None),
                "cta": cta_text,
            },
            "icp": {
                "geography": getattr(icp_config, "geography", None).allowed_country_keywords if hasattr(getattr(icp_config, "geography", None), "allowed_country_keywords") else [],
                "industries": getattr(icp_config, "industries", [lead_intel.industry]),
                "company_size": getattr(icp_config, "company_size", lead_intel.company_size),
                "target_personas": getattr(icp_config, "target_personas", []),
            },
            "lead": {
                "company_name": lead_intel.company_name,
                "contact_name": lead_intel.contact_name,
                "job_title": lead_intel.job_title,
                "industry": lead_intel.industry,
                "company_size": lead_intel.company_size,
                "linkedin_url": lead_intel.linkedin_url,
                "relevant_signal": lead_intel.relevant_signal,
                "pain_point": lead_intel.pain_point if lead_intel.pain_point_evidence != EvidenceLevel.INFERRED else f"Potential operational challenges in {lead_intel.industry}",
                "pain_point_evidence": lead_intel.pain_point_evidence.value,
                "personalization_note": lead_intel.personalization_note,
                "personalization_note_status": lead_intel.personalization_note_status.value,
            },
            "voc_angle": voc_context.voc_angle if voc_context else f"{lead_intel.industry} Operations",
            "value_prop": voc_context.aedrix_value_prop if voc_context else f"{brand} supports {lead_intel.industry} teams."
        }

        user_prompt = (
            f"Generate Email 1 draft (under 120 words) for the following verified lead context:\n"
            f"```json\n{json.dumps(user_context, indent=2)}\n```\n\n"
            f"Return JSON format:\n{{\"subject\": \"...\", \"body\": \"...\"}}"
        )

        return {"system": system_prompt, "user": user_prompt}

    def _build_followup_a_prompt(
        self,
        lead_intel: LeadIntelligenceOutput,
        email_1: EmailGenerationResult,
        voc_context: Optional[VoCContext],
        icp_config: Optional[Any] = None,
    ) -> Dict[str, str]:
        """Constructs Zero-Hallucination Follow-up A prompt."""
        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        voc_angle = voc_context.voc_angle if voc_context else f"{lead_intel.industry} Operations"
        system_prompt = (
            f"You are a senior B2B cold outreach copywriter representing {brand}. "
            "Write Follow-up A (opened Email 1 but did not reply). Max 90 words. "
            "Never invent facts. Return ONLY valid JSON with 'subject' and 'body'."
        )
        user_prompt = (
            f"Company: {lead_intel.company_name}\n"
            f"Contact: {lead_intel.contact_name}\n"
            f"Previous Email 1 Subject: {email_1.subject}\n"
            f"VoC Angle: {voc_angle}\n"
            f"Generate Follow-up A under 90 words in JSON format: {{\"subject\": \"...\", \"body\": \"...\"}}"
        )
        return {"system": system_prompt, "user": user_prompt}

    def _build_followup_b_prompt(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext],
        icp_config: Optional[Any] = None,
    ) -> Dict[str, str]:
        """Constructs Zero-Hallucination Follow-up B prompt."""
        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        voc_angle = voc_context.voc_angle if voc_context else f"{lead_intel.industry} Operations"
        system_prompt = (
            f"You are a senior B2B cold outreach copywriter representing {brand}. "
            f"Write Follow-up B (unopened Email 1, pivoted angle to {voc_angle}). Max 90 words. "
            "Never invent facts. Return ONLY valid JSON with 'subject' and 'body'."
        )
        user_prompt = (
            f"Company: {lead_intel.company_name}\n"
            f"Contact: {lead_intel.contact_name}\n"
            f"Pivoted Angle: {voc_angle}\n"
            f"Generate Follow-up B under 90 words in JSON format: {{\"subject\": \"...\", \"body\": \"...\"}}"
        )
        return {"system": system_prompt, "user": user_prompt}

    def _post_process_copy_compliance(
        self,
        body: str,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext] = None,
        icp_config: Optional[Any] = None,
    ) -> str:
        """
        Guarantees:
        1. Strips any internal system codes/labels (NO_STRONG_SIGNAL, SIGNAL_VERIFIED, HARD_DISQUALIFIED, etc.).
        2. Ensures an approved signature exists.
        3. Ensures the canonical unsubscribe footer exists with the lead's email address.
        """
        clean_body = body or ""

        # Forbidden internal labels that must never leak to prospect
        forbidden_labels = [
            "NO_STRONG_SIGNAL",
            "SIGNAL_VERIFIED",
            "HARD_DISQUALIFIED",
            "CAMPAIGN_EXCLUDED",
            "INVALID_BOUNCED",
        ]
        for label in forbidden_labels:
            if label.lower() in clean_body.lower():
                clean_body = re.sub(re.escape(label), "", clean_body, flags=re.IGNORECASE).strip()

        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        sender = getattr(voc_context, "sender_name", None) or getattr(icp_config, "sender_name", None) or f"{brand} Team"
        email_addr = (lead_intel.email or "contact@example.com").strip()
        unsub_url = f"https://aedrix.com/unsubscribe?email={email_addr}"

        body_lower = clean_body.lower()
        has_sig = any(sig in clean_body for sig in ["Alex Mitchell", "Aedrix Team", "Best regards", "Outreach Manager"])
        has_unsub = ("unsubscribe" in body_lower or "opt out" in body_lower) and ("https://" in body_lower or "aedrix.com" in body_lower or "click here" in body_lower or "reply unsubscribe" in body_lower)

        if not has_sig:
            clean_body = f"{clean_body.rstrip()}\n\nBest regards,\n{sender}"

        if not has_unsub:
            clean_body = f"{clean_body.rstrip()}\nOutreach Manager, {brand}\nTo unsubscribe, click here: {unsub_url}"

        return clean_body

    def _generate_offline_email_1(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext],
        icp_config: Optional[Any] = None,
    ) -> EmailGenerationResult:
        """High-fidelity deterministic offline template generator."""
        contact_first_name = (lead_intel.contact_name or "there").strip().split(" ")[0]
        if not contact_first_name or contact_first_name.lower() == "there":
            contact_first_name = "there"
        company = lead_intel.company_name
        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        sender = getattr(voc_context, "sender_name", None) or getattr(icp_config, "sender_name", None) or f"{brand} Team"
        cta_text = getattr(voc_context, "cta", None) or getattr(icp_config, "cta", None) or "Are you open to a brief 2-minute overview this week?"

        is_signal_verified = lead_intel.personalization_note_status == PersonalizationNoteStatus.SIGNAL_VERIFIED
        has_valid_note = (
            is_signal_verified
            and lead_intel.personalization_note
            and lead_intel.personalization_note != "NO_STRONG_SIGNAL"
            and "NO_STRONG_SIGNAL" not in str(lead_intel.personalization_note)
        )

        if has_valid_note:
            personalization_text = lead_intel.personalization_note
            evidence_used = [lead_intel.relevant_signal or "Verified corporate signal"]
        else:
            personalization_text = f"Given your role leading {lead_intel.job_title} operations at {company}, I thought you'd be interested in how {brand} supports {lead_intel.industry} teams."
            evidence_used = ["Baseline Value Proposition"]

        val_prop = (
            getattr(voc_context, "aedrix_value_prop", None)
            or getattr(icp_config, "value_proposition", None)
            or f"{brand} provides solutions to streamline {lead_intel.industry} workflows."
        )

        voc_angle = getattr(voc_context, "voc_angle", None) or getattr(icp_config, "voc_context", None) or f"{lead_intel.industry} Operations"
        prod = getattr(voc_context, "product_or_service", None) or getattr(icp_config, "product_or_service", None) or lead_intel.industry
        subject = sanitize_subject(None, company_name=company, product_or_industry=prod, voc_angle=voc_angle, email_type="EMAIL_1", max_words=6)

        raw_body = (
            f"Hi {contact_first_name},\n\n"
            f"{personalization_text}\n\n"
            f"{val_prop}\n\n"
            f"{cta_text}\n\nBest regards,\n{sender}"
        )
        body = self._post_process_copy_compliance(raw_body, lead_intel, voc_context, icp_config)
        word_count = len(body.split())

        return EmailGenerationResult(
            email_type="EMAIL_1",
            subject=subject,
            body=body,
            word_count=word_count,
            personalization_status=lead_intel.personalization_note_status,
            evidence_used=evidence_used,
            generation_mode="DRY_RUN_TEMPLATE"
        )

    def _generate_offline_followup_a(
        self,
        lead_intel: LeadIntelligenceOutput,
        email_1: EmailGenerationResult,
        voc_context: Optional[VoCContext],
        icp_config: Optional[Any] = None,
    ) -> EmailGenerationResult:
        """Offline Follow-up A template."""
        contact_first_name = (lead_intel.contact_name or "there").strip().split(" ")[0]
        if not contact_first_name or contact_first_name.lower() == "there":
            contact_first_name = "there"
        company = lead_intel.company_name
        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        sender = getattr(voc_context, "sender_name", None) or getattr(icp_config, "sender_name", None) or f"{brand} Team"
        voc_angle = getattr(voc_context, "voc_angle", None) or getattr(icp_config, "voc_context", None) or f"{lead_intel.industry} Operations"
        prod = getattr(voc_context, "product_or_service", None) or getattr(icp_config, "product_or_service", None) or lead_intel.industry

        subject = sanitize_subject(f"Re: {email_1.subject}", company_name=company, product_or_industry=prod, voc_angle=voc_angle, email_type="FOLLOWUP_A", max_words=6)
        raw_body = (
            f"Hi {contact_first_name},\n\n"
            f"Following up on my previous note regarding operations for {company}.\n\n"
            f"Given {company}'s focus on operational delivery, I wanted to highlight how {brand} specifically helps teams in {lead_intel.industry}.\n\n"
            f"Would Thursday afternoon work for a quick conversation?\n\nBest regards,\n{sender}"
        )
        body = self._post_process_copy_compliance(raw_body, lead_intel, voc_context, icp_config)
        word_count = len(body.split())

        return EmailGenerationResult(
            email_type="FOLLOWUP_A",
            subject=subject,
            body=body,
            word_count=word_count,
            personalization_status=lead_intel.personalization_note_status,
            evidence_used=["Email 1 Open Event Context"],
            generation_mode="DRY_RUN_TEMPLATE"
        )

    def _generate_offline_followup_b(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext],
        icp_config: Optional[Any] = None,
    ) -> EmailGenerationResult:
        """Offline Follow-up B template."""
        contact_first_name = (lead_intel.contact_name or "there").strip().split(" ")[0]
        if not contact_first_name or contact_first_name.lower() == "there":
            contact_first_name = "there"
        company = lead_intel.company_name
        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        sender = getattr(voc_context, "sender_name", None) or getattr(icp_config, "sender_name", None) or f"{brand} Team"
        val_prop = getattr(voc_context, "aedrix_value_prop", None) or getattr(icp_config, "value_proposition", None) or f"{brand} delivers operational efficiency solutions."
        voc_angle = getattr(voc_context, "voc_angle", None) or getattr(icp_config, "voc_context", None) or f"{lead_intel.industry} Operations"
        prod = getattr(voc_context, "product_or_service", None) or getattr(icp_config, "product_or_service", None) or lead_intel.industry

        subject = sanitize_subject(None, company_name=company, product_or_industry=prod, voc_angle=voc_angle, email_type="FOLLOWUP_B", max_words=6)
        raw_body = (
            f"Hi {contact_first_name},\n\n"
            f"Pivoting from my earlier message: {val_prop}\n\n"
            f"Would you be open to exploring how this fits your operational roadmap?\n\nBest regards,\n{sender}"
        )
        body = self._post_process_copy_compliance(raw_body, lead_intel, voc_context, icp_config)
        word_count = len(body.split())

        return EmailGenerationResult(
            email_type="FOLLOWUP_B",
            subject=subject,
            body=body,
            word_count=word_count,
            personalization_status=lead_intel.personalization_note_status,
            evidence_used=["Pivoted Operational Angle"],
            generation_mode="DRY_RUN_TEMPLATE"
        )
