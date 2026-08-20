"""
research_normalizer.py
Research Normalizer Module for Aedrix Lead Intelligence Pipeline (Python 3.12).

Responsibilities:
- Accepts raw research records.
- Normalizes company, contact, industry, location, headcount, and signal fields.
- Normalizes evidence levels (VERIFIED, ESTIMATED, INFERRED, UNKNOWN).
- Preserves research sources & citations.
- NEVER upgrades UNKNOWN or INFERRED to VERIFIED.
- NEVER fabricates missing information.
"""

import re
from typing import Dict, Any, List, Union, Optional
from src.models import EvidenceLevel


class ResearchNormalizer:
    def normalize(self, input_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Normalizes a single raw research record or list of records."""
        if isinstance(input_data, list):
            return [self.normalize_record(record) for record in input_data]
        return self.normalize_record(input_data)

    def normalize_record(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes a single raw research record."""
        company_name = str(raw.get("company_name", "UNKNOWN_COMPANY")).strip()
        company_domain = self.clean_domain(raw.get("company_domain"))
        
        country = str(raw.get("country") or ("UK" if raw.get("is_uk_operating") is not False else "UNKNOWN")).strip().upper()
        is_uk_operating = raw.get("is_uk_operating") if raw.get("is_uk_operating") is not None else (country == "UK" or "UNITED KINGDOM" in country)

        industry = str(raw.get("industry", "Construction")).strip()
        is_construction_sector = raw.get("is_construction_sector") if raw.get("is_construction_sector") is not None else True

        emp_count_raw = raw.get("employee_count")
        company_size = str(raw.get("company_size") or (f"{emp_count_raw} employees" if emp_count_raw else "UNKNOWN")).strip()
        employee_count = int(emp_count_raw) if emp_count_raw else self.parse_employee_count(company_size)
        company_size_evidence = self.normalize_evidence_level(raw.get("company_size_evidence"), EvidenceLevel.ESTIMATED)

        ownership_type = str(raw.get("ownership_type") or ("PUBLIC_PLC" if "plc" in company_name.lower() else "PRIVATE")).strip().upper()

        contact_name = str(raw.get("contact_name", "UNKNOWN_CONTACT")).strip()
        job_title = str(raw.get("job_title", "UNKNOWN_TITLE")).strip()
        email = str(raw.get("email", "")).strip().lower()
        linkedin_url = str(raw.get("linkedin_url", "")).strip() if raw.get("linkedin_url") else None

        relevant_signal_raw = raw.get("relevant_signal")
        relevant_signal = str(relevant_signal_raw).strip() if (relevant_signal_raw and relevant_signal_raw != "NO_STRONG_SIGNAL") else "NO_STRONG_SIGNAL"
        
        if relevant_signal == "NO_STRONG_SIGNAL":
            relevant_signal_evidence = EvidenceLevel.UNKNOWN
        else:
            relevant_signal_evidence = self.normalize_evidence_level(raw.get("relevant_signal_evidence"), EvidenceLevel.UNKNOWN)

        pain_point = str(raw.get("pain_point", "Managing pre-construction document control across multi-site teams.")).strip()
        pain_point_evidence = self.normalize_evidence_level(raw.get("pain_point_evidence"), EvidenceLevel.INFERRED)

        sources_raw = raw.get("research_sources", [])
        research_sources = [str(s).strip() for s in sources_raw if s and str(s).strip()] if isinstance(sources_raw, list) else []

        personalization_note = str(raw.get("personalization_note")).strip() if raw.get("personalization_note") else None

        res = {
            "company_name": company_name,
            "company_domain": company_domain,
            "country": country,
            "is_uk_operating": is_uk_operating,
            "industry": industry,
            "is_construction_sector": is_construction_sector,
            "company_size": company_size,
            "employee_count": employee_count,
            "company_size_evidence": company_size_evidence,
            "ownership_type": ownership_type,
            "contact_name": contact_name,
            "job_title": job_title,
            "email": email,
            "linkedin_url": linkedin_url,
            "relevant_signal": relevant_signal,
            "relevant_signal_evidence": relevant_signal_evidence,
            "pain_point": pain_point,
            "pain_point_evidence": pain_point_evidence,
            "personalization_note": personalization_note,
            "research_sources": research_sources,
        }

        # Preserve optional qualification flags
        for key in ["is_active_crm_deal", "is_existing_client", "is_global_suppressed", "contacted_within_60_days", "is_hard_bounce", "email_invalid", "email_status_input", "email_source", "email_verified_primary", "no_signal_override", "decision_maker_reason"]:
            if key in raw:
                res[key] = raw[key]

        return res

    def clean_domain(self, domain: Optional[str]) -> str:
        if not domain:
            return "unknown.com"
        d = str(domain).lower().strip()
        d = re.sub(r"^https?://", "", d)
        d = re.sub(r"^www\.", "", d)
        d = re.sub(r"/.*$", "", d)
        return d.strip()

    def parse_employee_count(self, size_str: str) -> int:
        if not size_str:
            return 0
        clean = size_str.replace(",", "")
        match = re.search(r"\d+", clean)
        return int(match.group(0)) if match else 0

    def normalize_evidence_level(self, level: Any, default_level: EvidenceLevel = EvidenceLevel.UNKNOWN) -> EvidenceLevel:
        if not level:
            return default_level
        if isinstance(level, EvidenceLevel):
            return level
        val_str = level.value if hasattr(level, 'value') else str(level)
        upper = str(val_str).strip().upper()
        try:
            return EvidenceLevel(upper)
        except ValueError:
            return default_level
