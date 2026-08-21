"""
bedrock_client.py
AWS Bedrock DeepSeek V3.2 Client Integration for Aedrix Cold Outreach System (Python 3.12).

Responsibility:
- Reads configuration from environment variables:
  - LLM_PROVIDER (defaults to 'aws_bedrock')
  - LLM_MODEL (defaults to 'deepseek.v3.2')
  - AWS_REGION (defaults to 'ap-south-1')
  - AWS_BEARER_TOKEN_BEDROCK (optional bearer token / API key)
  - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
  - DRY_RUN ('true' by default)
  - SEND_EMAILS ('false' by default)
- Generates structured, zero-hallucination email drafts (Email 1, Follow-up A, Follow-up B).
- Feeds structured lead intelligence, VoC angle, and evidence levels into DeepSeek via AWS Bedrock Converse API.
- Strictly instructs DeepSeek not to fabricate any facts, metrics, or personal achievements.
- Parses and validates JSON responses cleanly.
- Seamlessly falls back to high-fidelity offline generation when DRY_RUN=true or credentials are absent.
- Preserves exact system/user prompts and structured outputs matching AEDRIX V1 requirements.
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
)


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


class BedrockClient:
    def __init__(
        self,
        region: Optional[str] = None,
        model: Optional[str] = None,
        bearer_token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        bedrock_client: Optional[Any] = None,
    ):
        load_env_file_if_present()

        self.provider = os.getenv("LLM_PROVIDER", "aws_bedrock")
        self.region = region or os.getenv("AWS_REGION", "ap-south-1")
        self.model = model or os.getenv("LLM_MODEL", "deepseek.v3.2")
        self.bearer_token = bearer_token or os.getenv("AWS_BEARER_TOKEN_BEDROCK")

        env_dry_run = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
        self.dry_run = dry_run if dry_run is not None else env_dry_run
        self.send_emails = os.getenv("SEND_EMAILS", "false").lower() in ("true", "1", "yes")

        self.client = bedrock_client
        if not self.client and not self.dry_run:
            self.client = self._init_bedrock_client()

    def _init_bedrock_client(self) -> Optional[Any]:
        """Initializes boto3 bedrock-runtime client with region and optional Bearer auth hook."""
        try:
            import boto3

            session_kwargs = {"region_name": self.region}
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session_token = os.getenv("AWS_SESSION_TOKEN")

            if aws_access_key and aws_secret_key:
                session_kwargs["aws_access_key_id"] = aws_access_key
                session_kwargs["aws_secret_access_key"] = aws_secret_key
                if aws_session_token:
                    session_kwargs["aws_session_token"] = aws_session_token

            client = boto3.client("bedrock-runtime", **session_kwargs)

            if self.bearer_token:
                token = self.bearer_token
                def add_bearer_auth(request, **kwargs):
                    request.headers["Authorization"] = f"Bearer {token}"
                client.meta.events.register("before-send.bedrock-runtime.*", add_bearer_auth)

            return client
        except Exception:
            return None

    def invoke_bedrock_converse(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 400,
        temperature: float = 0.2,
    ) -> str:
        """Invokes AWS Bedrock Converse API for DeepSeek V3.2 model."""
        if not self.client:
            raise RuntimeError("Bedrock client is not initialized.")

        try:
            response = self.client.converse(
                modelId=self.model,
                system=[{"text": system_prompt}],
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": user_prompt}]
                    }
                ],
                inferenceConfig={
                    "temperature": temperature,
                    "maxTokens": max_tokens
                }
            )
            output_message = response.get("output", {}).get("message", {})
            content_list = output_message.get("content", [])
            if content_list and "text" in content_list[0]:
                return content_list[0]["text"]
            raise ValueError("Empty or malformed content in Bedrock Converse response.")
        except Exception as primary_exc:
            # Fallback to invoke_model API if model endpoint requires raw body
            try:
                payload = json.dumps({
                    "prompt": f"System: {system_prompt}\nUser: {user_prompt}\nAssistant:",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                })
                resp = self.client.invoke_model(
                    modelId=self.model,
                    contentType="application/json",
                    accept="application/json",
                    body=payload
                )
                body_bytes = resp.get("body").read()
                data = json.loads(body_bytes.decode("utf-8"))
                if "completion" in data:
                    return data["completion"]
                elif "outputs" in data and data["outputs"]:
                    return data["outputs"][0].get("text", "")
                elif "text" in data:
                    return data["text"]
                raise primary_exc
            except Exception:
                raise primary_exc

    def generate_email_1(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext] = None,
    ) -> EmailGenerationResult:
        """Generates Email 1 using DeepSeek V3.2 via AWS Bedrock Converse API (Max 120 words)."""
        prompt = self._build_email_1_prompt(lead_intel, voc_context)

        if self.dry_run or not self.client:
            return self._generate_offline_email_1(lead_intel, voc_context)

        try:
            raw_text = self.invoke_bedrock_converse(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"],
                max_tokens=400,
                temperature=0.2,
            )
            parsed = self.parse_json_response(raw_text)
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
                generation_mode="BEDROCK_DEEPSEEK_API"
            )
        except Exception:
            # Fall back safely if API call fails
            return self._generate_offline_email_1(lead_intel, voc_context)

    def generate_followup_a(
        self,
        lead_intel: LeadIntelligenceOutput,
        email_1: EmailGenerationResult,
        voc_context: Optional[VoCContext] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up A using DeepSeek V3.2 via AWS Bedrock Converse API (Max 90 words)."""
        prompt = self._build_followup_a_prompt(lead_intel, email_1, voc_context)

        if self.dry_run or not self.client:
            return self._generate_offline_followup_a(lead_intel, email_1, voc_context)

        try:
            raw_text = self.invoke_bedrock_converse(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"],
                max_tokens=300,
                temperature=0.2,
            )
            parsed = self.parse_json_response(raw_text)
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
                generation_mode="BEDROCK_DEEPSEEK_API"
            )
        except Exception:
            return self._generate_offline_followup_a(lead_intel, email_1, voc_context)

    def generate_followup_b(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up B using DeepSeek V3.2 via AWS Bedrock Converse API (Max 90 words)."""
        prompt = self._build_followup_b_prompt(lead_intel, voc_context)

        if self.dry_run or not self.client:
            return self._generate_offline_followup_b(lead_intel, voc_context)

        try:
            raw_text = self.invoke_bedrock_converse(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"],
                max_tokens=300,
                temperature=0.2,
            )
            parsed = self.parse_json_response(raw_text)
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
                generation_mode="BEDROCK_DEEPSEEK_API"
            )
        except Exception:
            return self._generate_offline_followup_b(lead_intel, voc_context)

    def parse_json_response(self, raw_text: str) -> Dict[str, str]:
        """Parses JSON from DeepSeek response, safely handling markdown wrappers."""
        text = raw_text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        else:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1].strip()

        subject = ""
        body = ""
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                subject = str(data.get("subject", "")).strip()
                body = str(data.get("body", "")).strip()
        except json.JSONDecodeError:
            subject = "Aedrix Construction Platform Overview"
            body = raw_text.strip()

        # Post-processing Sanitizer: Clean any accidental internal system codes/placeholders
        forbidden_terms = [
            "NO_STRONG_SIGNAL",
            "SIGNAL_VERIFIED",
            "HARD_DISQUALIFIED",
            "CAMPAIGN_EXCLUDED",
            "INVALID_BOUNCED",
        ]
        for term in forbidden_terms:
            body = re.sub(rf"\b{term}\b", "", body, flags=re.IGNORECASE)
            subject = re.sub(rf"\b{term}\b", "", subject, flags=re.IGNORECASE)

        # Normalize whitespace after removal
        body = re.sub(r" +", " ", body).strip()
        subject = re.sub(r" +", " ", subject).strip()

        return {"subject": subject, "body": body}

    def _build_email_1_prompt(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext],
    ) -> Dict[str, str]:
        """Constructs Zero-Hallucination Email 1 prompt for DeepSeek V3.2."""
        system_prompt = (
            "You are a senior B2B cold outreach copywriter representing Aedrix (https://aedrix.com) — "
            "a cloud-based construction management SaaS platform for UK main contractors covering "
            "pre-construction document control, drawing versioning, site manpower tracking, and commercial control.\n\n"
            "STRICT ZERO-HALLUCINATION & COPY CLEANLINESS RULES:\n"
            "1. Use ONLY the verified facts, signals, and personalization notes provided in the input JSON.\n"
            "2. NEVER invent company facts, achievements, projects, promotions, technologies, financial metrics, customer names, or dates.\n"
            "3. If a fact is not present in the supplied evidence, do NOT state it as fact.\n"
            "4. NEVER output internal system codes, status enum names, or pipeline labels (such as NO_STRONG_SIGNAL, SIGNAL_VERIFIED, QUALIFIED, DISQUALIFIED, P1, P2, score values, or metadata keys) anywhere in the email body or subject.\n"
            "5. If research signal or personalization note is null or empty, write a clean, natural, professional baseline cold outreach email focusing on the contact's role, company, and industry challenges.\n"
            "6. Word count MUST NOT exceed 120 words.\n"
            "7. Tone must be concise, professional, human, construction-industry aware, not generic AI spam.\n"
            "8. End with a low-friction 2-minute overview CTA.\n"
            "9. Return ONLY a valid JSON object with 'subject' and 'body' keys."
        )

        raw_signal = lead_intel.relevant_signal or ""
        clean_signal = "" if raw_signal == "NO_STRONG_SIGNAL" else raw_signal

        raw_note = lead_intel.personalization_note or ""
        clean_note = "" if raw_note == "NO_STRONG_SIGNAL" else raw_note

        user_context = {
            "company": lead_intel.company_name,
            "contact": lead_intel.contact_name,
            "job_title": lead_intel.job_title,
            "has_verified_signal": bool(clean_signal),
            "verified_research_signals": clean_signal if clean_signal else None,
            "personalization_note": clean_note if clean_note else None,
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
        """Constructs Zero-Hallucination Follow-up A prompt for DeepSeek V3.2."""
        system_prompt = (
            "You are a senior B2B cold outreach copywriter representing Aedrix. "
            "Write Follow-up A (opened Email 1 but did not reply). Max 90 words. "
            "Never invent facts. Never output internal system codes or status labels (such as NO_STRONG_SIGNAL, SIGNAL_VERIFIED, QUALIFIED, P1, P2). "
            "Return ONLY valid JSON with 'subject' and 'body'."
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
        """Constructs Zero-Hallucination Follow-up B prompt for DeepSeek V3.2."""
        system_prompt = (
            "You are a senior B2B cold outreach copywriter representing Aedrix. "
            "Write Follow-up B (unopened Email 1, pivoted angle to manpower & financial tracking). Max 90 words. "
            "Never invent facts. Never output internal system codes or status labels (such as NO_STRONG_SIGNAL, SIGNAL_VERIFIED, QUALIFIED, P1, P2). "
            "Return ONLY valid JSON with 'subject' and 'body'."
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

        if is_signal_verified and lead_intel.personalization_note and lead_intel.personalization_note != "NO_STRONG_SIGNAL":
            personalization_text = lead_intel.personalization_note
            evidence_used = [lead_intel.relevant_signal or "Verified corporate signal"]
        else:
            personalization_text = (
                "Given your role leading operations across UK building projects, I thought you'd be "
                "interested in how Aedrix unifies pre-construction document control directly with real-time site manpower tracking."
            )
            evidence_used = ["Baseline Aedrix Value Proposition"]

        subject = "Pre-construction document control"
        unsubscribe_url = f"https://aedrix.com/unsubscribe?email={lead_intel.email}"
        body = (
            f"Hi {contact_first_name},\n\n"
            f"{personalization_text}\n\n"
            f"Managing subcontractor document versions across regional sites can create administrative latency. "
            f"Aedrix unifies pre-construction document control directly with real-time site manpower tracking "
            f"so your operational teams operate from a single source of truth.\n\n"
            f"Are you open to a brief 2-minute overview this week?\n\nBest regards,\n\n"
            f"Alex Mitchell\n"
            f"Outreach Manager, Aedrix\n"
            f"To unsubscribe, click here: {unsubscribe_url}"
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
        unsubscribe_url = f"https://aedrix.com/unsubscribe?email={lead_intel.email}"
        body = (
            f"Hi {contact_first_name},\n\n"
            f"Following up on my previous note regarding pre-construction document control for {company}.\n\n"
            f"Given {company}'s focus on operational delivery across sites, I wanted to highlight how Aedrix specifically reduces document versioning errors across multi-site main contractor teams.\n\n"
            f"Would Thursday afternoon work for a quick conversation?\n\nBest regards,\n\n"
            f"Alex Mitchell\n"
            f"Outreach Manager, Aedrix\n"
            f"To unsubscribe, click here: {unsubscribe_url}"
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

        subject = "Real-time manpower and financial tracking"
        unsubscribe_url = f"https://aedrix.com/unsubscribe?email={lead_intel.email}"
        body = (
            f"Hi {contact_first_name},\n\n"
            f"Pivoting from my earlier message. Beyond document control, many established main contractors like {company} face challenges reconciling pre-construction estimates against live site manpower and financial expenditure.\n\n"
            f"Aedrix provides a modular cloud platform that gives leadership real-time labor productivity visibility without requiring a complex IT overhaul.\n\n"
            f"Would you be open to exploring how this fits your digital roadmap?\n\nBest regards,\n\n"
            f"Alex Mitchell\n"
            f"Outreach Manager, Aedrix\n"
            f"To unsubscribe, click here: {unsubscribe_url}"
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
