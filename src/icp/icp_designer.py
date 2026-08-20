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
        product_context: str = "Aedrix is a modular construction management SaaS platform for UK main contractors covering pre-construction document control, drawing versioning, site manpower tracking, and commercial control.",
        geography: Optional[str] = "United Kingdom",
        industry: Optional[str] = "Construction, Commercial & Industrial Building, Infrastructure",
        company_size: Optional[str] = "50+ employees or £10M+ annual revenue",
        target_personas: Optional[List[str]] = None,
        minimum_employees: Optional[int] = 50,
        maximum_employees: Optional[int] = None,
        minimum_revenue: Optional[float] = 10.0,
        maximum_revenue: Optional[float] = None,
        positive_signals: Optional[List[str]] = None,
        negative_signals: Optional[List[str]] = None,
        hard_disqualifiers: Optional[List[str]] = None,
        campaign_exclusions: Optional[List[str]] = None,
        voc_context: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> ICPConfig:
        """
        Converts user campaign requirements into a structured ICPConfig.
        Always uses deterministic offline generator (Claude is reserved strictly for email copy).
        Always initializes status as PENDING_REVIEW.
        """
        cid = campaign_id or f"camp_{re.sub(r'[^a-zA-Z0-9_]', '_', campaign_name.lower())[:24]}"
        icp_id = f"icp_{cid}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        return self._generate_offline_icp(
            icp_id=icp_id,
            campaign_id=cid,
            campaign_name=campaign_name,
            campaign_objective=campaign_objective,
            product_context=product_context,
            geography=geography or "United Kingdom",
            industry=industry or "Construction",
            company_size=company_size or "50+ employees or £10M+ revenue",
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
        hard_disqualifiers: Optional[List[str]],
        campaign_exclusions: Optional[List[str]],
        voc_context: Optional[str],
    ) -> ICPConfig:
        """Deterministic high-fidelity offline ICP generator."""
        personas = target_personas or [
            "Digital Director",
            "IT Director",
            "Operations Director",
            "Business Improvement Director",
            "Chief Information Officer (CIO)",
            "Head of Digital Construction",
        ]

        title_keywords = [
            "digital", "it director", "operations", "business improvement",
            "cio", "cdo", "head of digital", "transformation", "bim"
        ]

        industries_list = [i.strip() for i in industry.split(",") if i.strip()] if isinstance(industry, str) else ["Construction", "Commercial Building", "Infrastructure"]
        allowed_kw = ["construction", "contractor", "building", "civil engineering", "infrastructure", "engineering"]

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
                description=f"Company has fewer than {minimum_employees or 50} employees and revenue under £{minimum_revenue or 10.0}M.",
                field="company_size"
            ),
            HardDisqualificationRule(
                code="OUT_OF_SCOPE_BUSINESS_MODEL",
                description="Business model lacks project or operational document complexity.",
                field="business_model"
            )
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
            "Digital transformation or BIM adoption roadmap",
            "Multi-site regional contractor operations",
            "Document versioning or site coordination complexity",
            "Recent key IT / Operations leadership hire",
        ]

        neg_signals = negative_signals or [
            "Single-site residential micro-contractor",
            "Pure software vendor or IT consultancy",
            "Zero active commercial or civil building projects",
        ]

        reasoning = (
            f"Derived criteria to maximize relevance for '{campaign_name}'. Focuses on organizations in {geography} "
            f"within {industry} possessing scale ({company_size}) with verified complexity signals."
        )

        return ICPConfig(
            id=icp_id,
            campaign_id=campaign_id,
            name=campaign_name,
            version="1.0.0",
            campaign_description=campaign_objective,
            geography=GeographyConfig(
                primary_country=geography,
                allowed_country_keywords=["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GB", "GBR"] if "uk" in geography.lower() else [geography.upper()],
                require_target_country_operating=True
            ),
            industries=industries_list,
            allowed_industry_keywords=allowed_kw,
            disallowed_industry_keywords=["pure software", "retail only", "hospitality only", "consumer goods"],
            company_size=company_size,
            minimum_employees=minimum_employees or 50,
            maximum_employees=maximum_employees,
            minimum_revenue=minimum_revenue or 10.0,
            maximum_revenue=maximum_revenue,
            target_personas=personas,
            persona_title_keywords=title_keywords,
            positive_signals=pos_signals,
            negative_signals=neg_signals,
            hard_disqualifiers=hard_rules,
            campaign_exclusions=camp_rules,
            required_conditions=[f"Must operate in {geography}", f"Minimum {minimum_employees or 50} employees or £{minimum_revenue or 10.0}M revenue"],
            preferred_conditions=["Active digital transformation initiatives", "Document control complexity"],
            scoring_weights=ScoringWeights(),
            source_context=campaign_objective,
            voc_context=voc_context,
            reasoning=reasoning,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            status=ICPStatus.PENDING_REVIEW
        )
