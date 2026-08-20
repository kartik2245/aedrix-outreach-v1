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
            return {
                "icp_id": config_input.id,
                "campaign_id": config_input.campaign_id,
                "icp_version": config_input.version,
                "target_geography": {
                    "allowed_country_keywords": geo_dict.get("allowed_country_keywords") or ["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GB"],
                    "require_uk_operating": geo_dict.get("require_target_country_operating", True)
                },
                "allowed_industry_keywords": config_input.allowed_industry_keywords or ["construction", "contractor", "building", "civil engineering", "infrastructure", "engineering"],
                "disallowed_industry_keywords": config_input.disallowed_industry_keywords or ["pure software", "retail only", "hospitality only", "consumer goods"],
                "size_thresholds": {
                    "min_employee_count": config_input.minimum_employees or 50,
                    "min_revenue_gbp_millions": config_input.minimum_revenue or 10.0,
                    "evaluation_mode": "OR"
                },
                "target_personas": {
                    "title_keywords": config_input.persona_title_keywords or ["digital", "it director", "operations", "bim", "transformation", "cio"]
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
                "allowed_country_keywords": ["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GB"],
                "require_uk_operating": True
            },
            "allowed_industry_keywords": ["construction", "contractor", "building", "civil engineering", "infrastructure", "engineering"],
            "disallowed_industry_keywords": ["pure software", "retail only", "hospitality only", "consumer goods"],
            "size_thresholds": {
                "min_employee_count": 50,
                "min_revenue_gbp_millions": 10.0,
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
        """Evaluates Hard Disqualification rules."""
        # Geography check
        is_uk = lead.get("is_uk_operating")
        country = str(lead.get("country") or lead.get("company_location") or "").strip().upper()
        allowed_countries = self.config.get("target_geography", {}).get(
            "allowed_country_keywords", ["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GB"]
        )

        if is_uk is False:
            return True, "Non-UK geography (Headquarters or primary operations outside target geography)", "OUTSIDE_UK"

        if country:
            matches_geo = any(kw in country for kw in allowed_countries)
            if not matches_geo:
                return True, "Non-UK geography (Headquarters or primary operations outside target geography)", "OUTSIDE_UK"

        # Industry & Sector check
        is_const_flag = lead.get("is_construction_sector")
        if is_const_flag is False:
            return True, "Non-construction sector (Out of scope business model)", "NON_CONSTRUCTION"

        industry = str(lead.get("industry") or "").lower()
        construction_type = str(lead.get("construction_type") or "").lower()
        combined_ind = f"{industry} {construction_type}".strip()

        disallowed_keywords = self.config.get("disallowed_industry_keywords", [])
        if any(dkw in combined_ind for dkw in disallowed_keywords):
            return True, "Non-construction sector (Out of scope business model)", "NON_CONSTRUCTION"

        allowed_keywords = self.config.get("allowed_industry_keywords", ["construction", "contractor", "building", "infrastructure", "civil engineering", "engineering"])
        if combined_ind and not any(akw in combined_ind for akw in allowed_keywords):
            return True, "Non-construction sector (Out of scope business model)", "NON_CONSTRUCTION"

        # Size threshold check
        emp_count = self._parse_employee_count(lead)
        rev_millions = self._parse_revenue_millions(lead)
        min_emp = self.config.get("size_thresholds", {}).get("min_employee_count", 50)
        min_rev = self.config.get("size_thresholds", {}).get("min_revenue_gbp_millions", 10.0)

        # If both are known and both are under threshold -> Hard Disqualified
        if emp_count is not None and emp_count > 0 and emp_count < min_emp:
            if rev_millions is not None and rev_millions >= min_rev:
                pass  # Qualified via revenue
            elif rev_millions is None or rev_millions < min_rev:
                return True, f"Under minimum size threshold (<{min_emp} employees)", "UNDER_SIZE_THRESHOLD"

        # Out of scope business model check
        business_model = str(lead.get("business_model") or "").lower()
        if business_model and any(obm in business_model for obm in ["recruiter only", "software vendor", "residential micro-subcontractor"]):
            return True, "Clearly out-of-scope business model", "OUT_OF_SCOPE_BUSINESS_MODEL"

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
