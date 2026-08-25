"""
models.py
Pydantic data models and Enums for Aedrix Cold Outreach Lead Intelligence, ICP, VoC, and Outreach Engine.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, HttpUrl, ConfigDict


class EvidenceLevel(str, Enum):
    VERIFIED = "VERIFIED"
    ESTIMATED = "ESTIMATED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class EmailStatus(str, Enum):
    VALID = "VALID"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    NO_EMAIL = "NO_EMAIL"
    INVALID = "INVALID"
    BOUNCED = "BOUNCED"
    SUPPRESSED = "SUPPRESSED"
    OPT_OUT = "OPT_OUT"
    UNKNOWN = "UNKNOWN"

    # Backward compatibility aliases
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    PATTERN_CONFIRMED = "PATTERN_CONFIRMED"
    CATCHALL_UNVERIFIED = "CATCHALL_UNVERIFIED"
    INVALID_BOUNCED = "INVALID_BOUNCED"


class DisqualificationStatus(str, Enum):
    QUALIFIED = "QUALIFIED"
    HARD_DISQUALIFIED = "HARD_DISQUALIFIED"
    CAMPAIGN_EXCLUDED = "CAMPAIGN_EXCLUDED"


class PersonalizationNoteStatus(str, Enum):
    SIGNAL_VERIFIED = "SIGNAL_VERIFIED"
    NO_STRONG_SIGNAL = "NO_STRONG_SIGNAL"


class PriorityLevel(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class AccessibilityTier(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class OutreachState(str, Enum):
    INITIAL = "INITIAL"
    QUALIFIED = "QUALIFIED"
    EMAIL_1_READY = "EMAIL_1_READY"
    EMAIL_1_SENT = "EMAIL_1_SENT"
    EMAIL_1_OPENED = "EMAIL_1_OPENED"
    WAITING_FOLLOWUP_A = "WAITING_FOLLOWUP_A"
    FOLLOWUP_A_READY = "FOLLOWUP_A_READY"
    FOLLOWUP_A_SENT = "FOLLOWUP_A_SENT"
    EMAIL_1_UNOPENED = "EMAIL_1_UNOPENED"
    WAITING_FOLLOWUP_B = "WAITING_FOLLOWUP_B"
    FOLLOWUP_B_READY = "FOLLOWUP_B_READY"
    FOLLOWUP_B_SENT = "FOLLOWUP_B_SENT"
    TOUCH_3_READY = "TOUCH_3_READY"
    TOUCH_3_SENT = "TOUCH_3_SENT"
    TOUCH_4_READY = "TOUCH_4_READY"
    TOUCH_4_SENT = "TOUCH_4_SENT"
    TOUCH_5_READY = "TOUCH_5_READY"
    TOUCH_5_SENT = "TOUCH_5_SENT"
    STOPPED_REPLIED = "STOPPED_REPLIED"
    STOPPED_BOUNCED = "STOPPED_BOUNCED"
    STOPPED_UNSUBSCRIBED = "STOPPED_UNSUBSCRIBED"
    HANDOFF_HUMAN_SALES = "HANDOFF_HUMAN_SALES"
    SUPPRESSED_NOT_INTERESTED = "SUPPRESSED_NOT_INTERESTED"
    HOLD = "HOLD"
    OOO_DELAYED = "OOO_DELAYED"


class ICPQualificationResult(BaseModel):
    status: DisqualificationStatus
    disqualification_reason: Optional[str] = None
    rule_code: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class VoCContext(BaseModel):
    pain_category: str
    voc_angle: str
    customer_language_hook: str
    personalization_note: str
    personalization_note_status: PersonalizationNoteStatus
    aedrix_value_prop: str
    evidence_level: EvidenceLevel = EvidenceLevel.UNKNOWN
    campaign_name: Optional[str] = None
    campaign_objective: Optional[str] = None
    product_or_service: Optional[str] = None
    value_proposition: Optional[str] = None
    offer: Optional[str] = None
    cta: Optional[str] = None
    company_name: Optional[str] = None
    sender_name: Optional[str] = None
    geography: Optional[str] = None
    industry: Optional[str] = None


class PersonalizationQAResult(BaseModel):
    qa_status: str  # "PASS" or "FAIL"
    qa_reasons: List[str] = Field(default_factory=list)
    word_counts: Dict[str, int] = Field(default_factory=dict)
    checks_passed: List[str] = Field(default_factory=list)
    checks_failed: List[str] = Field(default_factory=list)


class LeadIntelligenceOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    company_name: str
    company_domain: str
    contact_name: str
    job_title: str
    email: str
    email_status: EmailStatus
    linkedin_url: Optional[str] = None
    company_size: str
    company_size_evidence: EvidenceLevel = EvidenceLevel.ESTIMATED
    industry: str
    opportunity_score: float = Field(ge=0, le=100)
    accessibility_score: float = Field(ge=0, le=100)
    outreach_priority_index: float = Field(ge=0, le=100)
    priority_level: PriorityLevel
    opportunity_tier: str
    accessibility_tier: AccessibilityTier
    disqualification_status: DisqualificationStatus
    disqualification_reason: Optional[str] = None
    personalization_note_status: PersonalizationNoteStatus
    personalization_note: str
    research_sources: List[str] = Field(default_factory=list)
    ICP_score: float = Field(ge=0, le=100)  # Legacy alias
    pain_point: str
    pain_point_evidence: EvidenceLevel = EvidenceLevel.INFERRED
    relevant_signal: str
    relevant_signal_evidence: EvidenceLevel = EvidenceLevel.UNKNOWN
    persona_selection_rationale: str
    role_track: str = "UNCLASSIFIED"
    role_classification_status: str = "UNCLASSIFIED"
    role_matched_keyword: Optional[str] = None
    role_match_reason: Optional[str] = None


class EmailGenerationResult(BaseModel):
    email_type: str
    subject: str
    body: str
    word_count: int
    personalization_status: PersonalizationNoteStatus
    evidence_used: List[str] = Field(default_factory=list)
    generation_mode: str = "DRY_RUN_TEMPLATE"


class ReplyClassificationResult(BaseModel):
    classification: str
    confidence: float
    reasoning: str
    requires_human_handoff: bool
    generation_mode: str = "DRY_RUN_TEMPLATE"


class SmartleadPayload(BaseModel):
    api_endpoint: str
    headers: Dict[str, str]
    payload: Dict[str, Any]
    campaign_status: Optional[str] = "DRAFT_PAUSED_TEST"
    mock_response: Dict[str, Any]


class BatchLeadDraftOutput(BaseModel):
    company: str
    contact: str
    title: str
    qualification_status: str
    opportunity_score: float
    accessibility_score: float
    outreach_priority_index: float
    priority: str
    personalization_note_status: str
    personalization_note: str
    voc_angle: str
    email_1: str
    followup_a: str
    followup_b: str
    qa_status: str
    qa_reasons: List[str] = Field(default_factory=list)


class SmartleadWebhookEventType(str, Enum):
    EMAIL_SENT = "EMAIL_SENT"
    EMAIL_OPENED = "EMAIL_OPENED"
    EMAIL_CLICKED = "EMAIL_CLICKED"
    EMAIL_REPLIED = "EMAIL_REPLIED"
    EMAIL_BOUNCED = "EMAIL_BOUNCED"
    EMAIL_UNSUBSCRIBED = "EMAIL_UNSUBSCRIBED"


class SmartleadWebhookEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_type: SmartleadWebhookEventType
    lead_email: str
    campaign_id: Optional[str] = None
    event_timestamp: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


class SmartleadLeadPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    first_name: str
    last_name: str = ""
    company_name: str
    website: Optional[str] = None
    linkedin_profile: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class SmartleadAuditEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    timestamp: str
    action: str
    lead_id: Optional[str] = None
    company: Optional[str] = None
    provider: str = "SMARTLEAD"
    status: str
    campaign_id: Optional[str] = None
    approval_status: Optional[str] = None
    reviewer: Optional[str] = None
    dry_run: bool = True
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

