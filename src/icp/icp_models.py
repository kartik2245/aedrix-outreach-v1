"""
icp_models.py
Structured Pydantic data models, configurations, and Enums for the Dynamic ICP Designer & Deepline Discovery (Python 3.12).
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class ICPStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    EDITED = "EDITED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    ARCHIVED = "ARCHIVED"


class ICPSource(str, Enum):
    CLAUDE_GENERATED = "CLAUDE_GENERATED"
    MANUAL = "MANUAL"


class GeographyConfig(BaseModel):
    primary_country: str = "United Kingdom"
    country_codes: List[str] = Field(default_factory=lambda: ["UK", "GB", "GBR"])
    allowed_country_keywords: List[str] = Field(
        default_factory=lambda: ["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "NORTHERN IRELAND", "GREAT BRITAIN"]
    )
    require_target_country_operating: bool = True


class SizeThresholdConfig(BaseModel):
    min_employee_count: Optional[int] = 50
    max_employee_count: Optional[int] = None
    min_revenue_gbp_millions: Optional[float] = 10.0
    max_revenue_gbp_millions: Optional[float] = None
    evaluation_mode: str = "OR"  # "OR" or "AND"
    description: str = "Must meet minimum employee count OR minimum revenue threshold."


class ScoringWeights(BaseModel):
    opportunity_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "tier1_scale": 40.0,
            "tier2_scale": 25.0,
            "midmarket_scale": 15.0,
            "high_complexity_signal": 35.0,
            "medium_complexity_signal": 20.0,
            "target_persona_match": 25.0,
        }
    )
    accessibility_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "evidence_verified_email": 50.0,
            "pattern_confirmed_email": 35.0,
            "catchall_unverified_email": 15.0,
            "linkedin_verified": 25.0,
            "signal_verified_personalization": 25.0,
        }
    )
    outreach_priority_index_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "opportunity_weight": 0.6,
            "accessibility_weight": 0.4,
        }
    )


class HardDisqualificationRule(BaseModel):
    code: str
    description: str
    field: str


class CampaignExclusionRule(BaseModel):
    code: str
    description: str
    fields: List[str]


class ICPConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Unique ICP Identifier e.g. icp_uk_construction_2026_01")
    campaign_id: str = Field(default="default_campaign", description="Associated Campaign ID")
    name: str = Field(description="Human readable ICP Name")
    version: str = Field(default="1.0.0", description="Semantic version of ICP definition")
    campaign_description: str = Field(description="High-level objective and campaign context")
    geography: GeographyConfig = Field(default_factory=GeographyConfig)
    industries: List[str] = Field(default_factory=list, description="Target industry verticals")
    allowed_industry_keywords: List[str] = Field(default_factory=list)
    disallowed_industry_keywords: List[str] = Field(default_factory=list)
    company_size: str = Field(default="50+ employees or £10M+ revenue")
    minimum_employees: Optional[int] = 50
    maximum_employees: Optional[int] = None
    minimum_revenue: Optional[float] = 10.0
    maximum_revenue: Optional[float] = None
    target_personas: List[str] = Field(default_factory=list)
    persona_title_keywords: List[str] = Field(default_factory=list)
    positive_signals: List[str] = Field(default_factory=list)
    negative_signals: List[str] = Field(default_factory=list)
    hard_disqualifiers: List[HardDisqualificationRule] = Field(default_factory=list)
    campaign_exclusions: List[CampaignExclusionRule] = Field(default_factory=list)
    required_conditions: List[str] = Field(default_factory=list)
    preferred_conditions: List[str] = Field(default_factory=list)
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)
    source_context: str = Field(default="", description="Original user requirements or prompt")
    voc_context: Optional[str] = Field(default=None, description="Voice of customer context / research angle")
    product_or_service: Optional[str] = Field(default=None, description="Product or service being promoted")
    value_proposition: Optional[str] = Field(default=None, description="Core value proposition of product/service")
    offer: Optional[str] = Field(default=None, description="Outreach offer or hook")
    cta: Optional[str] = Field(default=None, description="Call to action e.g. 'Are you open to a brief 2-minute overview this week?'")
    company_name: Optional[str] = Field(default=None, description="Sender company/brand name")
    sender_name: Optional[str] = Field(default=None, description="Sender person name")
    reasoning: Optional[str] = Field(default="", description="Claude explanation of criteria derivation")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ICPStatus = Field(default=ICPStatus.PENDING_REVIEW)
    source: ICPSource = Field(default=ICPSource.CLAUDE_GENERATED, description="Origin: CLAUDE_GENERATED or MANUAL")


class DeeplineDiscoveryRequest(BaseModel):
    icp_id: str
    campaign_id: str
    campaign_name: str
    geography: List[str]
    industries: List[str]
    company_size: str
    personas: List[str]
    positive_signals: List[str]
    exclusions: List[str]
    requested_lead_count: int = 100
    batch_size: int = 400


class DeeplineRunMetadata(BaseModel):
    run_id: str
    icp_id: str
    campaign_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mode: str = "DRY_RUN_SIMULATION"
    requested_count: int
    discovered_count: int
    valid_count: int
    qualified_count: int
    campaign_excluded_count: int
    hard_disqualified_count: int
    p1_count: int
    p2_count: int
    p3_count: int
    api_calls_made: int = 0
    credits_consumed: int = 0
    safety_status: str = "SAFETY_GATE_ACTIVE"
