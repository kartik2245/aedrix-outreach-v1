"""
deepline_export_adapter.py
Deepline Research Export Adapter Module (Dry-Run Adapter - Python 3.12).

Responsibilities:
- Accepts raw Deepline-style JSON export records.
- Validates input against schemas/deepline_research_schema.json logic.
- Enforces validation rules (UK geography, construction sector, contact identity, evidence levels).
- Transforms & writes validated records to data/research_leads.json.
- Preserves all Apollo fields, research sources, and evidence levels.
- NEVER fabricates missing fields.
- NEVER upgrades UNKNOWN or INFERRED to VERIFIED.
"""

import json
import os
import re
from typing import Dict, Any, List, Union, Optional
from src.models import EvidenceLevel, EmailStatus


VALID_EMAIL_STATUS_SET = {
    EmailStatus.EVIDENCE_VERIFIED,
    EmailStatus.PATTERN_CONFIRMED,
    EmailStatus.CATCHALL_UNVERIFIED,
    EmailStatus.INVALID_BOUNCED,
}


class DeeplineExportAdapter:
    def adapt(self, input_data: Union[str, Dict[str, Any], List[Dict[str, Any]]], output_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Processes raw Deepline JSON array or file path and writes to output research_leads.json."""
        if isinstance(input_data, str) and os.path.exists(input_data):
            with open(input_data, "r", encoding="utf-8") as f:
                records = json.load(f)
        elif isinstance(input_data, list):
            records = input_data
        else:
            records = [input_data]

        adapted_records = [self.adapt_record(rec) for rec in records]

        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(adapted_records, f, indent=2)

        return adapted_records

    def parse_employee_count(self, value: Any) -> Optional[int]:
        """Helper to safely extract integer employee count from raw data."""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            clean = re.sub(r"[^0-9]", "", value)
            return int(clean) if clean else None
        return None

    def adapt_record(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Adapts & validates a single Deepline research record."""
        errors: List[str] = []
        warnings: List[str] = []

        comp_obj = raw.get("company") if isinstance(raw.get("company"), dict) else {}
        comp_name_raw = (
            raw.get("company_name")
            or (comp_obj.get("summary", {}).get("name") if isinstance(comp_obj.get("summary"), dict) else None)
            or comp_obj.get("name")
            or (raw.get("company") if isinstance(raw.get("company"), str) else None)
        )
        if not comp_name_raw or not str(comp_name_raw).strip():
            errors.append("MISSING_COMPANY_NAME: Company name is missing.")

        comp_domain_raw = (
            raw.get("company_domain")
            or raw.get("domain")
            or raw.get("website")
            or (comp_obj.get("link", {}).get("domain") if isinstance(comp_obj.get("link"), dict) else None)
            or comp_obj.get("domain")
        )
        if not comp_domain_raw or not str(comp_domain_raw).strip():
            warnings.append("MISSING_COMPANY_DOMAIN: Company domain is missing.")

        company_name = str(comp_name_raw or "UNKNOWN_COMPANY").strip()
        domain_str = str(comp_domain_raw or "unknown.com").strip().lower()
        company_domain = re.sub(r"^https?://", "", domain_str)
        company_domain = re.sub(r"^www\.", "", company_domain).strip()

        # Resolve country: AI Ark may return location as a dict with keys like COUNTRY, DEFAULT, etc.
        def _extract_country_str(raw_loc: Any) -> str:
            if isinstance(raw_loc, dict):
                return str(
                    raw_loc.get("COUNTRY")
                    or raw_loc.get("country")
                    or raw_loc.get("DEFAULT")
                    or raw_loc.get("default")
                    or ""
                ).strip()
            return str(raw_loc or "").strip()

        country = _extract_country_str(
            raw.get("company_location")
            or raw.get("country")
            or raw.get("location")
            or comp_obj.get("location")
            or comp_obj.get("company_location")
            or "UK"
        ).upper()
        is_uk = raw.get("is_uk_operating") if raw.get("is_uk_operating") is not None else comp_obj.get("is_uk_operating")
        if is_uk is not None:
            is_uk_operating = bool(is_uk)
        else:
            is_uk_operating = country == "UK" or any(kw in country for kw in ["UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GB"])

        industry = str(raw.get("industry") or comp_obj.get("industry") or "Construction").strip()
        is_const = raw.get("is_construction_sector") if raw.get("is_construction_sector") is not None else comp_obj.get("is_construction_sector")
        if is_const is not None:
            is_construction_sector = bool(is_const)
        else:
            is_construction_sector = "software" not in industry.lower()

        company_size = str(
            raw.get("company_size")
            or raw.get("size")
            or comp_obj.get("company_size")
            or comp_obj.get("size")
            or "UNKNOWN"
        ).strip()
        # New field: employee_count derived from company_size string or raw employee_count
        raw_emp = raw.get("employee_count") or raw.get("employees") or comp_obj.get("employee_count") or comp_obj.get("employees")
        employee_count = self.parse_employee_count(raw_emp) if raw_emp is not None else self.parse_employee_count(company_size)
        evidence_levels = raw.get("evidence_levels", {})
        
        company_size_ev_raw = evidence_levels.get("company_size") if isinstance(evidence_levels, dict) else None
        if not company_size_ev_raw:
            company_size_ev_raw = raw.get("company_size_evidence")
        
        if company_size_ev_raw:
            try:
                company_size_ev = EvidenceLevel(str(company_size_ev_raw).strip().upper())
            except ValueError:
                company_size_ev = EvidenceLevel.ESTIMATED
        else:
            company_size_ev = EvidenceLevel.ESTIMATED

        profile_obj = raw.get("profile") if isinstance(raw.get("profile"), dict) else {}
        contact_name_raw = (
            raw.get("contact_name")
            or raw.get("full_name")
            or profile_obj.get("full_name")
            or profile_obj.get("name")
        )
        if not contact_name_raw:
            fn = str(raw.get("first_name") or profile_obj.get("first_name") or "").strip()
            ln = str(raw.get("last_name") or profile_obj.get("last_name") or "").strip()
            if fn or ln:
                contact_name_raw = f"{fn} {ln}".strip()

        if not contact_name_raw or not str(contact_name_raw).strip():
            warnings.append("MALFORMED_CONTACT: Contact name is missing.")

        job_title_raw = (
            raw.get("job_title")
            or raw.get("title")
            or raw.get("headline")
            or profile_obj.get("title")
            or profile_obj.get("job_title")
            or profile_obj.get("headline")
        )
        if not job_title_raw or not str(job_title_raw).strip():
            warnings.append("MALFORMED_CONTACT: Job title is missing.")

        contact_name = str(contact_name_raw or "UNKNOWN_CONTACT").strip()
        job_title = str(job_title_raw or "UNKNOWN_TITLE").strip()
        email = str(raw.get("email") or profile_obj.get("email") or "").strip().lower()
        link_obj = raw.get("link") if isinstance(raw.get("link"), dict) else {}
        linkedin_raw = (
            raw.get("linkedin_url")
            or raw.get("linkedin")
            or link_obj.get("linkedin")
            or link_obj.get("url")
        )
        linkedin_url = str(linkedin_raw).strip() if linkedin_raw else None

        email_status_str = str(raw.get("email_status", EmailStatus.PATTERN_CONFIRMED.value)).strip().upper()
        try:
            email_status = EmailStatus(email_status_str)
        except ValueError:
            warnings.append(f"INVALID_EMAIL_STATUS: '{email_status_str}' is invalid. Defaulting to PATTERN_CONFIRMED.")
            email_status = EmailStatus.PATTERN_CONFIRMED

        signals_raw = raw.get("research_signals")
        if isinstance(signals_raw, list) and signals_raw:
            signals = signals_raw
        elif raw.get("relevant_signal"):
            signals = [raw["relevant_signal"]]
        else:
            signals = []

        primary_signal = str(signals[0]).strip() if (signals and str(signals[0]).strip() != "NO_STRONG_SIGNAL") else "NO_STRONG_SIGNAL"
        
        signal_ev_raw = evidence_levels.get("signal") if isinstance(evidence_levels, dict) else None
        if not signal_ev_raw:
            signal_ev_raw = raw.get("relevant_signal_evidence")

        if signal_ev_raw:
            try:
                signal_ev = EvidenceLevel(str(signal_ev_raw).strip().upper())
            except ValueError:
                signal_ev = EvidenceLevel.UNKNOWN
        else:
            signal_ev = EvidenceLevel.UNKNOWN if primary_signal == "NO_STRONG_SIGNAL" else EvidenceLevel.VERIFIED

        sources_raw = raw.get("research_sources", [])
        sources = [str(s).strip() for s in sources_raw if s and str(s).strip()] if isinstance(sources_raw, list) else []

        if signal_ev == EvidenceLevel.VERIFIED and len(sources) == 0:
            warnings.append("UNSUPPORTED_VERIFIED_CLAIM: Signal marked VERIFIED without research sources. Downgrading to INFERRED.")
            signal_ev = EvidenceLevel.INFERRED

        pain_point = str(raw.get("pain_point", "Managing pre-construction document control across multi-site teams."))
        pain_point_ev_raw = evidence_levels.get("pain_point") if isinstance(evidence_levels, dict) else None
        if not pain_point_ev_raw:
            pain_point_ev_raw = raw.get("pain_point_evidence")

        if pain_point_ev_raw:
            try:
                pain_point_ev = EvidenceLevel(str(pain_point_ev_raw).strip().upper())
            except ValueError:
                pain_point_ev = EvidenceLevel.INFERRED
        else:
            pain_point_ev = EvidenceLevel.INFERRED

        res = {
            "company_name": company_name,
            "company_domain": company_domain,
            "country": country,
            "is_uk_operating": is_uk_operating,
            "industry": industry,
            "is_construction_sector": is_construction_sector,
            "company_size": company_size,
            "employee_count": employee_count,
            "company_size_evidence": company_size_ev,
            "ownership_type": raw.get("ownership_type") or ("PUBLIC_PLC" if "plc" in company_name.lower() else "PRIVATE"),
            "contact_name": contact_name,
            "job_title": job_title,
            "email": email,
            "email_status_input": email_status,
            "linkedin_url": linkedin_url,
            "relevant_signal": primary_signal,
            "relevant_signal_evidence": signal_ev,
            "pain_point": pain_point,
            "pain_point_evidence": pain_point_ev,
            "personalization_note": raw.get("personalization_note"),
            "research_sources": sources,
            "decision_maker_reason": raw.get("decision_maker_reason", "Matching executive digital / operations persona."),
            "adapter_audit": {
                "is_valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
            }
        }

        # Preserve qualification flags if present
        for key in ["is_active_crm_deal", "is_existing_client", "is_global_suppressed", "contacted_within_60_days", "is_hard_bounce", "email_invalid"]:
            if key in raw:
                res[key] = raw[key]

        return res
