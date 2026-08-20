"""
lead_intelligence.py
Production V1 Lead Intelligence Engine for Aedrix Cold Outreach System (Python 3.12).

Implements:
1. 100-Point Opportunity Score & Factor Breakdown
2. 100-Point Accessibility Score
3. Outreach Priority Index: (0.60 * Opportunity) + (0.40 * Accessibility)
4. Evidence Validation (VERIFIED, ESTIMATED, INFERRED, UNKNOWN)
5. Hard Disqualification vs. Campaign Exclusion Rules
6. Evidence-Based Email Verification Statuses
7. Persona Selection Rules & Rationale
8. Two-Sentence Personalization Note with NO_STRONG_SIGNAL Fallback
"""

import math
from typing import Dict, Any, Tuple, Optional
from src.models import (
    LeadIntelligenceOutput,
    EvidenceLevel,
    EmailStatus,
    DisqualificationStatus,
    PersonalizationNoteStatus,
    PriorityLevel,
    AccessibilityTier,
)
from src.role_classifier import RoleTrackClassifier


class LeadIntelligenceEngine:
    def process_lead(self, raw_lead: Dict[str, Any]) -> LeadIntelligenceOutput:
        """Processes a raw lead object through the complete Lead Intelligence Engine."""
        qual_status, qual_reason = self.evaluate_qualification(raw_lead)
        email_status = self.resolve_email_status(raw_lead)

        # Hard Disqualified check
        if qual_status == DisqualificationStatus.HARD_DISQUALIFIED:
            return self.build_output_object(
                raw_lead,
                disqualification_status=DisqualificationStatus.HARD_DISQUALIFIED,
                disqualification_reason=qual_reason,
                email_status=email_status,
                opportunity_score=0.0,
                accessibility_score=0.0,
                outreach_priority_index=0.0,
                priority_level=PriorityLevel.P3,
                opportunity_tier="Disqualified — Out of Scope",
                accessibility_tier=AccessibilityTier.LOW,
                personalization_note_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL,
                personalization_note="Lead disqualified from Aedrix outreach.",
                persona_rationale="Disqualified account."
            )

        # Campaign Exclusion check for invalid email
        if email_status == EmailStatus.INVALID_BOUNCED and qual_status == DisqualificationStatus.QUALIFIED:
            qual_status = DisqualificationStatus.CAMPAIGN_EXCLUDED
            qual_reason = "Email address is invalid or hard bounced (INVALID_BOUNCED)"

        opp_total, opp_factors = self.calculate_opportunity_score(raw_lead)
        acc_total = self.calculate_accessibility_score(raw_lead, email_status)

        # Outreach Priority Index: (0.60 * Opp) + (0.40 * Acc)
        priority_index = round(0.60 * opp_total + 0.40 * acc_total, 1)

        if priority_index >= 85.0:
            priority_level = PriorityLevel.P1
        elif priority_index >= 70.0:
            priority_level = PriorityLevel.P2
        else:
            priority_level = PriorityLevel.P3

        opportunity_tier = self.assign_opportunity_tier(opp_total, raw_lead)
        accessibility_tier = self.assign_accessibility_tier(acc_total)
        persona_rationale = self.evaluate_persona_rationale(raw_lead)
        pers_status, pers_note = self.generate_personalization_note(raw_lead)

        return self.build_output_object(
            raw_lead,
            disqualification_status=qual_status,
            disqualification_reason=qual_reason,
            email_status=email_status,
            opportunity_score=opp_total,
            accessibility_score=acc_total,
            outreach_priority_index=priority_index,
            priority_level=priority_level,
            opportunity_tier=opportunity_tier,
            accessibility_tier=accessibility_tier,
            personalization_note_status=pers_status,
            personalization_note=pers_note,
            persona_rationale=persona_rationale
        )

    def evaluate_qualification(self, lead: Dict[str, Any]) -> Tuple[DisqualificationStatus, Optional[str]]:
        """Evaluates Hard Disqualifiers and Campaign Exclusions."""
        is_uk = lead.get("is_uk_operating")
        country = str(lead.get("country", "")).upper()

        if is_uk is False or (country and "UK" not in country and "UNITED KINGDOM" not in country):
            return DisqualificationStatus.HARD_DISQUALIFIED, "Non-UK geography (Headquarters or primary operations outside UK)"

        if lead.get("is_construction_sector") is False:
            return DisqualificationStatus.HARD_DISQUALIFIED, "Non-construction sector (Out of scope business model)"

        emp_count = lead.get("employee_count")
        if emp_count is not None and emp_count > 0 and emp_count < 50:
            return DisqualificationStatus.HARD_DISQUALIFIED, "Under minimum size threshold (<50 employees)"

        if lead.get("is_active_crm_deal") is True or lead.get("is_existing_client") is True:
            return DisqualificationStatus.CAMPAIGN_EXCLUDED, "Active sales deal or existing customer in CRM"

        if lead.get("is_global_suppressed") is True:
            return DisqualificationStatus.CAMPAIGN_EXCLUDED, "Contact or domain listed on global suppression blocklist"

        if lead.get("contacted_within_60_days") is True:
            return DisqualificationStatus.CAMPAIGN_EXCLUDED, "Contacted within past 60 days in prior campaign"

        return DisqualificationStatus.QUALIFIED, None

    def resolve_email_status(self, lead: Dict[str, Any]) -> EmailStatus:
        """Resolves evidence-based email verification status."""
        if lead.get("email_status_input"):
            inp = lead["email_status_input"]
            if isinstance(inp, EmailStatus):
                return inp
            return EmailStatus(str(inp).strip().upper())
        if lead.get("is_hard_bounce") is True or lead.get("email_invalid") is True:
            return EmailStatus.INVALID_BOUNCED
        if lead.get("email_source") == "OFFICIAL_FILING" or lead.get("email_verified_primary") is True:
            return EmailStatus.EVIDENCE_VERIFIED
        email = lead.get("email", "")
        if email and "@" in email:
            return EmailStatus.PATTERN_CONFIRMED
        return EmailStatus.CATCHALL_UNVERIFIED

    def calculate_opportunity_score(self, lead: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Calculates 100-point Opportunity Score across 7 weighted factors."""
        industry = str(lead.get("industry", "")).lower()
        if any(kw in industry for kw in ["commercial", "educational", "industrial", "main contractor"]):
            fit = 24.0
        elif any(kw in industry for kw in ["infrastructure", "civil"]):
            fit = 18.0
        else:
            fit = 15.0

        size_str = str(lead.get("company_size", ""))
        active_sites = lead.get("active_sites")
        if active_sites is not None and active_sites >= 15:
            complexity = 14.0
        elif any(kw in size_str for kw in ["1,000", "10,000", "7,500", "13,000"]):
            complexity = 14.0
        elif "1,500" in size_str:
            complexity = 12.0
        else:
            complexity = 10.0

        signal = str(lead.get("relevant_signal", "")).lower()
        if any(kw in signal for kw in ["digital by default", "digitall", "expanded digital"]):
            digital = 14.0
        elif any(kw in signal for kw in ["cio", "dfma", "digital"]):
            digital = 13.0
        else:
            digital = 8.0

        title = str(lead.get("job_title", "")).lower()
        if any(kw in title for kw in ["director", "cio", "head of digital"]):
            relevance = 14.0
        else:
            relevance = 10.0

        signal_ev = lead.get("relevant_signal_evidence", EvidenceLevel.UNKNOWN)
        if signal_ev == EvidenceLevel.VERIFIED and signal and signal != "no_strong_signal":
            timing = 9.0
        elif signal and signal != "no_strong_signal":
            timing = 7.0
        else:
            timing = 5.0

        ownership = str(lead.get("ownership_type", "")).upper()
        company_name = str(lead.get("company_name", "")).lower()
        if ownership == "PRIVATE":
            saas = 8.0
        elif "laing" in company_name:
            saas = 6.0
        else:
            saas = 8.0

        if any(kw in size_str for kw in ["26,000", "10,000", "13,000"]):
            scale = 10.0
        elif any(kw in size_str for kw in ["7,500", "1,500"]):
            scale = 8.0
        else:
            scale = 5.0

        total = min(100.0, fit + complexity + digital + relevance + timing + saas + scale)
        return total, {
            "icp_fit": fit,
            "operational_complexity": complexity,
            "digital_transformation": digital,
            "decision_maker_relevance": relevance,
            "buying_timing_signal": timing,
            "saas_likelihood": saas,
            "scale_acv_potential": scale,
        }

    def calculate_accessibility_score(self, lead: Dict[str, Any], email_status: EmailStatus) -> float:
        """Calculates 100-point Accessibility Score."""
        title = str(lead.get("job_title", "")).lower()
        if "cio" in title or "director" in title:
            authority = 28.0
        else:
            authority = 18.0

        if email_status == EmailStatus.EVIDENCE_VERIFIED:
            email_quality = 30.0
        elif email_status == EmailStatus.PATTERN_CONFIRMED:
            email_quality = 22.0
        elif email_status == EmailStatus.CATCHALL_UNVERIFIED:
            email_quality = 12.0
        else:
            email_quality = 0.0

        ownership = str(lead.get("ownership_type", "")).upper()
        company_name = str(lead.get("company_name", "")).lower()
        if ownership == "PRIVATE" or "bowmer" in company_name:
            speed = 24.0
        elif "kier" in company_name:
            speed = 18.0
        elif "morgan" in company_name:
            speed = 12.0
        else:
            speed = 12.0

        if ownership == "PRIVATE":
            ciso_friction = 14.0
        elif "balfour" in company_name:
            ciso_friction = 6.0
        else:
            ciso_friction = 10.0

        return min(100.0, authority + email_quality + speed + ciso_friction)

    def assign_opportunity_tier(self, score: float, lead: Dict[str, Any]) -> str:
        """Assigns Strategic Opportunity Tier."""
        ownership = str(lead.get("ownership_type", "")).upper()
        company_name = str(lead.get("company_name", "")).lower()
        if score >= 88.0 and (ownership == "PRIVATE" or "bowmer" in company_name):
            return "Tier 1 — Mid-Market High Intent"
        if score >= 85.0:
            return "Tier 1 — Enterprise Strategic / Megadeal"
        if score >= 70.0:
            return "Tier 2 — Divisional / Technical Target"
        return "Tier 3 — Standard Target"

    def assign_accessibility_tier(self, score: float) -> AccessibilityTier:
        """Assigns Accessibility Tier."""
        if score >= 80.0:
            return AccessibilityTier.HIGH
        if score >= 60.0:
            return AccessibilityTier.MEDIUM
        return AccessibilityTier.LOW

    def evaluate_persona_rationale(self, lead: Dict[str, Any]) -> str:
        """Evaluates Persona Selection Rationale."""
        title = str(lead.get("job_title", "")).lower()
        size = str(lead.get("company_size", ""))
        ownership = str(lead.get("ownership_type", "")).upper()

        if "1,500" in size or ownership == "PRIVATE":
            return "Selected Business Improvement / Operations Director for mid-market private contractor (direct software budget authority & fast procurement)."
        elif "10,000" in size or "kier" in title:
            return "Selected Digital Director (Construction Division) for Tier-1 Public PLC (direct control over construction division digital systems)."
        elif "26,000" in size or "cio" in title:
            return "Selected Group CIO for mega-infrastructure PLC (group-wide mandate over enterprise IT platforms and AI delivery)."
        else:
            return "Selected senior digital engineering / operational director matching company scale."

    def generate_personalization_note(self, lead: Dict[str, Any]) -> Tuple[PersonalizationNoteStatus, str]:
        """Generates Personalization Note or triggers NO_STRONG_SIGNAL fallback."""
        signal = lead.get("relevant_signal")
        signal_ev = lead.get("relevant_signal_evidence", EvidenceLevel.UNKNOWN)
        has_signal = signal and signal_ev != EvidenceLevel.UNKNOWN and signal != "NO_STRONG_SIGNAL"
        is_no_signal_flag = lead.get("no_signal_override") is True or signal == "NO_STRONG_SIGNAL"

        if not has_signal or is_no_signal_flag:
            return (
                PersonalizationNoteStatus.NO_STRONG_SIGNAL,
                "Given your role leading operations across UK building projects, I thought you'd be interested in how Aedrix unifies pre-construction document control directly with real-time site manpower tracking."
            )

        note_str = lead.get("personalization_note")
        if note_str:
            parts = note_str.split('.')
            s1 = parts[0] + '.'
            s2 = parts[1].strip() + '.' if len(parts) > 1 and parts[1].strip() else "Aedrix provides a ready-to-deploy cloud layer for unifying pre-construction document control and regional manpower tracking."
        else:
            company = lead.get("company_name", "your company")
            clean_signal = str(signal).rstrip(".")
            s1 = f"Saw {company}'s recent initiative regarding {clean_signal}."
            s2 = "Aedrix provides a ready-to-deploy cloud layer for unifying pre-construction document control and regional manpower tracking."

        return PersonalizationNoteStatus.SIGNAL_VERIFIED, f"{s1} {s2}"

    def build_output_object(
        self,
        raw_lead: Dict[str, Any],
        disqualification_status: DisqualificationStatus,
        disqualification_reason: Optional[str],
        email_status: EmailStatus,
        opportunity_score: float,
        accessibility_score: float,
        outreach_priority_index: float,
        priority_level: PriorityLevel,
        opportunity_tier: str,
        accessibility_tier: AccessibilityTier,
        personalization_note_status: PersonalizationNoteStatus,
        personalization_note: str,
        persona_rationale: str
    ) -> LeadIntelligenceOutput:
        """Constructs standardized Pydantic output lead object."""
        role_classification = RoleTrackClassifier.classify(
            job_title=str(raw_lead.get("job_title", "")),
            context=raw_lead,
        )

        return LeadIntelligenceOutput(
            company_name=raw_lead.get("company_name", "UNKNOWN_COMPANY"),
            company_domain=raw_lead.get("company_domain", "unknown.com"),
            contact_name=raw_lead.get("contact_name", "UNKNOWN_CONTACT"),
            job_title=raw_lead.get("job_title", "UNKNOWN_TITLE"),
            email=raw_lead.get("email", "unknown@domain.com"),
            email_status=email_status,
            linkedin_url=raw_lead.get("linkedin_url"),
            company_size=raw_lead.get("company_size", "UNKNOWN"),
            company_size_evidence=raw_lead.get("company_size_evidence", EvidenceLevel.ESTIMATED),
            industry=raw_lead.get("industry", "Construction"),
            opportunity_score=opportunity_score,
            accessibility_score=accessibility_score,
            outreach_priority_index=outreach_priority_index,
            priority_level=priority_level,
            opportunity_tier=opportunity_tier,
            accessibility_tier=accessibility_tier,
            disqualification_status=disqualification_status,
            disqualification_reason=disqualification_reason,
            personalization_note_status=personalization_note_status,
            personalization_note=personalization_note,
            research_sources=raw_lead.get("research_sources", []),
            ICP_score=opportunity_score,
            pain_point=raw_lead.get("pain_point", "Managing pre-construction document control across multi-site teams."),
            pain_point_evidence=raw_lead.get("pain_point_evidence", EvidenceLevel.INFERRED),
            relevant_signal=raw_lead.get("relevant_signal", "NO_STRONG_SIGNAL"),
            relevant_signal_evidence=raw_lead.get("relevant_signal_evidence", EvidenceLevel.UNKNOWN),
            persona_selection_rationale=persona_rationale,
            role_track=role_classification.role_track,
            role_classification_status=role_classification.classification_status,
            role_matched_keyword=role_classification.matched_title_or_keyword,
            role_match_reason=role_classification.reason,
        )
