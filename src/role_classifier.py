"""
role_classifier.py

Deterministic R1–R6 Role Track Classifier for the Aedrix Cold Outreach System.

Role tracks:
- R1: Document Controller / Head of Document Control
- R2: Project Director / Project Manager
- R3: Operations Director / Contracts Manager — Specialist Subcontractors
- R4: Commercial Manager / QS / Commercial Director
- R5: Technical / Design Manager / Digital & BIM Lead
- R6: Service / Operations Manager — Maintenance & FM Agencies

Rules:
- Strictly deterministic string and pattern matching (NO LLM calls).
- If a title matches multiple conflicting role tracks or context is ambiguous, returns
  role_track="UNCLASSIFIED", classification_status="AMBIGUOUS".
- If no patterns match, returns role_track="UNCLASSIFIED", classification_status="UNCLASSIFIED".
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, computed_field


class RoleClassificationResult(BaseModel):
    role_track: str  # "R1", "R2", "R3", "R4", "R5", "R6", "UNCLASSIFIED"
    classification_status: str  # "CLASSIFIED", "AMBIGUOUS", "UNCLASSIFIED"
    matched_title_or_keyword: Optional[str] = None
    match_reason: str

    @computed_field
    @property
    def reason(self) -> str:
        """Deterministic explanation exposed with the requested result field name."""
        return self.match_reason


class RoleTrackClassifier:
    """
    Deterministic classifier for mapping B2B construction job titles into Aedrix Role Tracks (R1–R6).
    """

    # Primary Title Keywords per Track
    R1_PATTERNS = [
        r"\bdocument\s+control\b",
        r"\bdocument\s+controller\b",
        r"\bdoc\s+control\b",
        r"\bdocument\s+management\b",
        r"\bdrawing\s+control\b",
        r"\bdrawing\s+controller\b",
    ]

    R2_PATTERNS = [
        r"\bproject\s+director\b",
        r"\bproject\s+manager\b",
        r"\bproject\s+delivery\s+manager\b",
        r"\bprogramm?e?\s+manager\b",
        r"\bprogramm?e?\s+director\b",
        r"\bproject\s+lead\b",
        r"\bdirector\s+of\s+projects\b",
        r"\bhead\s+of\s+projects\b",
    ]

    R3_PATTERNS = [
        r"\bcontracts?\s+manager\b",
        r"\bhead\s+of\s+contracts?\b",
        r"\bcontracts?\s+director\b",
        r"\bdirector\s+of\s+contracts?\b",
        r"\boperations\s+director\b",
        r"\bdirector\s+of\s+operations\b",
        r"\bsubcontractor\s+operations\b",
        r"\bsubcontractor\s+manager\b",
    ]

    R4_PATTERNS = [
        r"\bcommercial\s+manager\b",
        r"\bquantity\s+surveyor\b",
        r"\bqs\b",
        r"\bcommercial\s+director\b",
        r"\bhead\s+of\s+commercial\b",
        r"\bchief\s+commercial\s+officer\b",
        r"\bcco\b",
        r"\bmanaging\s+quantity\s+surveyor\b",
        r"\bcommercial\s+lead\b",
    ]

    R5_PATTERNS = [
        r"\btechnical\s+manager\b",
        r"\btechnical\s+director\b",
        r"\bhead\s+of\s+technical\b",
        r"\bdesign\s+manager\b",
        r"\bdesign\s+director\b",
        r"\bhead\s+of\s+design\b",
        r"\bdesign\s+lead\b",
        r"\bdigital\s+lead\b",
        r"\bdigital\s+director\b",
        r"\bhead\s+of\s+digital\b",
        r"\bdigital\s+construction\b",
        r"\bbim\s+lead\b",
        r"\bbim\s+manager\b",
        r"\bbim\s+director\b",
        r"\bhead\s+of\s+bim\b",
        r"\bvdc\s+manager\b",
        r"\bvdc\s+lead\b",
        r"\bvdc\s+director\b",
        r"\btransformation\s+director\b",
        r"\bhead\s+of\s+transformation\b",
        r"\bbusiness\s+improvement\s+director\b",
        r"\bhead\s+of\s+business\s+improvement\b",
    ]

    R6_PATTERNS = [
        r"\bservice\s+manager\b",
        r"\bhead\s+of\s+service\b",
        r"\bservice\s+director\b",
        r"\bmaintenance\s+operations\s+manager\b",
        r"\bmaintenance\s+manager\b",
        r"\bhead\s+of\s+maintenance\b",
        r"\bfacilities\s+manager\b",
        r"\bfacilities\s+director\b",
        r"\bfm\s+operations\s+manager\b",
        r"\bhead\s+of\s+fm\b",
        r"\bfacilities\s+operations\s+manager\b",
    ]

    # Context keywords indicating Subcontractor / Trade (for R3)
    SUBCONTRACTOR_CONTEXT_KEYWORDS = [
        "subcontractor", "specialist", "trade", "m&e", "mechanical", "electrical",
        "drylining", "steelwork", "glazing", "roofing", "fit-out", "fitout",
        "demolition", "piling", "joinery", "cladding"
    ]

    # Context keywords indicating FM / Maintenance (for R6)
    FM_CONTEXT_KEYWORDS = [
        "fm", "facilities", "maintenance", "property services", "asset management",
        "servicing", "repairs", "estate management"
    ]

    @classmethod
    def _match_patterns(cls, title: str, patterns: List[str]) -> Tuple[bool, Optional[str]]:
        """Checks if title matches any regex pattern in the list."""
        title_clean = title.lower().strip()
        for pattern in patterns:
            match = re.search(pattern, title_clean)
            if match:
                return True, match.group(0)
        return False, None

    @classmethod
    def classify(
        cls,
        job_title: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RoleClassificationResult:
        """
        Classifies a job title into an R1–R6 role track using deterministic rules and context inspection.
        """
        if not job_title or not job_title.strip():
            return RoleClassificationResult(
                role_track="UNCLASSIFIED",
                classification_status="UNCLASSIFIED",
                matched_title_or_keyword=None,
                match_reason="Job title is empty or missing."
            )

        title_clean = job_title.lower().strip()
        ctx = context or {}

        # Collect context strings for disambiguation
        context_str = " ".join([
            str(ctx.get("industry", "")),
            str(ctx.get("trade", "")),
            str(ctx.get("company_name", "")),
            str(ctx.get("construction_type", "")),
            str(ctx.get("business_model", "")),
            str(ctx.get("relevant_signal", "")),
            str(ctx.get("pain_point", ""))
        ]).lower()

        matches = {}

        # Test against all pattern sets
        for track, patterns in [
            ("R1", cls.R1_PATTERNS),
            ("R2", cls.R2_PATTERNS),
            ("R3", cls.R3_PATTERNS),
            ("R4", cls.R4_PATTERNS),
            ("R5", cls.R5_PATTERNS),
            ("R6", cls.R6_PATTERNS),
        ]:
            is_match, matched_keyword = cls._match_patterns(title_clean, patterns)
            if is_match:
                matches[track] = matched_keyword

        # SPECIAL HANDLING: Generic "Operations Manager"
        # "Operations Manager" without Director / Maintenance / FM explicitly in title
        is_generic_ops_mgr = bool(re.search(r"\boperations\s+manager\b", title_clean) and
                                 not re.search(r"\boperations\s+director\b", title_clean) and
                                 not re.search(r"\bmaintenance\s+operations\s+manager\b", title_clean) and
                                 not re.search(r"\bfacilities\s+operations\s+manager\b", title_clean) and
                                 not re.search(r"\bfm\s+operations\s+manager\b", title_clean))

        if is_generic_ops_mgr:
            # Check context to resolve R3 (Subcontractor Ops) vs R6 (FM/Maintenance Ops)
            has_subcontractor_ctx = any(kw in context_str for kw in cls.SUBCONTRACTOR_CONTEXT_KEYWORDS)
            has_fm_ctx = any(kw in context_str for kw in cls.FM_CONTEXT_KEYWORDS)

            if has_subcontractor_ctx and not has_fm_ctx:
                return RoleClassificationResult(
                    role_track="R3",
                    classification_status="CLASSIFIED",
                    matched_title_or_keyword="operations manager (specialist subcontractor context)",
                    match_reason="Generic Operations Manager classified as R3 based on specialist subcontractor context."
                )
            elif has_fm_ctx and not has_subcontractor_ctx:
                return RoleClassificationResult(
                    role_track="R6",
                    classification_status="CLASSIFIED",
                    matched_title_or_keyword="operations manager (maintenance/fm context)",
                    match_reason="Generic Operations Manager classified as R6 based on FM/maintenance context."
                )
            else:
                return RoleClassificationResult(
                    role_track="UNCLASSIFIED",
                    classification_status="AMBIGUOUS",
                    matched_title_or_keyword="operations manager",
                    match_reason="Generic Operations Manager title is ambiguous without distinguishing R3 (Subcontractor Ops) vs R6 (Maintenance/FM) context."
                )

        # Apply deterministic precedence filtering if multiple matches exist
        if len(matches) > 1:
            resolved_tracks = set(matches.keys())
            
            # Rule 1: R1 wins over everything
            if "R1" in resolved_tracks:
                resolved_tracks = {"R1"}
            else:
                # Rule 2 & 3: R4 > R2, R5 > R2
                if "R2" in resolved_tracks:
                    if "R4" in resolved_tracks or "R5" in resolved_tracks:
                        resolved_tracks.discard("R2")
                
                # Rule 4: R3 > R2 when S3/subcontractor context exists
                if "R2" in resolved_tracks and "R3" in resolved_tracks:
                    has_subcontractor_ctx = any(kw in context_str for kw in cls.SUBCONTRACTOR_CONTEXT_KEYWORDS)
                    if has_subcontractor_ctx:
                        resolved_tracks.discard("R2")
                
                # Rule 5: R6 > R2 when S5/FM context exists
                if "R2" in resolved_tracks and "R6" in resolved_tracks:
                    has_fm_ctx = any(kw in context_str for kw in cls.FM_CONTEXT_KEYWORDS)
                    if has_fm_ctx:
                        resolved_tracks.discard("R2")
            
            # Keep only the resolved matches
            matches = {t: matches[t] for t in resolved_tracks}

        # MULTIPLE CONFLICTING TRACK MATCHES CHECK
        if len(matches) > 1:
            matching_tracks = sorted(list(matches.keys()))
            keywords_str = ", ".join([f"{t}: '{matches[t]}'" for t in matching_tracks])
            return RoleClassificationResult(
                role_track="UNCLASSIFIED",
                classification_status="AMBIGUOUS",
                matched_title_or_keyword=f"Multiple tracks matched ({keywords_str})",
                match_reason=f"Title '{job_title}' matched multiple conflicting role tracks: {matching_tracks}. Routing marked AMBIGUOUS."
            )

        # EXACT SINGLE TRACK MATCH
        if len(matches) == 1:
            track = list(matches.keys())[0]
            keyword = matches[track]

            if track == "R3":
                has_subcontractor_ctx = any(kw in context_str for kw in cls.SUBCONTRACTOR_CONTEXT_KEYWORDS)
                has_fm_ctx = any(kw in context_str for kw in cls.FM_CONTEXT_KEYWORDS)
                if not has_subcontractor_ctx or has_fm_ctx:
                    return RoleClassificationResult(
                        role_track="UNCLASSIFIED",
                        classification_status="AMBIGUOUS",
                        matched_title_or_keyword=keyword,
                        match_reason=(
                            "R3 title requires specialist-subcontractor context and cannot be "
                            "resolved when that context is absent or conflicts with maintenance/FM context."
                        )
                    )

            return RoleClassificationResult(
                role_track=track,
                classification_status="CLASSIFIED",
                matched_title_or_keyword=keyword,
                match_reason=f"Matched role track {track} pattern '{keyword}'."
            )

        # NO MATCHES FOUND
        return RoleClassificationResult(
            role_track="UNCLASSIFIED",
            classification_status="UNCLASSIFIED",
            matched_title_or_keyword=None,
            match_reason=f"No matching R1–R6 role track patterns found for title '{job_title}'."
        )
