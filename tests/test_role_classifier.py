"""Deterministic unit tests for the R1-R6 role track classifier."""

import pytest

from src.lead_intelligence import LeadIntelligenceEngine
from src.role_classifier import RoleTrackClassifier


@pytest.mark.parametrize(
    ("job_title", "context", "expected_track"),
    [
        ("Document Controller", {}, "R1"),
        ("Head of Document Control", {}, "R1"),
        ("Document Control Manager", {}, "R1"),
        ("Project Director", {}, "R2"),
        ("Project Manager", {}, "R2"),
        ("Operations Director", {"industry": "Specialist mechanical subcontractor"}, "R3"),
        ("Contracts Manager", {"business_model": "Specialist subcontractor"}, "R3"),
        ("Commercial Manager", {}, "R4"),
        ("Quantity Surveyor", {}, "R4"),
        ("QS", {}, "R4"),
        ("Commercial Director", {}, "R4"),
        ("Technical Manager", {}, "R5"),
        ("Design Manager", {}, "R5"),
        ("Digital Lead", {}, "R5"),
        ("BIM Lead", {}, "R5"),
        ("Service Manager", {}, "R6"),
        ("Maintenance Operations Manager", {"industry": "Facilities management"}, "R6"),
    ],
)
def test_classifies_defined_role_tracks(job_title, context, expected_track):
    result = RoleTrackClassifier.classify(job_title, context)

    assert result.role_track == expected_track
    assert result.classification_status == "CLASSIFIED"
    assert result.matched_title_or_keyword
    assert result.reason


def test_operations_manager_without_context_is_ambiguous():
    result = RoleTrackClassifier.classify("Operations Manager")
    assert result.role_track == "UNCLASSIFIED"
    assert result.classification_status == "AMBIGUOUS"


def test_unknown_title_is_unclassified():
    result = RoleTrackClassifier.classify("Chief Happiness Officer")
    assert result.role_track == "UNCLASSIFIED"
    assert result.classification_status == "UNCLASSIFIED"


def test_conflicting_title_matches_resolve_by_precedence():
    # R4 > R2: "Project Manager and Commercial Manager" should resolve to R4
    result = RoleTrackClassifier.classify("Project Manager and Commercial Manager")
    assert result.role_track == "R4"
    assert result.classification_status == "CLASSIFIED"

    # R1 > everything: "Document Controller and Project Director" should resolve to R1
    result2 = RoleTrackClassifier.classify("Document Controller and Project Director")
    assert result2.role_track == "R1"
    assert result2.classification_status == "CLASSIFIED"

    # R5 > R2: "Project Manager and BIM Lead" should resolve to R5
    result3 = RoleTrackClassifier.classify("Project Manager and BIM Lead")
    assert result3.role_track == "R5"
    assert result3.classification_status == "CLASSIFIED"


def test_r3_and_r2_conflicts_resolve_when_context_present():
    # R3 > R2 when S3/subcontractor context exists
    result = RoleTrackClassifier.classify(
        "Project Manager and Contracts Manager", 
        {"industry": "specialist subcontractor"}
    )
    assert result.role_track == "R3"
    assert result.classification_status == "CLASSIFIED"

    # R3 and R2 conflicts remain AMBIGUOUS if context is absent or incorrect
    result2 = RoleTrackClassifier.classify("Project Manager and Contracts Manager", {"industry": "Construction"})
    assert result2.role_track == "UNCLASSIFIED"
    assert result2.classification_status == "AMBIGUOUS"


def test_r6_and_r2_conflicts_resolve_when_context_present():
    # R6 > R2 when S5/FM context exists
    result = RoleTrackClassifier.classify(
        "Project Manager and Facilities Manager",
        {"industry": "Facilities management"}
    )
    assert result.role_track == "R6"
    assert result.classification_status == "CLASSIFIED"


def test_r3_title_without_specialist_subcontractor_context_is_ambiguous():
    result = RoleTrackClassifier.classify("Operations Director", {"industry": "Construction"})
    assert result.role_track == "UNCLASSIFIED"
    assert result.classification_status == "AMBIGUOUS"


def test_lead_intelligence_includes_classifier_output_without_changing_scores():
    result = LeadIntelligenceEngine().process_lead(
        {
            "company_name": "Example Contractor",
            "company_domain": "example.co.uk",
            "contact_name": "Alex Smith",
            "job_title": "Document Controller",
            "email": "alex@example.co.uk",
            "company_size": "200 employees",
            "industry": "Commercial Construction",
            "is_uk_operating": True,
            "country": "UK",
        }
    )

    assert result.role_track == "R1"
    assert result.role_classification_status == "CLASSIFIED"
    assert result.role_matched_keyword == "document controller"
    assert result.role_match_reason
    assert result.opportunity_score == 70.0
    assert result.accessibility_score == 62.0
    assert result.outreach_priority_index == 66.8
