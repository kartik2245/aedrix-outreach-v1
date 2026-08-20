"""
evidence_validator.py
Evidence Validator Module for Aedrix Lead Intelligence Pipeline (Python 3.12).

Responsibilities:
- Validates each normalized research field.
- Ensures important claims have a value, evidence_level, and valid source where required.
- Supports: VERIFIED, ESTIMATED, INFERRED, UNKNOWN.
- Flags unsupported claims (e.g. claim marked VERIFIED with zero source URLs) and downgrades them.
- Prevents fabricated data from entering the Lead Intelligence Engine.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Union
from src.models import EvidenceLevel


class EvidenceValidator:
    def validate(self, input_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Validates a normalized record or list of records."""
        if isinstance(input_data, list):
            return [self.validate_record(record) for record in input_data]
        return self.validate_record(input_data)

    def validate_record(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        """Validates a single normalized research record."""
        validated = dict(normalized)
        warnings: List[str] = []

        sources = validated.get("research_sources", [])

        # 1. Validate Signal Evidence
        if validated.get("relevant_signal_evidence") == EvidenceLevel.VERIFIED:
            if not sources or len(sources) == 0:
                warnings.append("UNSUPPORTED_CLAIM: Signal marked VERIFIED without research sources. Downgrading to INFERRED.")
                validated["relevant_signal_evidence"] = EvidenceLevel.INFERRED

        # 2. Validate Company Size Evidence
        if validated.get("company_size_evidence") == EvidenceLevel.VERIFIED:
            if not sources or len(sources) == 0:
                warnings.append("UNSUPPORTED_CLAIM: Company size marked VERIFIED without research sources. Downgrading to ESTIMATED.")
                validated["company_size_evidence"] = EvidenceLevel.ESTIMATED

        # 3. Check NO_STRONG_SIGNAL consistency
        rel_signal = validated.get("relevant_signal")
        if rel_signal == "NO_STRONG_SIGNAL" or not rel_signal:
            validated["relevant_signal"] = "NO_STRONG_SIGNAL"
            validated["relevant_signal_evidence"] = EvidenceLevel.UNKNOWN
            validated["personalization_note"] = None  # Forces fallback baseline value prop

        validated["validation_audit"] = {
            "is_valid": True,
            "warnings": warnings,
            "validated_at": datetime.now(timezone.utc).isoformat()
        }

        return validated
