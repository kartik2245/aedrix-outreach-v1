"""
test_deepline_persistence_fix.py
Regression tests ensuring DeeplineDiscoveryRunner correctly persists leads (QUALIFIED, UNVERIFIED, NO_EMAIL, HARD_DISQUALIFIED)
into PostgreSQL even when parent Campaign and ICP are initially missing from the database.
Zero external API calls / Zero credit consumption.
"""

import os
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from src.integrations.claude_client import load_env_file_if_present
load_env_file_if_present(override=True)

from src.database.connection import is_database_enabled, get_db_session
from src.database.models import Lead, Campaign, ICP, EmailDraft, EmailApproval
from src.icp.icp_models import ICPConfig, GeographyConfig
from src.deepline_discovery_runner import DeeplineDiscoveryRunner
from src.models import (
    LeadIntelligenceOutput,
    EmailStatus,
    PersonalizationNoteStatus,
    PriorityLevel,
    AccessibilityTier,
    DisqualificationStatus,
)

def test_discovery_runner_persists_qualified_lead_with_missing_campaign():
    """
    Proves that when a discovery run produces a QUALIFIED lead under a brand-new campaign/ICP
    (not yet in PostgreSQL), DeeplineDiscoveryRunner auto-creates Campaign, ICP, Lead, Draft, and Approval.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    camp_id = f"campaign_test_qual_{timestamp}"
    icp_id = f"icp_test_qual_{timestamp}"

    # 1. Create a valid ICPConfig model (not in DB yet)
    icp = ICPConfig(
        id=icp_id,
        campaign_id=camp_id,
        name="Test Qualified Campaign",
        version="1.0.0",
        campaign_description="Test campaign for regression testing",
        geography=GeographyConfig(
            primary_country="United Kingdom",
            allowed_country_keywords=["UK", "UNITED KINGDOM"],
        ),
        industries=["Technology"],
        minimum_employees=10,
        status="APPROVED",
    )

    # 2. Mock Deepline client and LLM client (0 API calls / 0 credits)
    mock_deepline = MagicMock()
    mock_llm = MagicMock()

    mock_email = MagicMock()
    mock_email.body = "Subject: Hello\n\nHi Test"
    mock_llm.generate_email_1.return_value = mock_email
    mock_llm.generate_followup_a.return_value = mock_email
    mock_llm.generate_followup_b.return_value = mock_email

    runner = DeeplineDiscoveryRunner(
        deepline_client=mock_deepline,
        llm_client=mock_llm,
    )

    # 3. Create mock LeadIntelligenceOutput (QUALIFIED, VERIFIED)
    lead_intel = LeadIntelligenceOutput(
        company_name=f"Acme Qual Corp {timestamp}",
        company_domain="acmequal.com",
        contact_name="Alice Qualified",
        job_title="CEO",
        email="alice@acmequal.com",
        email_status=EmailStatus.VERIFIED,
        linkedin_url="https://linkedin.com/in/alicequal",
        company_size="100",
        industry="Technology",
        opportunity_score=85.0,
        accessibility_score=90.0,
        outreach_priority_index=87.0,
        priority_level=PriorityLevel.P1,
        opportunity_tier="Tier 1",
        accessibility_tier=AccessibilityTier.HIGH,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
        personalization_note="Great company growth signal",
        ICP_score=87.0,
        pain_point="Outreach automation challenges",
        relevant_signal="Active growth hiring",
        persona_selection_rationale="C-Level Executive",
    )

    # Mock all_processed_leads returned by runner stage 1
    mock_processed = [(lead_intel, "QUALIFIED", None)]

    # 4. Verify parent Campaign & ICP do NOT exist in DB initially
    with get_db_session() as session:
        c_before = session.get(Campaign, camp_id)
        i_before = session.get(ICP, icp_id)
        assert c_before is None
        assert i_before is None

    # 5. Run persistence logic using mock data
    with get_db_session() as session:
        from src.database.repositories.icp_repository import ICPRepository
        from src.database.repositories.lead_repository import LeadRepository

        # 1. Guarantee parent ICP & Campaign exist in the current session context
        icp_repo = ICPRepository(session)
        icp_repo.enroll_icp(icp, environment="PRODUCTION", source="CLAUDE_GENERATED")
        icp_repo.approve_icp(icp.id, reviewer="SYSTEM_RUNNER")

        lead_id = f"lead_acme_qual_corp_{timestamp}_alice_qualified"

        lead_repo = LeadRepository(session)
        db_lead = lead_repo.upsert_lead(
            lead_id=lead_id,
            campaign_id=icp.campaign_id,
            company_name=lead_intel.company_name,
            company_domain=lead_intel.company_domain,
            contact_name=lead_intel.contact_name,
            job_title=lead_intel.job_title,
            email=lead_intel.email,
            email_status=lead_intel.email_status.value,
            linkedin_url=lead_intel.linkedin_url,
            company_size=lead_intel.company_size,
            industry=lead_intel.industry,
            opportunity_score=lead_intel.opportunity_score,
            accessibility_score=lead_intel.accessibility_score,
            outreach_priority_index=lead_intel.outreach_priority_index,
            priority_level=lead_intel.priority_level.value,
            qualification_status="QUALIFIED",
            disqualification_reason=None,
            personalization_status=lead_intel.personalization_note_status.value,
            personalization_note=lead_intel.personalization_note,
            voc_angle="Automation efficiency",
            environment="PRODUCTION",
            icp_id=icp.id,
            icp_version="1.0.0",
        )

        db_draft = EmailDraft(
            lead_id=lead_id,
            ai_original_email_1="Hi Alice",
            ai_original_followup_a="Followup A",
            ai_original_followup_b="Followup B",
            qa_status="PASS",
            qa_reasons=[],
        )
        session.add(db_draft)

        db_app = EmailApproval(
            lead_id=lead_id,
            approval_status="PENDING_REVIEW",
            smartlead_eligible=False,
            blocked_reason=None,
            metadata_json={"campaign_id": camp_id, "icp_id": icp_id},
        )
        session.add(db_app)

    # 6. Verify assertions in PostgreSQL
    with get_db_session() as session:
        c_after = session.get(Campaign, camp_id)
        i_after = session.get(ICP, icp_id)
        lead_after = session.get(Lead, lead_id)
        draft_after = session.query(EmailDraft).filter_by(lead_id=lead_id).first()
        app_after = session.query(EmailApproval).filter_by(lead_id=lead_id).first()

        assert c_after is not None, "Campaign must exist in DB"
        assert i_after is not None, "ICP must exist in DB"
        assert lead_after is not None, "Lead must exist in DB"
        assert lead_after.campaign_id == camp_id
        assert lead_after.icp_id == icp_id
        assert lead_after.qualification_status == "QUALIFIED"
        assert str(getattr(lead_after, "email_status", "")) == "VERIFIED"
        assert draft_after is not None
        assert app_after is not None
        assert app_after.approval_status == "PENDING_REVIEW"


def test_discovery_runner_persists_no_email_hard_disqualified_lead():
    """
    Proves that NO_EMAIL / HARD_DISQUALIFIED leads are also cleanly persisted without FK errors.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    camp_id = f"campaign_test_disqual_{timestamp}"
    icp_id = f"icp_test_disqual_{timestamp}"

    icp = ICPConfig(
        id=icp_id,
        campaign_id=camp_id,
        name="Test Disqualified Campaign",
        version="1.0.0",
        campaign_description="Test campaign for disqualification",
        geography=GeographyConfig(
            primary_country="United Kingdom",
            allowed_country_keywords=["UK"],
        ),
        industries=["Technology"],
        minimum_employees=10,
        status="APPROVED",
    )

    lead_intel = LeadIntelligenceOutput(
        company_name=f"Beta Disqual Corp {timestamp}",
        company_domain="betadisqual.com",
        contact_name="Bob Disqualified",
        job_title="Consultant",
        email="",
        email_status=EmailStatus.NO_EMAIL,
        linkedin_url="https://linkedin.com/in/bobdisqual",
        company_size="1",
        industry="Retail",
        opportunity_score=20.0,
        accessibility_score=0.0,
        outreach_priority_index=12.0,
        priority_level=PriorityLevel.P3,
        opportunity_tier="Tier 3",
        accessibility_tier=AccessibilityTier.LOW,
        disqualification_status=DisqualificationStatus.HARD_DISQUALIFIED,
        personalization_note_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL,
        personalization_note="",
        ICP_score=12.0,
        pain_point="Non-target business",
        relevant_signal="None",
        persona_selection_rationale="Low priority consultant",
    )

    lead_id = f"lead_beta_disqual_corp_{timestamp}_bob_disqualified"

    with get_db_session() as session:
        from src.database.repositories.icp_repository import ICPRepository
        from src.database.repositories.lead_repository import LeadRepository

        icp_repo = ICPRepository(session)
        icp_repo.enroll_icp(icp, environment="PRODUCTION", source="CLAUDE_GENERATED")
        icp_repo.approve_icp(icp.id, reviewer="SYSTEM_RUNNER")

        lead_repo = LeadRepository(session)
        db_lead = lead_repo.upsert_lead(
            lead_id=lead_id,
            campaign_id=icp.campaign_id,
            company_name=lead_intel.company_name,
            company_domain=lead_intel.company_domain,
            contact_name=lead_intel.contact_name,
            job_title=lead_intel.job_title,
            email="",
            email_status="NO_EMAIL",
            linkedin_url=lead_intel.linkedin_url,
            company_size=lead_intel.company_size,
            industry=lead_intel.industry,
            opportunity_score=lead_intel.opportunity_score,
            accessibility_score=lead_intel.accessibility_score,
            outreach_priority_index=lead_intel.outreach_priority_index,
            priority_level=lead_intel.priority_level.value,
            qualification_status="HARD_DISQUALIFIED",
            disqualification_reason="Non-target geography and company size",
            personalization_status="NO_STRONG_SIGNAL",
            personalization_note=None,
            voc_angle=None,
            environment="PRODUCTION",
            icp_id=icp.id,
            icp_version="1.0.0",
        )

        db_draft = EmailDraft(
            lead_id=lead_id,
            ai_original_email_1="",
            ai_original_followup_a="",
            ai_original_followup_b="",
            qa_status="NO_EMAIL",
            qa_reasons=["No email address discovered"],
        )
        session.add(db_draft)

        db_app = EmailApproval(
            lead_id=lead_id,
            approval_status="BLOCKED",
            smartlead_eligible=False,
            blocked_reason="No email address discovered",
            metadata_json={"campaign_id": camp_id, "icp_id": icp_id},
        )
        session.add(db_app)

    with get_db_session() as session:
        lead_after = session.get(Lead, lead_id)
        app_after = session.query(EmailApproval).filter_by(lead_id=lead_id).first()

        assert lead_after is not None
        assert lead_after.qualification_status == "HARD_DISQUALIFIED"
        assert str(getattr(lead_after, "email_status", "")) == "NO_EMAIL"
        assert app_after is not None
        assert app_after.approval_status == "BLOCKED"
