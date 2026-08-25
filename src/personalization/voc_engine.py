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
    def map_lead_voc(
        self,
        lead_data: Union[Dict[str, Any], LeadIntelligenceOutput],
        icp_config: Optional[Any] = None,
    ) -> VoCContext:
        """
        Maps a LeadIntelligenceOutput or raw lead dictionary to structured VoCContext.
        Dynamically adapts to the active ICP config and lead evidence without hardcoded industry templates.
        """
        if isinstance(lead_data, LeadIntelligenceOutput):
            lead = lead_data.model_dump()
        else:
            lead = dict(lead_data)

        # Extract brand, campaign, and value prop details from icp_config if available
        brand_name = getattr(icp_config, "company_name", None) or "Aedrix"
        sender_name = getattr(icp_config, "sender_name", None) or f"{brand_name} Team"
        camp_name = getattr(icp_config, "name", None) or getattr(icp_config, "campaign_id", None)
        camp_obj = getattr(icp_config, "campaign_description", None) or getattr(icp_config, "source_context", None)
        prod_desc = getattr(icp_config, "product_or_service", None) or getattr(icp_config, "product_context", None)
        val_prop = (
            getattr(icp_config, "value_proposition", None)
            or getattr(icp_config, "voc_context", None)
            or camp_obj
            or prod_desc
        )
        offer = getattr(icp_config, "offer", None)
        cta = getattr(icp_config, "cta", None) or "Are you open to a brief 2-minute overview this week?"

        lead_ind = lead.get("industry") or (
            ", ".join(getattr(icp_config, "industries", []))
            if getattr(icp_config, "industries", None)
            else "Business"
        )

        if not val_prop:
            val_prop = f"{brand_name} provides solutions to optimize operational workflows for {lead_ind} organizations."

        default_voc_angle = getattr(icp_config, "voc_context", None) or f"{lead_ind} Operations Optimization"

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

        company = lead.get("company_name", "your company")
        job_title = lead.get("job_title", "operations")

        if is_explicit_no_signal:
            hook = f"Given your role leading {job_title} at {company}, I thought you'd be interested in how {brand_name} supports {lead_ind} teams."
            return VoCContext(
                pain_category=f"{lead_ind.lower().replace(' ', '_')}_operations",
                voc_angle=default_voc_angle,
                customer_language_hook=hook,
                personalization_note=hook,
                personalization_note_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL,
                aedrix_value_prop=val_prop,
                evidence_level=EvidenceLevel.UNKNOWN,
                campaign_name=camp_name,
                campaign_objective=camp_obj,
                product_or_service=prod_desc,
                value_proposition=val_prop,
                offer=offer,
                cta=cta,
                company_name=brand_name,
                sender_name=sender_name,
                geography=str(getattr(icp_config, "geography", "")),
                industry=lead_ind,
            )

        # Matched signal exists
        clean_signal = str(signal).rstrip(".")
        pers_note = lead.get("personalization_note")
        if not pers_note:
            pers_note = f"Saw {company}'s recent initiative regarding {clean_signal}. {val_prop}"

        return VoCContext(
            pain_category=f"{lead_ind.lower().replace(' ', '_')}_verified_signal",
            voc_angle=default_voc_angle,
            customer_language_hook=pers_note,
            personalization_note=pers_note,
            personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
            aedrix_value_prop=val_prop,
            evidence_level=signal_ev,
            campaign_name=camp_name,
            campaign_objective=camp_obj,
            product_or_service=prod_desc,
            value_proposition=val_prop,
            offer=offer,
            cta=cta,
            company_name=brand_name,
            sender_name=sender_name,
            geography=str(getattr(icp_config, "geography", "")),
            industry=lead_ind,
        )
