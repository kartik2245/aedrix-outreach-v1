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


def load_env_file_if_present(env_path: Optional[str] = None, override: bool = True) -> None:
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
    ) -> EmailGenerationResult:
        """Generates Email 1 (Max 120 words)."""
        prompt = self._build_email_1_prompt(lead_intel, voc_context)

        if self.dry_run or not self.client:
            return self._generate_offline_email_1(lead_intel, voc_context)

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
            body = parsed.get("body", "").strip()
            subject = parsed.get("subject", f"Pre-construction document control at {lead_intel.company_name}").strip()
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
            # Fallback gracefully if API call fails
            return self._generate_offline_email_1(lead_intel, voc_context)

    def generate_followup_a(
        self,
        lead_intel: LeadIntelligenceOutput,
        email_1: EmailGenerationResult,
        voc_context: Optional[VoCContext] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up A (Opened Email 1, No Reply - Max 90 words)."""
        prompt = self._build_followup_a_prompt(lead_intel, email_1, voc_context)

        if self.dry_run or not self.client:
            return self._generate_offline_followup_a(lead_intel, email_1, voc_context)

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
            body = parsed.get("body", "").strip()
            subject = parsed.get("subject", f"Re: {email_1.subject}").strip()
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
            return self._generate_offline_followup_a(lead_intel, email_1, voc_context)

    def generate_followup_b(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up B (Unopened Email 1, Pivoted Angle - Max 90 words)."""
        prompt = self._build_followup_b_prompt(lead_intel, voc_context)

        if self.dry_run or not self.client:
            return self._generate_offline_followup_b(lead_intel, voc_context)

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
            body = parsed.get("body", "").strip()
            subject = parsed.get("subject", f"Real-time manpower & financial tracking for {lead_intel.company_name}").strip()
            word_count = len(body.split())

            return EmailGenerationResult(
                email_type="FOLLOWUP_B",
                subject=subject,
                body=body,
                word_count=word_count,
                personalization_status=lead_intel.personalization_note_status,
                evidence_used=["Pivoted Angle: Real-Time Manpower & Financial Control"],
                generation_mode="CLAUDE_API"
            )
        except Exception:
            return self._generate_offline_followup_b(lead_intel, voc_context)

    def parse_claude_json_response(self, raw_text: str) -> Dict[str, str]:
        """Parses JSON from Claude response, safely handling markdown wrappers."""
        text = raw_text.strip()
        # Strip ```json ... ``` code fences
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        else:
            # Look for outermost curly braces
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

        # Fallback if invalid JSON returned
        return {"subject": "Aedrix Construction Platform Overview", "body": raw_text.strip()}

    def _build_email_1_prompt(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext],
    ) -> Dict[str, str]:
        """Constructs Zero-Hallucination Email 1 prompt."""
        system_prompt = (
            "You are a senior B2B cold outreach copywriter representing Aedrix (https://aedrix.com) — "
            "a cloud-based construction management SaaS platform for UK main contractors covering "
            "pre-construction document control, drawing versioning, site manpower tracking, and commercial control.\n\n"
            "STRICT ZERO-HALLUCINATION RULES:\n"
            "1. Use ONLY the verified facts, signals, and personalization notes provided in the input JSON.\n"
            "2. NEVER invent company facts, achievements, projects, promotions, technologies, financial metrics, customer names, or dates.\n"
            "3. If a fact is not present in the supplied evidence, do NOT state it as fact.\n"
            "4. Word count MUST NOT exceed 120 words.\n"
            "5. Tone must be concise, professional, human, construction-industry aware, not generic AI spam.\n"
            "6. End with a low-friction 2-minute overview CTA.\n"
            "7. Return ONLY a valid JSON object with 'subject' and 'body' keys."
        )

        user_context = {
            "company": lead_intel.company_name,
            "contact": lead_intel.contact_name,
            "job_title": lead_intel.job_title,
            "opportunity_score": lead_intel.opportunity_score,
            "accessibility_score": lead_intel.accessibility_score,
            "outreach_priority_index": lead_intel.outreach_priority_index,
            "priority": lead_intel.priority_level.value,
            "verified_research_signals": lead_intel.relevant_signal,
            "evidence_levels": {
                "signal": lead_intel.relevant_signal_evidence.value,
                "company_size": lead_intel.company_size_evidence.value,
                "pain_point": lead_intel.pain_point_evidence.value
            },
            "personalization_note_status": lead_intel.personalization_note_status.value,
            "personalization_note": lead_intel.personalization_note,
            "voc_angle": voc_context.voc_angle if voc_context else "Pre-construction document control",
            "aedrix_value_prop": voc_context.aedrix_value_prop if voc_context else "Unifying pre-construction document control with real-time site manpower tracking."
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
    ) -> Dict[str, str]:
        """Constructs Zero-Hallucination Follow-up A prompt."""
        system_prompt = (
            "You are a senior B2B cold outreach copywriter representing Aedrix. "
            "Write Follow-up A (opened Email 1 but did not reply). Max 90 words. "
            "Never invent facts. Return ONLY valid JSON with 'subject' and 'body'."
        )
        user_prompt = (
            f"Company: {lead_intel.company_name}\n"
            f"Contact: {lead_intel.contact_name}\n"
            f"Previous Email 1 Subject: {email_1.subject}\n"
            f"VoC Angle: {voc_context.voc_angle if voc_context else 'Pre-construction document control'}\n"
            f"Generate Follow-up A under 90 words in JSON format: {{\"subject\": \"...\", \"body\": \"...\"}}"
        )
        return {"system": system_prompt, "user": user_prompt}

    def _build_followup_b_prompt(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext],
    ) -> Dict[str, str]:
        """Constructs Zero-Hallucination Follow-up B prompt."""
        system_prompt = (
            "You are a senior B2B cold outreach copywriter representing Aedrix. "
            "Write Follow-up B (unopened Email 1, pivoted angle to manpower & financial tracking). Max 90 words. "
            "Never invent facts. Return ONLY valid JSON with 'subject' and 'body'."
        )
        user_prompt = (
            f"Company: {lead_intel.company_name}\n"
            f"Contact: {lead_intel.contact_name}\n"
            f"Pivoted Angle: Real-Time Manpower & Financial Tracking\n"
            f"Generate Follow-up B under 90 words in JSON format: {{\"subject\": \"...\", \"body\": \"...\"}}"
        )
        return {"system": system_prompt, "user": user_prompt}

    def _generate_offline_email_1(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext],
    ) -> EmailGenerationResult:
        """High-fidelity deterministic offline template generator."""
        contact_first_name = (lead_intel.contact_name or "there").split(" ")[0]
        company = lead_intel.company_name
        is_signal_verified = lead_intel.personalization_note_status == PersonalizationNoteStatus.SIGNAL_VERIFIED

        if is_signal_verified and lead_intel.personalization_note:
            personalization_text = lead_intel.personalization_note
            evidence_used = [lead_intel.relevant_signal or "Verified corporate signal"]
        else:
            personalization_text = (
                "Given your role leading operations across UK building projects, I thought you'd be "
                "interested in how Aedrix unifies pre-construction document control directly with real-time site manpower tracking."
            )
            evidence_used = ["Baseline Aedrix Value Proposition (NO_STRONG_SIGNAL)"]

        subject = f"Pre-construction document control at {company}"
        body = (
            f"Hi {contact_first_name},\n\n"
            f"{personalization_text}\n\n"
            f"Managing subcontractor document versions across regional sites can create administrative latency. "
            f"Aedrix unifies pre-construction document control directly with real-time site manpower tracking "
            f"so your operational teams operate from a single source of truth.\n\n"
            f"Are you open to a brief 2-minute overview this week?\n\nBest regards,\nAedrix Team"
        )
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
    ) -> EmailGenerationResult:
        """Offline Follow-up A template."""
        contact_first_name = (lead_intel.contact_name or "there").split(" ")[0]
        company = lead_intel.company_name

        subject = f"Re: {email_1.subject}"
        body = (
            f"Hi {contact_first_name},\n\n"
            f"Following up on my previous note regarding pre-construction document control for {company}.\n\n"
            f"Given {company}'s focus on operational delivery across sites, I wanted to highlight how Aedrix specifically reduces document versioning errors across multi-site main contractor teams.\n\n"
            f"Would Thursday afternoon work for a quick conversation?\n\nBest regards,\nAedrix Team"
        )
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
    ) -> EmailGenerationResult:
        """Offline Follow-up B template."""
        contact_first_name = (lead_intel.contact_name or "there").split(" ")[0]
        company = lead_intel.company_name

        subject = f"Real-time manpower & financial tracking for {company}"
        body = (
            f"Hi {contact_first_name},\n\n"
            f"Pivoting from my earlier message—beyond document control, many established main contractors like {company} face challenges reconciling pre-construction estimates against live jobsite manpower and financial expenditure.\n\n"
            f"Aedrix provides a modular cloud platform that gives leadership real-time labor productivity visibility without requiring a complex IT overhaul.\n\n"
            f"Would you be open to exploring how this fits your digital roadmap?\n\nBest regards,\nAedrix Team"
        )
        word_count = len(body.split())

        return EmailGenerationResult(
            email_type="FOLLOWUP_B",
            subject=subject,
            body=body,
            word_count=word_count,
            personalization_status=lead_intel.personalization_note_status,
            evidence_used=["Pivoted Angle: Real-Time Manpower & Financial Control"],
            generation_mode="DRY_RUN_TEMPLATE"
        )
