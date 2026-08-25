"""
icp_designer.py
Claude-Powered Dynamic Ideal Customer Profile (ICP) Designer (Python 3.12).

Converts natural-language campaign specifications into structured, validated Pydantic ICPConfig objects.
Adheres strictly to zero-hallucination rules and deterministic offline fallback.
"""

import json
import os
import re
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.icp.icp_models import (
    ICPConfig,
    ICPStatus,
    GeographyConfig,
    SizeThresholdConfig,
    ScoringWeights,
    HardDisqualificationRule,
    CampaignExclusionRule,
)


class ICPDesigner:
    def __init__(self, claude_client: Optional[Any] = None):
        """Initializes the ICP Designer. Claude is not used for ICP generation."""
        self.claude_client = None
        self.dry_run = True

    def design_icp(
        self,
        campaign_name: str,
        campaign_objective: str,
        product_context: Optional[str] = None,
        geography: Optional[str] = None,
        industry: Optional[str] = None,
        company_size: Optional[str] = None,
        target_personas: Optional[List[str]] = None,
        minimum_employees: Optional[int] = 10,
        maximum_employees: Optional[int] = None,
        minimum_revenue: Optional[float] = None,
        maximum_revenue: Optional[float] = None,
        positive_signals: Optional[List[str]] = None,
        negative_signals: Optional[List[str]] = None,
        hard_disqualifiers: Optional[List[str]] = None,
        campaign_exclusions: Optional[List[str]] = None,
        voc_context: Optional[str] = None,
        campaign_id: Optional[str] = None,
        product_or_service: Optional[str] = None,
        value_proposition: Optional[str] = None,
        offer: Optional[str] = None,
        cta: Optional[str] = None,
        company_name: Optional[str] = None,
        sender_name: Optional[str] = None,
    ) -> ICPConfig:
        """
        Converts user campaign requirements into a structured ICPConfig.
        Always uses deterministic offline generator (Claude is reserved strictly for email copy).
        Always initializes status as PENDING_REVIEW.
        """
        cid = campaign_id or f"camp_{re.sub(r'[^a-zA-Z0-9_]', '_', campaign_name.lower())[:24]}"
        icp_id = f"icp_{cid}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        prod_ctx = product_or_service or product_context or campaign_objective

        return self._generate_offline_icp(
            icp_id=icp_id,
            campaign_id=cid,
            campaign_name=campaign_name,
            campaign_objective=campaign_objective,
            product_context=prod_ctx,
            geography=geography or "Global",
            industry=industry or "Technology",
            company_size=company_size or "10+ employees",
            target_personas=target_personas,
            minimum_employees=minimum_employees,
            maximum_employees=maximum_employees,
            minimum_revenue=minimum_revenue,
            maximum_revenue=maximum_revenue,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
            hard_disqualifiers=hard_disqualifiers,
            campaign_exclusions=campaign_exclusions,
            voc_context=voc_context,
            product_or_service=prod_ctx,
            value_proposition=value_proposition or voc_context or prod_ctx,
            offer=offer,
            cta=cta,
            company_name=company_name,
            sender_name=sender_name,
        )

    def _build_designer_prompt(
        self,
        campaign_name: str,
        campaign_objective: str,
        product_context: str,
        geography: Optional[str],
        industry: Optional[str],
        company_size: Optional[str],
        target_personas: Optional[List[str]],
        minimum_employees: Optional[int],
        maximum_employees: Optional[int],
        minimum_revenue: Optional[float],
        maximum_revenue: Optional[float],
        positive_signals: Optional[List[str]],
        negative_signals: Optional[List[str]],
        hard_disqualifiers: Optional[List[str]],
        campaign_exclusions: Optional[List[str]],
        voc_context: Optional[str],
    ) -> Dict[str, str]:
        """Builds structured prompt for Claude with strict zero-hallucination constraints."""
        system_prompt = (
            "You are an expert enterprise Go-To-Market and ICP Architect for B2B cold outreach.\n"
            "Your role is to translate natural language campaign specifications into a comprehensive, "
            "structured Ideal Customer Profile (ICP) JSON definition.\n\n"
            "STRICT RULES:\n"
            "1. Do not invent facts about the product or service. Rely strictly on provided context.\n"
            "2. Do not invent fake market statistics or fabricated regulatory mandates.\n"
            "3. Clearly distinguish hard disqualifiers (fatal criteria) from soft preferences.\n"
            "4. Preserve all user-provided constraints exactly.\n"
            "5. If information is missing, use conservative defaults or mark it as unspecified.\n"
            "6. Provide a structured explanation of reasoning for the derived criteria.\n"
            "7. Return ONLY a valid JSON object matching the ICPConfig schema."
        )

        user_input = {
            "campaign_name": campaign_name,
            "campaign_objective": campaign_objective,
            "product_context": product_context,
            "geography": geography,
            "industry": industry,
            "company_size": company_size,
            "target_personas": target_personas or [],
            "minimum_employees": minimum_employees,
            "maximum_employees": maximum_employees,
            "minimum_revenue": minimum_revenue,
            "maximum_revenue": maximum_revenue,
            "positive_signals": positive_signals or [],
            "negative_signals": negative_signals or [],
            "hard_disqualifiers": hard_disqualifiers or [],
            "campaign_exclusions": campaign_exclusions or [],
            "voc_context": voc_context,
        }

        user_prompt = (
            f"Generate a structured ICPConfig JSON for the following campaign requirement:\n"
            f"```json\n{json.dumps(user_input, indent=2)}\n```\n\n"
            f"Ensure the JSON output includes keys: name, version, campaign_description, geography, "
            f"industries, allowed_industry_keywords, disallowed_industry_keywords, company_size, "
            f"minimum_employees, maximum_employees, minimum_revenue, maximum_revenue, target_personas, "
            f"persona_title_keywords, positive_signals, negative_signals, hard_disqualifiers, "
            f"campaign_exclusions, required_conditions, preferred_conditions, scoring_weights, reasoning."
        )

        return {"system": system_prompt, "user": user_prompt}

    def _parse_claude_icp_response(
        self,
        raw_text: str,
        icp_id: str,
        campaign_id: str,
        campaign_name: str,
        campaign_objective: str,
        voc_context: Optional[str],
    ) -> ICPConfig:
        """Parses Claude's JSON response and validates into an ICPConfig."""
        text = raw_text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        else:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1].strip()

        data = json.loads(text)

        # Parse nested models safely
        geo_data = data.get("geography", {})
        if isinstance(geo_data, dict):
            geography = GeographyConfig(
                primary_country=geo_data.get("primary_country", "United Kingdom"),
                country_codes=geo_data.get("country_codes", ["UK", "GB", "GBR"]),
                allowed_country_keywords=geo_data.get("allowed_country_keywords", ["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES"]),
                require_target_country_operating=geo_data.get("require_target_country_operating", True)
            )
        else:
            geography = GeographyConfig()

        hard_disquals = [
            HardDisqualificationRule(
                code=h.get("code", "CUSTOM_DISQUALIFIER"),
                description=h.get("description", str(h)),
                field=h.get("field", "general")
            )
            for h in data.get("hard_disqualifiers", [])
            if isinstance(h, dict)
        ]

        camp_excls = [
            CampaignExclusionRule(
                code=c.get("code", "CUSTOM_EXCLUSION"),
                description=c.get("description", str(c)),
                fields=c.get("fields", ["general"])
            )
            for c in data.get("campaign_exclusions", [])
            if isinstance(c, dict)
        ]

        return ICPConfig(
            id=icp_id,
            campaign_id=campaign_id,
            name=data.get("name", campaign_name),
            version=data.get("version", "1.0.0"),
            campaign_description=data.get("campaign_description", campaign_objective),
            geography=geography,
            industries=data.get("industries", ["Construction", "Commercial Building"]),
            allowed_industry_keywords=data.get("allowed_industry_keywords", ["construction", "contractor", "building"]),
            disallowed_industry_keywords=data.get("disallowed_industry_keywords", ["software only", "retail only"]),
            company_size=data.get("company_size", "50+ employees or £10M+ revenue"),
            minimum_employees=data.get("minimum_employees", 50),
            maximum_employees=data.get("maximum_employees"),
            minimum_revenue=data.get("minimum_revenue", 10.0),
            maximum_revenue=data.get("maximum_revenue"),
            target_personas=data.get("target_personas", ["Digital Director", "IT Director", "Operations Director"]),
            persona_title_keywords=data.get("persona_title_keywords", ["digital", "it director", "operations", "bim"]),
            positive_signals=data.get("positive_signals", ["Digital transformation initiative", "Multi-site regional projects"]),
            negative_signals=data.get("negative_signals", ["Residential micro-subcontractor", "Single site operations"]),
            hard_disqualifiers=hard_disquals,
            campaign_exclusions=camp_excls,
            required_conditions=data.get("required_conditions", ["Operating within target geography", "Enterprise size"]),
            preferred_conditions=data.get("preferred_conditions", ["Active digital team expansion"]),
            scoring_weights=ScoringWeights(),
            source_context=campaign_objective,
            voc_context=voc_context,
            reasoning=data.get("reasoning", "Derived directly from operator campaign requirements."),
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            status=ICPStatus.PENDING_REVIEW
        )
    def _generate_offline_icp(
        self,
        icp_id: str,
        campaign_id: str,
        campaign_name: str,
        campaign_objective: str,
        product_context: str,
        geography: str,
        industry: str,
        company_size: str,
        target_personas: Optional[List[str]],
        minimum_employees: Optional[int],
        maximum_employees: Optional[int],
        minimum_revenue: Optional[float],
        maximum_revenue: Optional[float],
        positive_signals: Optional[List[str]],
        negative_signals: Optional[List[str]],
        hard_disqualifiers: Optional[List[str]] = None,
        campaign_exclusions: Optional[List[str]] = None,
        voc_context: Optional[str] = None,
        product_or_service: Optional[str] = None,
        value_proposition: Optional[str] = None,
        offer: Optional[str] = None,
        cta: Optional[str] = None,
        company_name: Optional[str] = None,
        sender_name: Optional[str] = None,
    ) -> ICPConfig:
        """Deterministic high-fidelity offline ICP generator."""
        import re
        raw_p_list = target_personas if target_personas else ["Director", "Manager", "Head", "Vice President", "Executive"]
        clean_personas = []
        title_keywords = []
        for p in raw_p_list:
            clean_p = re.sub(r'\s*\([^)]*\)', '', str(p)).strip()
            if clean_p:
                clean_personas.append(clean_p)
                for word in clean_p.lower().split():
                    if len(word) > 2 and word not in title_keywords:
                        title_keywords.append(word)

        if not clean_personas:
            clean_personas = ["Director", "Executive"]
        if not title_keywords:
            title_keywords = ["director", "head", "vp", "chief", "manager"]

        # Parse geography into allowed_country_keywords
        geo_str = geography or "Global"
        allowed_country_kw = []
        for term in re.split(r'[\n,;]+', geo_str):
            clean_t = term.strip().upper()
            if clean_t and clean_t not in allowed_country_kw:
                allowed_country_kw.append(clean_t)
        if "UK" in allowed_country_kw or "UNITED KINGDOM" in allowed_country_kw:
            for uk_term in ["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GB", "GBR"]:
                if uk_term not in allowed_country_kw:
                    allowed_country_kw.append(uk_term)
        if not allowed_country_kw:
            allowed_country_kw = [geo_str.upper()]

        # Parse industry into allowed_industry_keywords
        ind_str = industry or "Technology"
        industries_list = [i.strip() for i in re.split(r'[\n,;/]+', ind_str) if i.strip()]
        if not industries_list:
            industries_list = [ind_str]

        allowed_ind_kw = []
        for ind_item in industries_list:
            for word in ind_item.lower().split():
                if len(word) > 2 and word not in allowed_ind_kw:
                    allowed_ind_kw.append(word)
        if not allowed_ind_kw:
            allowed_ind_kw = [ind_str.lower()]

        disallowed_ind_kw = []
        if negative_signals:
            for ns in negative_signals:
                for word in str(ns).lower().split():
                    if len(word) > 3 and word not in disallowed_ind_kw:
                        disallowed_ind_kw.append(word)

        hard_rules = [
            HardDisqualificationRule(
                code="OUTSIDE_TARGET_GEOGRAPHY",
                description=f"Headquarters or primary operations are outside {geography}.",
                field="country"
            ),
            HardDisqualificationRule(
                code="NON_TARGET_INDUSTRY",
                description=f"Company does not operate within {industry}.",
                field="industry"
            ),
            HardDisqualificationRule(
                code="UNDER_SIZE_THRESHOLD",
                description=f"Company has fewer than {minimum_employees or 10} employees.",
                field="company_size"
            ),
        ]
        if hard_disqualifiers:
            for hd in hard_disqualifiers:
                hard_rules.append(
                    HardDisqualificationRule(
                        code=f"CUSTOM_{re.sub(r'[^a-zA-Z0-9_]', '_', hd.upper())[:20]}",
                        description=hd,
                        field="custom_requirement"
                    )
                )

        camp_rules = [
            CampaignExclusionRule(
                code="ACTIVE_CRM_DEAL",
                description="Account has an active sales deal or is an existing customer in CRM.",
                fields=["is_active_crm_deal", "is_existing_client"]
            ),
            CampaignExclusionRule(
                code="GLOBAL_OPT_OUT",
                description="Contact or domain is listed on global suppression blocklist.",
                fields=["is_global_suppressed", "is_opted_out"]
            ),
            CampaignExclusionRule(
                code="CONTACTED_WITHIN_60_DAYS",
                description="Contacted within past 60 days in another campaign.",
                fields=["contacted_within_60_days"]
            ),
            CampaignExclusionRule(
                code="INVALID_BOUNCED_EMAIL",
                description="Email address is marked INVALID_BOUNCED or known hard bounce.",
                fields=["is_hard_bounce", "email_invalid", "email_status"]
            )
        ]
        if campaign_exclusions:
            for ce in campaign_exclusions:
                camp_rules.append(
                    CampaignExclusionRule(
                        code=f"CUSTOM_{re.sub(r'[^a-zA-Z0-9_]', '_', ce.upper())[:20]}",
                        description=ce,
                        fields=["custom_exclusion"]
                    )
                )

        pos_signals = positive_signals or [
            f"Active business operations within {geography}",
            f"Target decision maker persona match within {industry}",
        ]

        neg_signals = negative_signals or [
            "Out of scope business model",
            "Under minimum employee threshold",
        ]

        reasoning = (
            f"Derived criteria to maximize relevance for '{campaign_name}'. Focuses on organizations in {geography} "
            f"within {industry} possessing scale ({company_size}) with verified decision maker signals."
        )

        return ICPConfig(
            id=icp_id,
            campaign_id=campaign_id,
            name=campaign_name,
            version="1.0.0",
            campaign_description=campaign_objective,
            geography=GeographyConfig(
                primary_country=geography,
                allowed_country_keywords=allowed_country_kw,
                require_target_country_operating=True
            ),
            industries=industries_list,
            allowed_industry_keywords=allowed_ind_kw,
            disallowed_industry_keywords=disallowed_ind_kw,
            company_size=company_size,
            minimum_employees=minimum_employees or 10,
            maximum_employees=maximum_employees,
            minimum_revenue=minimum_revenue or 0.0,
            maximum_revenue=maximum_revenue,
            target_personas=clean_personas,
            persona_title_keywords=title_keywords,
            positive_signals=pos_signals,
            negative_signals=neg_signals,
            hard_disqualifiers=hard_rules,
            campaign_exclusions=camp_rules,
            required_conditions=[f"Must operate in {geography}", f"Minimum {minimum_employees or 10} employees"],
            preferred_conditions=["Active growth initiatives", "Identifiable decision maker"],
            scoring_weights=ScoringWeights(),
            source_context=campaign_objective,
            voc_context=voc_context,
            product_or_service=product_or_service or product_context,
            value_proposition=value_proposition or voc_context or product_context or campaign_objective,
            offer=offer,
            cta=cta,
            company_name=company_name,
            sender_name=sender_name,
            reasoning=reasoning,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            status=ICPStatus.PENDING_REVIEW
        )
