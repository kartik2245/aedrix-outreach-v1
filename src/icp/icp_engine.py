"""
icp_engine.py
Configurable and Dynamic ICP Engine for Aedrix Cold Outreach System (Python 3.12).

Supports:
1. Static JSON configuration file (config/icp_config.json)
2. Dynamic in-memory dictionary configuration
3. Claude-generated structured ICPConfig models

Evaluates raw and researched leads against target ICP criteria and returns structured ICPQualificationResult:
- QUALIFIED
- HARD_DISQUALIFIED
- CAMPAIGN_EXCLUDED
"""

import json
import os
import re
from typing import Dict, Any, Optional, Tuple, List, Union
from src.models import DisqualificationStatus, ICPQualificationResult, EmailStatus
from src.icp.icp_models import ICPConfig


class ICPEngine:
    def __init__(
        self,
        config_path: Optional[Union[str, Dict[str, Any], ICPConfig]] = None,
        config: Optional[Union[Dict[str, Any], ICPConfig]] = None,
        icp_config: Optional[ICPConfig] = None,
    ):
        """
        Initializes the ICP Engine with a config path, raw dictionary, or dynamic ICPConfig model.
        """
        chosen = icp_config or config or config_path
        self.raw_config = chosen
        self.config = self._resolve_config(chosen)

    def _find_default_config_path(self) -> str:
        """Finds config/icp_config.json relative to the project root."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "config", "icp_config.json")

    def _resolve_config(self, config_input: Optional[Union[str, Dict[str, Any], ICPConfig]]) -> Dict[str, Any]:
        """Resolves various configuration inputs into a unified evaluation dictionary."""
        if isinstance(config_input, ICPConfig):
            # Convert dynamic Pydantic ICPConfig
            geo_dict = config_input.geography.model_dump() if hasattr(config_input.geography, "model_dump") else {}
            primary_geo = config_input.geography.primary_country if hasattr(config_input, "geography") and hasattr(config_input.geography, "primary_country") else "United Kingdom"
            allowed_geo = geo_dict.get("allowed_country_keywords") or [primary_geo.upper()]
            return {
                "icp_id": config_input.id,
                "campaign_id": config_input.campaign_id,
                "icp_version": config_input.version,
                "target_geography": {
                    "allowed_country_keywords": allowed_geo,
                    "require_target_country_operating": geo_dict.get("require_target_country_operating", True)
                },
                "allowed_industry_keywords": config_input.allowed_industry_keywords or [i.lower() for i in config_input.industries],
                "disallowed_industry_keywords": config_input.disallowed_industry_keywords or [],
                "size_thresholds": {
                    "min_employee_count": config_input.minimum_employees or 10,
                    "min_revenue_gbp_millions": config_input.minimum_revenue or 0.0,
                    "evaluation_mode": "OR"
                },
                "target_personas": {
                    "title_keywords": config_input.persona_title_keywords or ["director", "head", "vp", "chief", "manager"]
                },
                "hard_disqualification_rules": [r.model_dump() for r in config_input.hard_disqualifiers] if config_input.hard_disqualifiers else [],
                "campaign_exclusion_rules": [r.model_dump() for r in config_input.campaign_exclusions] if config_input.campaign_exclusions else []
            }
        elif isinstance(config_input, dict):
            return config_input
        elif isinstance(config_input, str):
            if os.path.exists(config_input):
                with open(config_input, "r", encoding="utf-8") as f:
                    return json.load(f)

        # Default fallback
        default_path = self._find_default_config_path()
        if os.path.exists(default_path):
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            "target_geography": {
                "allowed_country_keywords": ["UK", "UNITED KINGDOM"],
                "require_target_country_operating": True
            },
            "allowed_industry_keywords": ["technology", "software", "services"],
            "disallowed_industry_keywords": [],
            "size_thresholds": {
                "min_employee_count": 10,
                "min_revenue_gbp_millions": 0.0,
                "evaluation_mode": "OR"
            }
        }

    def evaluate_lead(self, lead: Dict[str, Any]) -> ICPQualificationResult:
        """
        Evaluates a raw or researched lead against ICP and exclusion criteria.
        Returns a structured ICPQualificationResult.
        """
        # 1. Check Hard Disqualifiers First
        hard_disqual, hard_reason, rule_code = self._check_hard_disqualifications(lead)
        if hard_disqual:
            return ICPQualificationResult(
                status=DisqualificationStatus.HARD_DISQUALIFIED,
                disqualification_reason=hard_reason,
                rule_code=rule_code,
                details={"disqualification_type": "HARD_DISQUALIFIED"}
            )

        # 2. Check Campaign Exclusions
        campaign_excl, campaign_reason, excl_code = self._check_campaign_exclusions(lead)
        if campaign_excl:
            return ICPQualificationResult(
                status=DisqualificationStatus.CAMPAIGN_EXCLUDED,
                disqualification_reason=campaign_reason,
                rule_code=excl_code,
                details={"disqualification_type": "CAMPAIGN_EXCLUDED"}
            )

        # 3. Qualified
        return ICPQualificationResult(
            status=DisqualificationStatus.QUALIFIED,
            disqualification_reason=None,
            rule_code="ICP_QUALIFIED",
            details={"fit": "Account matches active ICP criteria and thresholds"}
        )

    def _check_hard_disqualifications(self, lead: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """Evaluates Hard Disqualification rules dynamically against active ICP criteria."""
        # 1. Geography Check
        is_uk_flag = lead.get("is_uk_operating")
        country = str(lead.get("country") or "").strip().upper()
        city = str(lead.get("city") or "").strip().upper()
        address = str(lead.get("address") or "").strip().upper()
        state = str(lead.get("state") or lead.get("region") or "").strip().upper()
        location = str(lead.get("location") or lead.get("geography") or "").strip().upper()
        comp_loc = str(lead.get("company_location") or "").strip().upper()
        comp_name = str(lead.get("company_name") or "").strip().upper()
        signals = str(lead.get("relevant_signal") or "").strip().upper()

        loc_parts = [p for p in [city, address, location, state, comp_loc, country] if p]
        most_specific_loc = loc_parts[0] if loc_parts else country
        full_geo_text = f"{' '.join(loc_parts)} {comp_name} {signals}".upper()

        words = set(re.findall(r'\b[A-Z0-9_]+\b', full_geo_text))
        target_geo = self.config.get("target_geography", {})
        allowed_geo_kw = [str(kw).strip().upper() for kw in target_geo.get("allowed_country_keywords", []) if kw and str(kw).strip()]
        primary_country = str(target_geo.get("primary_country") or "").strip().upper()

        is_uk_only_target = (
            len(allowed_geo_kw) > 0 and all(kw in ("UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GB", "GBR", "NORTHERN IRELAND", "GREAT BRITAIN") for kw in allowed_geo_kw)
        )

        if is_uk_flag is False and is_uk_only_target:
            return True, "Non-UK geography (Headquarters or primary operations outside target geography)", "OUTSIDE_UK"

        if allowed_geo_kw or primary_country:
            matches_geo = False
            if allowed_geo_kw:
                matches_geo = any(kw in words or kw in full_geo_text for kw in allowed_geo_kw)
            if not matches_geo and primary_country and not allowed_geo_kw:
                matches_geo = primary_country in words or primary_country in full_geo_text or (country and country in primary_country)

            if not matches_geo and (country or most_specific_loc):
                loc_str = most_specific_loc or country
                code = "OUTSIDE_UK" if is_uk_only_target else "OUTSIDE_TARGET_GEOGRAPHY"
                reason = "Non-UK geography (Headquarters or primary operations outside target geography)" if is_uk_only_target else f"Non-target geography (Headquarters or primary operations '{loc_str}' outside target geography)"
                return True, reason, code

        # 2. Industry & Sector Check
        is_const_flag = lead.get("is_construction_sector")
        industry = str(lead.get("industry") or "").lower()
        construction_type = str(lead.get("construction_type") or "").lower()
        combined_ind = f"{industry} {construction_type}".strip()

        allowed_keywords = self.config.get("allowed_industry_keywords", [])
        is_const_target = len(allowed_keywords) > 0 and any(kw.lower() in ("construction", "contractor", "building", "civil engineering") for kw in allowed_keywords)

        if is_const_flag is False and is_const_target:
            return True, "Non-target sector (Out of scope business model)", "NON_CONSTRUCTION"

        disallowed_keywords = self.config.get("disallowed_industry_keywords", [])
        if disallowed_keywords:
            if any(dkw.lower() in combined_ind for dkw in disallowed_keywords if dkw and dkw.strip()):
                return True, f"Disallowed industry (Industry '{industry}' matches disallowed ICP criteria)", "DISALLOWED_INDUSTRY"

        # If the lead is explicitly marked as construction sector True, respect that and skip keyword check for construction ICPs
        if not (is_const_flag is True and is_const_target):
            if allowed_keywords and combined_ind:
                matches_ind = any(akw.lower() in combined_ind for akw in allowed_keywords if akw and akw.strip())
                if not matches_ind and len(allowed_keywords) > 0:
                    return True, f"Industry '{industry}' does not match target ICP criteria", "NON_TARGET_INDUSTRY"

        # 3. Size Threshold Check
        emp_count = self._parse_employee_count(lead)
        rev_millions = self._parse_revenue_millions(lead)
        min_emp = self.config.get("size_thresholds", {}).get("min_employee_count", 10)
        min_rev = self.config.get("size_thresholds", {}).get("min_revenue_gbp_millions", 0.0)

        if emp_count is not None and emp_count > 0 and emp_count < min_emp:
            if min_rev > 0 and rev_millions is not None and rev_millions >= min_rev:
                pass  # Qualified via revenue
            else:
                return True, f"Under minimum size threshold (<{min_emp} employees)", "UNDER_SIZE_THRESHOLD"

        return False, None, None

    def _check_campaign_exclusions(self, lead: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """Evaluates Campaign Exclusion rules."""
        if lead.get("is_active_crm_deal") is True or lead.get("is_existing_client") is True:
            return True, "Active sales deal or existing customer in CRM", "ACTIVE_CRM_DEAL"

        if lead.get("is_global_suppressed") is True or lead.get("is_opted_out") is True:
            return True, "Contact or domain listed on global suppression blocklist", "GLOBAL_OPT_OUT"

        if lead.get("contacted_within_60_days") is True:
            return True, "Contacted within past 60 days in prior campaign", "CONTACTED_WITHIN_60_DAYS"

        email_status = lead.get("email_status")
        if email_status == EmailStatus.INVALID_BOUNCED or str(email_status).upper() == "INVALID_BOUNCED":
            return True, "Email address is invalid or hard bounced (INVALID_BOUNCED)", "INVALID_BOUNCED_EMAIL"

        if lead.get("is_hard_bounce") is True or lead.get("email_invalid") is True:
            return True, "Email address is invalid or hard bounced (INVALID_BOUNCED)", "INVALID_BOUNCED_EMAIL"

        return False, None, None

    def _parse_employee_count(self, lead: Dict[str, Any]) -> Optional[int]:
        """Extracts integer employee count from structured field or string."""
        raw_emp = lead.get("employee_count")
        if isinstance(raw_emp, (int, float)) and raw_emp > 0:
            return int(raw_emp)

        size_str = str(lead.get("company_size") or "")
        clean_str = size_str.replace(",", "")
        match = re.search(r"(\d+)", clean_str)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def _parse_revenue_millions(self, lead: Dict[str, Any]) -> Optional[float]:
        """Extracts revenue in millions of GBP if provided."""
        rev_raw = lead.get("revenue")
        if isinstance(rev_raw, (int, float)):
            return float(rev_raw)
        if not rev_raw:
            return None

        rev_str = str(rev_raw).upper().replace(",", "").replace("£", "").replace("$", "").replace("€", "").strip()
        match_b = re.search(r"([\d\.]+)\s*B", rev_str)
        if match_b:
            try:
                return float(match_b.group(1)) * 1000.0
            except ValueError:
                pass

        match_m = re.search(r"([\d\.]+)\s*M", rev_str)
        if match_m:
            try:
                return float(match_m.group(1))
            except ValueError:
                pass

        match_k = re.search(r"([\d\.]+)\s*K", rev_str)
        if match_k:
            try:
                return float(match_k.group(1)) * 0.001
            except ValueError:
                pass

        match_num = re.search(r"^([\d\.]+)$", rev_str)
        if match_num:
            try:
                val = float(match_num.group(1))
                if val >= 1000:
                    return val / 1_000_000.0
                return val
            except ValueError:
                pass
        return None
