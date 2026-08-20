"""
voc_engine.py
Voice-of-Customer (VoC) Engine for Aedrix Cold Outreach System (Python 3.12).

Responsibilities:
- Map verified/inferred research signals to approved UK construction industry language.
- Classify pain areas into approved construction domains (document control, drawing control,
  tendering, pre-construction, manpower/workforce tracking, commercial management, etc.).
- Strictly prohibit fabricated pain points: only use verified evidence or approved baseline value proposition.
- Handle NO_STRONG_SIGNAL fallbacks cleanly.
"""

from typing import Dict, Any, Union, Optional, Tuple
from src.models import (
    LeadIntelligenceOutput,
    VoCContext,
    EvidenceLevel,
    PersonalizationNoteStatus,
)


class VoCEngine:
    BASELINE_PERSONALIZATION = (
        "Given your role leading operations across UK building projects, I thought you'd be "
        "interested in how Aedrix unifies pre-construction document control directly with "
        "real-time site manpower tracking."
    )
    BASELINE_VALUE_PROP = (
        "Aedrix unifies pre-construction document control directly with real-time site manpower "
        "tracking so operational teams operate from a single source of truth."
    )
    BASELINE_VOC_ANGLE = "Pre-Construction Document Control & Real-Time Manpower Tracking"

    # Approved Voice-of-Customer pain domains and industry terminology
    VOC_TAXONOMY = {
        "digital_transformation": {
            "keywords": ["digital by default", "digital transformation", "digital construction", "bim", "dfma", "cio", "digitall", "expanded digital"],
            "angle": "Digital Transformation & Systems Modernization",
            "value_prop": "Aedrix delivers a fast-to-deploy cloud platform that bridges legacy systems with modern site data.",
            "pain_summary": "Navigating digital maturity roadmaps without adding administrative friction across regional project delivery teams."
        },
        "document_drawing_control": {
            "keywords": ["document control", "drawing control", "versioning", "drawings", "rfi", "submittals", "cde", "specifications"],
            "angle": "Pre-Construction Document & Drawing Control",
            "value_prop": "Aedrix eliminates document version latency between pre-construction teams and site subcontractors.",
            "pain_summary": "Managing fast-moving drawing revisions and subcontractor document versions across regional sites."
        },
        "manpower_workforce_tracking": {
            "keywords": ["manpower", "workforce", "labor tracking", "site attendance", "trades", "subcontractor hours", "labor productivity"],
            "angle": "Real-Time Jobsite Manpower & Workforce Visibility",
            "value_prop": "Aedrix gives operations leaders live site headcount and productivity tracking across all active projects.",
            "pain_summary": "Reconciling planned subcontractor allocations against live jobsite attendance without manual paperwork."
        },
        "commercial_financial_management": {
            "keywords": ["commercial management", "financial", "budget", "cost control", "tendering", "procurement", "margins", "variations"],
            "angle": "Commercial & Financial Cost Control",
            "value_prop": "Aedrix connects pre-construction tender estimates directly with live site expenditure and variations.",
            "pain_summary": "Protecting commercial project margins from delayed variation logging and untracked labor overruns."
        },
        "operational_coordination": {
            "keywords": ["fragmented systems", "operational visibility", "manual processes", "silos", "project coordination", "multi-site"],
            "angle": "Operational Coordination & Multi-Site Visibility",
            "value_prop": "Aedrix unifies fragmented spreadsheets and legacy tools into a central operational dashboard.",
            "pain_summary": "Eliminating operational silos and administrative delay between regional site managers and head office."
        }
    }

    def map_lead_voc(self, lead_data: Union[Dict[str, Any], LeadIntelligenceOutput]) -> VoCContext:
        """
        Maps a LeadIntelligenceOutput or raw lead dictionary to structured VoCContext.
        Enforces zero hallucination and evidence-level compliance.
        """
        if isinstance(lead_data, LeadIntelligenceOutput):
            lead = lead_data.model_dump()
        else:
            lead = dict(lead_data)

        signal = lead.get("relevant_signal") or ""
        signal_ev_raw = lead.get("relevant_signal_evidence")
        
        if isinstance(signal_ev_raw, EvidenceLevel):
            signal_ev = signal_ev_raw
        elif signal_ev_raw:
            try:
                signal_ev = EvidenceLevel(str(signal_ev_raw).strip().upper())
            except ValueError:
                signal_ev = EvidenceLevel.UNKNOWN
        else:
            signal_ev = EvidenceLevel.UNKNOWN

        pers_status_raw = lead.get("personalization_note_status")
        is_explicit_no_signal = (
            pers_status_raw == PersonalizationNoteStatus.NO_STRONG_SIGNAL
            or pers_status_raw == "NO_STRONG_SIGNAL"
            or signal == "NO_STRONG_SIGNAL"
            or not signal
            or signal_ev == EvidenceLevel.UNKNOWN
        )

        if is_explicit_no_signal:
            return VoCContext(
                pain_category="pre_construction_document_control",
                voc_angle=self.BASELINE_VOC_ANGLE,
                customer_language_hook=self.BASELINE_PERSONALIZATION,
                personalization_note=self.BASELINE_PERSONALIZATION,
                personalization_note_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL,
                aedrix_value_prop=self.BASELINE_VALUE_PROP,
                evidence_level=EvidenceLevel.UNKNOWN
            )

        # Matched signal exists
        category, taxonomy_match = self._classify_signal_to_voc(signal, lead)
        
        pers_note = lead.get("personalization_note")
        if not pers_note or pers_note == self.BASELINE_PERSONALIZATION:
            company = lead.get("company_name", "your organization")
            clean_signal = signal.rstrip(".")
            pers_note = f"Saw {company}'s recent initiative regarding {clean_signal}. {taxonomy_match['value_prop']}"

        return VoCContext(
            pain_category=category,
            voc_angle=taxonomy_match["angle"],
            customer_language_hook=pers_note,
            personalization_note=pers_note,
            personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
            aedrix_value_prop=taxonomy_match["value_prop"],
            evidence_level=signal_ev
        )

    def _classify_signal_to_voc(self, signal: str, lead: Dict[str, Any]) -> Tuple[str, Dict[str, str]]:
        """Classifies signal or lead fields into the closest approved VoC domain."""
        combined_text = f"{signal} {lead.get('job_title', '')} {lead.get('pain_point', '')}".lower()

        for category, data in self.VOC_TAXONOMY.items():
            for kw in data["keywords"]:
                if kw in combined_text:
                    return category, data

        # Default to operational coordination if specific keywords not hit
        return "operational_coordination", self.VOC_TAXONOMY["operational_coordination"]
