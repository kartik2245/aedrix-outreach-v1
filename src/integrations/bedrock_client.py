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
                    if v:
                        if override or k not in os.environ:
                            os.environ[k] = v
                    else:
                        if k in os.environ and not os.environ[k].strip():
                            os.environ.pop(k, None)


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
        raw_bearer = bearer_token or os.getenv("AWS_BEARER_TOKEN_BEDROCK")
        self.bearer_token = raw_bearer.strip() if raw_bearer and raw_bearer.strip() else None

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

            if "AWS_BEARER_TOKEN_BEDROCK" in os.environ and not os.environ["AWS_BEARER_TOKEN_BEDROCK"].strip():
                os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)

            session_kwargs = {"region_name": self.region}
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session_token = os.getenv("AWS_SESSION_TOKEN")

            if aws_access_key and aws_secret_key:
                session_kwargs["aws_access_key_id"] = aws_access_key
                session_kwargs["aws_secret_access_key"] = aws_secret_key
                if aws_session_token:
                    session_kwargs["aws_session_token"] = aws_session_token
            else:
                # Resolve credentials from boto3 Session (shared credentials file / profile / IAM)
                boto_session = boto3.Session(region_name=self.region)
                creds = boto_session.get_credentials()
                if creds:
                    frozen = creds.get_frozen_credentials()
                    if frozen and frozen.access_key and frozen.secret_key:
                        session_kwargs["aws_access_key_id"] = frozen.access_key
                        session_kwargs["aws_secret_access_key"] = frozen.secret_key
                        if frozen.token:
                            session_kwargs["aws_session_token"] = frozen.token

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
        icp_config: Optional[Any] = None,
    ) -> EmailGenerationResult:
        """Generates Email 1 using DeepSeek V3.2 via AWS Bedrock Converse API (Max 120 words)."""
        prompt = self._build_email_1_prompt(lead_intel, voc_context, icp_config=icp_config)

        if self.dry_run or not self.client:
            return self._generate_offline_email_1(lead_intel, voc_context, icp_config=icp_config)

        try:
            raw_text = self.invoke_bedrock_converse(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"],
                max_tokens=400,
                temperature=0.2,
            )
            parsed = self.parse_json_response(raw_text)
            body = parsed.get("body", "").strip()
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
                generation_mode="BEDROCK_DEEPSEEK_API"
            )
        except Exception:
            # Fall back safely if API call fails
            return self._generate_offline_email_1(lead_intel, voc_context, icp_config=icp_config)

    def generate_followup_a(
        self,
        lead_intel: LeadIntelligenceOutput,
        email_1: EmailGenerationResult,
        voc_context: Optional[VoCContext] = None,
        icp_config: Optional[Any] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up A using DeepSeek V3.2 via AWS Bedrock Converse API (Max 90 words)."""
        prompt = self._build_followup_a_prompt(lead_intel, email_1, voc_context, icp_config=icp_config)

        if self.dry_run or not self.client:
            return self._generate_offline_followup_a(lead_intel, email_1, voc_context, icp_config=icp_config)

        try:
            raw_text = self.invoke_bedrock_converse(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"],
                max_tokens=300,
                temperature=0.2,
            )
            parsed = self.parse_json_response(raw_text)
            body = parsed.get("body", "").strip()
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
                generation_mode="BEDROCK_DEEPSEEK_API"
            )
        except Exception:
            return self._generate_offline_followup_a(lead_intel, email_1, voc_context, icp_config=icp_config)

    def generate_followup_b(
        self,
        lead_intel: LeadIntelligenceOutput,
        voc_context: Optional[VoCContext] = None,
        icp_config: Optional[Any] = None,
    ) -> EmailGenerationResult:
        """Generates Follow-up B using DeepSeek V3.2 via AWS Bedrock Converse API (Max 90 words)."""
        prompt = self._build_followup_b_prompt(lead_intel, voc_context, icp_config=icp_config)

        if self.dry_run or not self.client:
            return self._generate_offline_followup_b(lead_intel, voc_context, icp_config=icp_config)

        try:
            raw_text = self.invoke_bedrock_converse(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"],
                max_tokens=300,
                temperature=0.2,
            )
            parsed = self.parse_json_response(raw_text)
            body = parsed.get("body", "").strip()
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
                evidence_used=["Pivoted Angle: Real-Time Manpower & Financial Control"],
                generation_mode="BEDROCK_DEEPSEEK_API"
            )
        except Exception:
            return self._generate_offline_followup_b(lead_intel, voc_context, icp_config=icp_config)

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
        icp_config: Optional[Any] = None,
    ) -> Dict[str, str]:
        """Constructs Zero-Hallucination Email 1 prompt for DeepSeek V3.2."""
        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        prod = getattr(voc_context, "product_or_service", None) or getattr(icp_config, "product_or_service", None) or getattr(voc_context, "aedrix_value_prop", None) or f"software and services for {lead_intel.industry} organizations"
        cta_text = getattr(voc_context, "cta", None) or getattr(icp_config, "cta", None) or "Are you open to a brief 2-minute overview this week?"

        system_prompt = (
            f"You are a senior B2B cold outreach copywriter representing {brand} — {prod}.\n\n"
            "STRICT ZERO-HALLUCINATION & COPY CLEANLINESS RULES:\n"
            "1. Use ONLY the verified facts, signals, and personalization notes provided in the input JSON.\n"
            "2. NEVER invent company facts, achievements, projects, promotions, technologies, financial metrics, customer names, or dates.\n"
            "3. If a fact is not present in the supplied evidence, do NOT state it as fact.\n"
            "4. NEVER output internal system codes, status enum names, or pipeline labels (such as NO_STRONG_SIGNAL, SIGNAL_VERIFIED, QUALIFIED, DISQUALIFIED, P1, P2, score values, or metadata keys) anywhere in the email body or subject.\n"
            "5. If research signal or personalization note is null or empty, write a clean, natural, professional baseline cold outreach email focusing on the contact's role, company, and industry challenges.\n"
            "6. Word count MUST NOT exceed 120 words.\n"
            f"7. Tone must be concise, professional, human, relevant to {lead_intel.industry}, not generic AI spam.\n"
            f"8. End with a low-friction CTA: '{cta_text}'.\n"
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
        """Constructs Zero-Hallucination Follow-up A prompt for DeepSeek V3.2."""
        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        voc_angle = voc_context.voc_angle if voc_context else f"{lead_intel.industry} Operations"
        system_prompt = (
            f"You are a senior B2B cold outreach copywriter representing {brand}. "
            "Write Follow-up A (opened Email 1 but did not reply). Max 90 words. "
            "Never invent facts. Never output internal system codes or status labels. "
            "Return ONLY valid JSON with 'subject' and 'body'."
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
        """Constructs Zero-Hallucination Follow-up B prompt for DeepSeek V3.2."""
        brand = getattr(voc_context, "company_name", None) or getattr(icp_config, "company_name", None) or "Aedrix"
        voc_angle = voc_context.voc_angle if voc_context else f"{lead_intel.industry} Operations"
        system_prompt = (
            f"You are a senior B2B cold outreach copywriter representing {brand}. "
            f"Write Follow-up B (unopened Email 1, pivoted angle to {voc_angle}). Max 90 words. "
            "Never invent facts. Never output internal system codes or status labels. "
            "Return ONLY valid JSON with 'subject' and 'body'."
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

        if is_signal_verified and lead_intel.personalization_note and lead_intel.personalization_note != "NO_STRONG_SIGNAL":
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
        unsubscribe_url = f"https://aedrix.com/unsubscribe?email={lead_intel.email}"
        body = (
            f"Hi {contact_first_name},\n\n"
            f"{personalization_text}\n\n"
            f"{val_prop}\n\n"
            f"{cta_text}\n\nBest regards,\n\n"
            f"{sender}\n"
            f"Outreach Manager, {brand}\n"
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
        unsubscribe_url = f"https://aedrix.com/unsubscribe?email={lead_intel.email}"
        body = (
            f"Hi {contact_first_name},\n\n"
            f"Following up on my previous note regarding operations for {company}.\n\n"
            f"Given {company}'s focus on operational delivery, I wanted to highlight how {brand} specifically helps teams in {lead_intel.industry}.\n\n"
            f"Would Thursday afternoon work for a quick conversation?\n\nBest regards,\n\n"
            f"{sender}\n"
            f"Outreach Manager, {brand}\n"
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
        unsubscribe_url = f"https://aedrix.com/unsubscribe?email={lead_intel.email}"
        body = (
            f"Hi {contact_first_name},\n\n"
            f"Pivoting from my earlier message: {val_prop}\n\n"
            f"Would you be open to exploring how this fits your operational roadmap?\n\nBest regards,\n\n"
            f"{sender}\n"
            f"Outreach Manager, {brand}\n"
            f"To unsubscribe, click here: {unsubscribe_url}"
        )
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
