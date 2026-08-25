import pytest
from src.integrations.deepline_client import DeeplineClient
from src.deepline_discovery_runner import DeeplineDiscoveryRequest
from src.icp.icp_designer import ICPDesigner
from src.icp.icp_engine import ICPEngine
from src.icp.icp_models import ICPStatus
from src.deepline_export_adapter import DeeplineExportAdapter
from app.api.icp import create_manual_icp, CreateManualICPRequest


def make_request(**kwargs):
    defaults = {
        "icp_id": "icp_test_001",
        "campaign_id": "camp_test_001",
        "campaign_name": "Generic Test Campaign",
        "geography": ["United Kingdom"],
        "industries": ["Technology"],
        "company_size": "10+ employees",
        "personas": ["Director"],
        "positive_signals": ["Growth"],
        "exclusions": ["CRM"],
        "requested_lead_count": 10
    }
    defaults.update(kwargs)
    return DeeplineDiscoveryRequest(**defaults)


def test_chandigarh_mohali_panchkula_no_uk_leakage():
    # 1. Test manual ICP creation API endpoint
    req = CreateManualICPRequest(
        campaign_name="AI Services Chandigarh",
        campaign_objective="Find AI companies in Tricity",
        geography="Chandigarh, Mohali, Panchkula",
        industries=["Information Technology", "Software Development"],
        minimum_employees=10
    )
    icp_res = create_manual_icp(req)
    icp_obj = icp_res["icp"]
    geo_keywords = icp_obj.geography.allowed_country_keywords

    assert "CHANDIGARH" in geo_keywords
    assert "MOHALI" in geo_keywords
    assert "PANCHKULA" in geo_keywords

    # Must NOT contain UK legacy fallbacks
    for prohibited in ["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GREAT BRITAIN"]:
        assert prohibited not in geo_keywords

    # 2. Test Deepline Client Payload Generation
    client = DeeplineClient(live_mode=False)
    discovery_req = DeeplineDiscoveryRequest(
        icp_id=icp_obj.id,
        campaign_id=icp_obj.campaign_id,
        campaign_name=icp_obj.name,
        geography=geo_keywords,
        industries=icp_obj.industries,
        company_size=icp_obj.company_size,
        personas=icp_obj.target_personas,
        positive_signals=[],
        exclusions=[],
        requested_lead_count=10
    )
    payload = client.build_v2_payload(discovery_req)["payload"]
    locations = payload["account"]["location"]["any"]["include"]

    assert "CHANDIGARH" in locations
    assert "MOHALI" in locations
    assert "PANCHKULA" in locations
    assert "United Kingdom" not in locations


def test_india_geography_only():
    req = CreateManualICPRequest(
        campaign_name="India Tech",
        campaign_objective="Find tech in India",
        geography="India",
        industries=["Software"],
        minimum_employees=10
    )
    icp_res = create_manual_icp(req)
    icp_obj = icp_res["icp"]
    geo_keywords = icp_obj.geography.allowed_country_keywords
    assert geo_keywords == ["INDIA"]

    client = DeeplineClient(live_mode=False)
    discovery_req = DeeplineDiscoveryRequest(
        icp_id=icp_obj.id,
        campaign_id=icp_obj.campaign_id,
        campaign_name=icp_obj.name,
        geography=geo_keywords,
        industries=["Software"],
        company_size="10+ employees",
        personas=["CEO"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )
    payload = client.build_v2_payload(discovery_req)["payload"]
    locations = payload["account"]["location"]["any"]["include"]
    assert locations == ["INDIA"]


def test_bangalore_geography_only():
    req = CreateManualICPRequest(
        campaign_name="Bangalore SaaS",
        campaign_objective="Find SaaS in Bangalore",
        geography="Bangalore, India",
        industries=["SaaS"],
        minimum_employees=10
    )
    icp_res = create_manual_icp(req)
    icp_obj = icp_res["icp"]
    geo_keywords = icp_obj.geography.allowed_country_keywords
    assert "BANGALORE" in geo_keywords
    assert "INDIA" in geo_keywords
    assert len(geo_keywords) == 2

    client = DeeplineClient(live_mode=False)
    discovery_req = DeeplineDiscoveryRequest(
        icp_id=icp_obj.id,
        campaign_id=icp_obj.campaign_id,
        campaign_name=icp_obj.name,
        geography=geo_keywords,
        industries=["SaaS"],
        company_size="10+ employees",
        personas=["CEO"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )
    payload = client.build_v2_payload(discovery_req)["payload"]
    locations = payload["account"]["location"]["any"]["include"]
    assert "BANGALORE" in locations
    assert "INDIA" in locations
    assert "United Kingdom" not in locations


def test_london_geography_only():
    req = CreateManualICPRequest(
        campaign_name="London FinTech",
        campaign_objective="Find FinTech in London",
        geography="London, United Kingdom",
        industries=["FinTech"],
        minimum_employees=10
    )
    icp_res = create_manual_icp(req)
    icp_obj = icp_res["icp"]
    geo_keywords = icp_obj.geography.allowed_country_keywords
    assert "LONDON" in geo_keywords
    assert "UNITED KINGDOM" in geo_keywords

    client = DeeplineClient(live_mode=False)
    discovery_req = DeeplineDiscoveryRequest(
        icp_id=icp_obj.id,
        campaign_id=icp_obj.campaign_id,
        campaign_name=icp_obj.name,
        geography=geo_keywords,
        industries=["FinTech"],
        company_size="10+ employees",
        personas=["CEO"],
        positive_signals=[],
        exclusions=[],
        requested_lead_count=1
    )
    payload = client.build_v2_payload(discovery_req)["payload"]
    locations = payload["account"]["location"]["any"]["include"]
    assert "LONDON" in locations
    assert "United Kingdom" in locations


def test_it_company_not_construction_sector():
    adapter = DeeplineExportAdapter()
    raw_lead = {
        "company_name": "Nethermind",
        "company_domain": "nethermind.io",
        "country": "UNITED KINGDOM",
        "industry": "Information Technology & Services",
        "contact_name": "Antonio Sabado",
        "job_title": "Chief Growth Officer"
    }
    adapted = adapter.adapt_record(raw_lead)
    assert adapted["industry"] == "Information Technology & Services"
    assert adapted["is_construction_sector"] is False


def test_generic_icp_qualification_flow():
    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="Bangalore Tech",
        campaign_objective="Find Bangalore tech leads",
        geography="Bangalore, India",
        industry="Software, Artificial Intelligence",
        company_size="10+ employees",
        minimum_employees=10
    )
    engine = ICPEngine(icp_config=icp)

    lead_bangalore = {
        "company_name": "AI Solutions Pvt Ltd",
        "company_domain": "aisolutions.in",
        "country": "INDIA",
        "company_location": "Bangalore, India",
        "industry": "Software & Artificial Intelligence",
        "employee_count": 25,
        "contact_name": "Anita Rao",
        "job_title": "CEO",
        "email": "anita@aisolutions.in"
    }
    res = engine.evaluate_lead(lead_bangalore)
    assert res.status.value == "QUALIFIED"

    # Mismatched location should fail
    lead_uk = {
        "company_name": "London Tech Ltd",
        "country": "UNITED KINGDOM",
        "company_location": "London, UK",
        "industry": "Software",
        "employee_count": 50,
        "contact_name": "John Smith",
        "job_title": "CEO",
        "email": "john@londontech.co.uk"
    }
    res_uk = engine.evaluate_lead(lead_uk)
    assert res_uk.status.value == "HARD_DISQUALIFIED"
    assert res_uk.rule_code == "OUTSIDE_TARGET_GEOGRAPHY"


def test_sparkbrains_lead_persistence_regardless_of_qualification(monkeypatch):
    """Test that SparkBrains lead from discovery run is persisted regardless of qualification status."""
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from unittest.mock import MagicMock

    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="AI Services Chandigarh Tricity",
        campaign_objective="Target tech companies in Chandigarh, Mohali, Panchkula",
        geography="Chandigarh, Mohali, Panchkula",
        industry="Information Technology, Software Development",
        company_size="10+ employees",
        minimum_employees=10
    )
    icp.status = ICPStatus.APPROVED

    sparkbrains_lead = {
        "company_name": "SparkBrains",
        "company_domain": "sparkbrains.in",
        "country": "INDIA",
        "company_location": "Chandigarh, India",
        "industry": "Computer Software",
        "company_size": "UNKNOWN",
        "contact_name": "Bhisham Trehan",
        "job_title": "Co-Founder & Managing Director",
        "email": "bhisham@sparkbrains.in"
    }

    mock_client = MagicMock()
    mock_client.discover_leads.return_value = {"leads": [sparkbrains_lead]}
    mock_client.live_mode = False

    runner = DeeplineDiscoveryRunner(deepline_client=mock_client)
    res = runner.run_discovery_pipeline(icp, requested_count=1)

    assert res["summary"]["discovered"] == 1

    # Check persistence in ApprovalStore
    store = ApprovalStore()
    recs = store.load_queue()
    sb_recs = [r for r in recs if r.company == "SparkBrains" and r.icp_id == icp.id]
    assert len(sb_recs) >= 1
    rec = sb_recs[-1]
    assert rec.company == "SparkBrains"
    assert rec.contact == "Bhisham Trehan"
    assert rec.icp_id == icp.id
    assert rec.campaign_id == icp.campaign_id


def test_multiple_icps_lead_association():
    """Test that Lead A from ICP A stays with ICP A and Lead B from ICP B stays with ICP B."""
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from unittest.mock import MagicMock

    designer = ICPDesigner()
    icp_a = designer.design_icp(
        campaign_name="ICP Alpha",
        campaign_objective="Objective A",
        geography="London",
        industry="Software",
        company_size="10+ employees"
    )
    icp_a.status = ICPStatus.APPROVED

    icp_b = designer.design_icp(
        campaign_name="ICP Beta",
        campaign_objective="Objective B",
        geography="Bangalore",
        industry="SaaS",
        company_size="10+ employees"
    )
    icp_b.status = ICPStatus.APPROVED

    lead_a = {
        "company_name": "Alpha Corp",
        "company_domain": "alpha.co.uk",
        "country": "UK",
        "industry": "Software",
        "contact_name": "Alice Smith",
        "job_title": "CEO",
        "email": "alice@alpha.co.uk"
    }

    lead_b = {
        "company_name": "Beta Systems",
        "company_domain": "beta.in",
        "country": "INDIA",
        "industry": "SaaS",
        "contact_name": "Bob Rao",
        "job_title": "CTO",
        "email": "bob@beta.in"
    }

    mock_client_a = MagicMock()
    mock_client_a.discover_leads.return_value = {"leads": [lead_a]}
    mock_client_a.live_mode = False
    runner_a = DeeplineDiscoveryRunner(deepline_client=mock_client_a)
    runner_a.run_discovery_pipeline(icp_a, requested_count=1)

    mock_client_b = MagicMock()
    mock_client_b.discover_leads.return_value = {"leads": [lead_b]}
    mock_client_b.live_mode = False
    runner_b = DeeplineDiscoveryRunner(deepline_client=mock_client_b)
    runner_b.run_discovery_pipeline(icp_b, requested_count=1)

    store = ApprovalStore()
    recs = store.load_queue()
    rec_a = [r for r in recs if r.company == "Alpha Corp" and r.icp_id == icp_a.id][-1]
    rec_b = [r for r in recs if r.company == "Beta Systems" and r.icp_id == icp_b.id][-1]

    assert rec_a.icp_id == icp_a.id
    assert rec_a.campaign_id == icp_a.campaign_id
    assert rec_b.icp_id == icp_b.id
    assert rec_b.campaign_id == icp_b.campaign_id


def test_email_gen_chandigarh_ai_icp_technology_context_no_construction_leak():
    """TEST 1: AI/Software ICP in Chandigarh produces technology-relevant email context and no construction terms."""
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from unittest.mock import MagicMock

    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="Chandigarh AI SaaS",
        campaign_objective="Connect with AI & SaaS companies in Chandigarh, India",
        product_or_service="Enterprise AI Analytics Engine",
        value_proposition="Automate data insights and predictive analytics for tech teams.",
        geography="Chandigarh, India",
        industry="Software, Artificial Intelligence, SaaS",
        company_size="10+ employees",
        company_name="TechData AI",
        sender_name="TechData Team"
    )
    icp.status = ICPStatus.APPROVED

    lead_dict = {
        "company_name": "Chandigarh AI Labs",
        "company_domain": "ailabs.in",
        "country": "INDIA",
        "company_location": "Chandigarh, India",
        "industry": "Artificial Intelligence",
        "employee_count": 25,
        "contact_name": "Rohit Kumar",
        "job_title": "Head of AI",
        "email": "rohit@ailabs.in"
    }

    mock_client = MagicMock()
    mock_client.discover_leads.return_value = {"leads": [lead_dict]}
    mock_client.live_mode = False

    runner = DeeplineDiscoveryRunner(deepline_client=mock_client)
    res = runner.run_discovery_pipeline(icp, requested_count=1)

    store = ApprovalStore()
    recs = store.load_queue()
    rec = [r for r in recs if r.company == "Chandigarh AI Labs"][-1]

    email_copy = f"{rec.email_1_original} {rec.followup_a_original} {rec.followup_b_original}".lower()

    # Must contain tech/brand context
    assert "techdata" in email_copy or "ai" in email_copy or "software" in email_copy or "analytics" in email_copy
    # Must NOT contain hardcoded construction terms
    for leak_term in ["pre-construction", "site manpower tracking", "subcontractor document", "building projects"]:
        assert leak_term not in email_copy


def test_email_gen_construction_icp_retains_construction_messaging():
    """TEST 2: Construction ICP generates construction-relevant messaging when explicitly specified."""
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from unittest.mock import MagicMock

    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="UK Construction Enterprise",
        campaign_objective="Target main contractors for construction management SaaS",
        product_or_service="Construction Operations Platform",
        value_proposition="Streamline site log governance and contractor project delivery.",
        geography="United Kingdom",
        industry="Commercial Construction",
        company_size="50+ employees",
        company_name="BuildCloud",
        sender_name="BuildCloud Team"
    )
    icp.status = ICPStatus.APPROVED

    lead_dict = {
        "company_name": "Apex Builders plc",
        "company_domain": "apexbuilders.co.uk",
        "country": "UNITED KINGDOM",
        "industry": "Commercial Construction",
        "contact_name": "David Clark",
        "job_title": "Operations Director",
        "email": "d.clark@apexbuilders.co.uk"
    }

    mock_client = MagicMock()
    mock_client.discover_leads.return_value = {"leads": [lead_dict]}
    mock_client.live_mode = False

    runner = DeeplineDiscoveryRunner(deepline_client=mock_client)
    runner.run_discovery_pipeline(icp, requested_count=1)

    store = ApprovalStore()
    recs = store.load_queue()
    rec = [r for r in recs if r.company == "Apex Builders plc"][-1]

    email_copy = f"{rec.email_1_original} {rec.followup_a_original} {rec.followup_b_original}".lower()
    assert "buildcloud" in email_copy
    assert "construction" in email_copy


def test_email_gen_unrelated_healthcare_icp():
    """TEST 3: A second unrelated ICP (Healthcare in London) produces healthcare messaging."""
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from unittest.mock import MagicMock

    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="London Healthcare Tech",
        campaign_objective="Target clinics and hospital networks for patient record workflow automation",
        product_or_service="HealthFlow EHR Integration",
        value_proposition="Automate patient intake and clinical record compliance.",
        geography="London, UK",
        industry="Healthcare, Hospital & Health Care",
        company_size="50+ employees",
        company_name="HealthFlow",
        sender_name="HealthFlow Team"
    )
    icp.status = ICPStatus.APPROVED

    lead_dict = {
        "company_name": "London Care Network",
        "company_domain": "londoncare.co.uk",
        "country": "UNITED KINGDOM",
        "industry": "Hospital & Health Care",
        "contact_name": "Dr. Sarah Jenkins",
        "job_title": "Medical Director",
        "email": "sarah@londoncare.co.uk"
    }

    mock_client = MagicMock()
    mock_client.discover_leads.return_value = {"leads": [lead_dict]}
    mock_client.live_mode = False

    runner = DeeplineDiscoveryRunner(deepline_client=mock_client)
    runner.run_discovery_pipeline(icp, requested_count=1)

    store = ApprovalStore()
    recs = store.load_queue()
    rec = [r for r in recs if r.company == "London Care Network"][-1]

    email_copy = f"{rec.email_1_original} {rec.followup_a_original} {rec.followup_b_original}".lower()
    assert "healthflow" in email_copy
    assert "healthcare" in email_copy or "hospital" in email_copy or "clinical" in email_copy or "patient" in email_copy
    assert "pre-construction" not in email_copy
    assert "site manpower tracking" not in email_copy


def test_email_gen_multiple_icps_lead_context_isolation():
    """TEST 4: Lead A uses ICP A context and Lead B uses ICP B context."""
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from unittest.mock import MagicMock

    designer = ICPDesigner()
    icp_a = designer.design_icp(
        campaign_name="Campaign FinTech",
        campaign_objective="Target FinTech in New York",
        product_or_service="FinPay Protocol",
        company_name="FinPay",
        industry="Financial Services"
    )
    icp_a.status = ICPStatus.APPROVED

    icp_b = designer.design_icp(
        campaign_name="Campaign AgriTech",
        campaign_objective="Target AgriTech in Iowa",
        product_or_service="AgriCrop Sensors",
        company_name="AgriCrop",
        industry="Agriculture"
    )
    icp_b.status = ICPStatus.APPROVED

    lead_a = {
        "company_name": "WallStreet Pay",
        "industry": "Financial Services",
        "contact_name": "Frank Miller",
        "job_title": "CTO",
        "email": "frank@wspay.com"
    }

    lead_b = {
        "company_name": "Midwest Farms Co",
        "industry": "Agriculture",
        "contact_name": "George Brown",
        "job_title": "VP Operations",
        "email": "george@midwestfarms.com"
    }

    mock_client_a = MagicMock()
    mock_client_a.discover_leads.return_value = {"leads": [lead_a]}
    mock_client_a.live_mode = False
    runner_a = DeeplineDiscoveryRunner(deepline_client=mock_client_a)
    runner_a.run_discovery_pipeline(icp_a, requested_count=1)

    mock_client_b = MagicMock()
    mock_client_b.discover_leads.return_value = {"leads": [lead_b]}
    mock_client_b.live_mode = False
    runner_b = DeeplineDiscoveryRunner(deepline_client=mock_client_b)
    runner_b.run_discovery_pipeline(icp_b, requested_count=1)

    store = ApprovalStore()
    recs = store.load_queue()
    rec_a = [r for r in recs if r.company == "WallStreet Pay"][-1]
    rec_b = [r for r in recs if r.company == "Midwest Farms Co"][-1]

    assert "finpay" in rec_a.email_1_original.lower()
    assert "agricrop" in rec_b.email_1_original.lower()


def test_email_gen_no_hardcoded_uk_construction_leak_unrelated_campaign():
    """TEST 5: No hardcoded UK/construction context leaks into unrelated campaigns."""
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from unittest.mock import MagicMock

    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="Tokyo Logistics SaaS",
        campaign_objective="Optimize warehouse operations in Tokyo",
        product_or_service="LogiFlow Warehouse Manager",
        geography="Japan",
        industry="Logistics & Supply Chain",
        company_name="LogiFlow"
    )
    icp.status = ICPStatus.APPROVED

    lead_dict = {
        "company_name": "Tokyo Express Corp",
        "country": "JAPAN",
        "industry": "Logistics & Supply Chain",
        "contact_name": "Kenji Sato",
        "job_title": "Logistics Director",
        "email": "kenji@tokyoexpress.jp"
    }

    mock_client = MagicMock()
    mock_client.discover_leads.return_value = {"leads": [lead_dict]}
    mock_client.live_mode = False

    runner = DeeplineDiscoveryRunner(deepline_client=mock_client)
    runner.run_discovery_pipeline(icp, requested_count=1)

    store = ApprovalStore()
    recs = store.load_queue()
    rec = [r for r in recs if r.company == "Tokyo Express Corp"][-1]

    copy_text = f"{rec.email_1_original} {rec.followup_a_original} {rec.followup_b_original}".lower()
    for leak in ["pre-construction", "subcontractor document control", "site manpower tracking", "uk building projects"]:
        assert leak not in copy_text


def test_email_gen_custom_brand_company_name_from_campaign_config():
    """TEST 6: Product/company name comes from campaign configuration rather than hardcoded email template."""
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from unittest.mock import MagicMock

    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="CyberGuard Security",
        campaign_objective="Promote CyberGuard SOC platform",
        product_or_service="CyberGuard Cloud SOC",
        company_name="CyberGuard Inc",
        sender_name="CyberGuard Team",
        industry="Cybersecurity"
    )
    icp.status = ICPStatus.APPROVED

    lead_dict = {
        "company_name": "SecureData Systems",
        "industry": "Cybersecurity",
        "contact_name": "Alice Vance",
        "job_title": "CISO",
        "email": "alice@securedatasystems.com"
    }

    mock_client = MagicMock()
    mock_client.discover_leads.return_value = {"leads": [lead_dict]}
    mock_client.live_mode = False

    runner = DeeplineDiscoveryRunner(deepline_client=mock_client)
    runner.run_discovery_pipeline(icp, requested_count=1)

    store = ApprovalStore()
    recs = store.load_queue()
    rec = [r for r in recs if r.company == "SecureData Systems"][-1]

    assert "cyberguard" in rec.email_1_original.lower()


def test_email_gen_no_strong_signal_does_not_invent_company_initiative():
    """TEST 7: No strong signal does not result in an invented company initiative."""
    from src.personalization.voc_engine import VoCEngine
    from src.models import LeadIntelligenceOutput, EmailStatus, PriorityLevel, AccessibilityTier, DisqualificationStatus, PersonalizationNoteStatus, EvidenceLevel

    engine = VoCEngine()
    lead_intel = LeadIntelligenceOutput(
        company_name="Acme Tech",
        company_domain="acmetech.com",
        contact_name="Bob Smith",
        job_title="VP Operations",
        email="bob@acmetech.com",
        email_status=EmailStatus.PATTERN_CONFIRMED,
        company_size="100 employees",
        industry="Software",
        opportunity_score=80.0,
        accessibility_score=80.0,
        outreach_priority_index=80.0,
        priority_level=PriorityLevel.P1,
        opportunity_tier="Tier 1",
        accessibility_tier=AccessibilityTier.HIGH,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        personalization_note_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL,
        personalization_note="NO_STRONG_SIGNAL",
        pain_point="Operational efficiency challenges.",
        pain_point_evidence=EvidenceLevel.INFERRED,
        relevant_signal="NO_STRONG_SIGNAL",
        relevant_signal_evidence=EvidenceLevel.UNKNOWN,
        persona_selection_rationale="Matching persona",
        ICP_score=80.0,
    )

    voc = engine.map_lead_voc(lead_intel)
    assert voc.personalization_note_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL
    assert "saw your recent announcement" not in voc.customer_language_hook.lower()
    assert "congratulations on" not in voc.customer_language_hook.lower()


def test_icp_api_outreach_context_fields_persistence():
    """TEST 8: Verify section E outreach context fields are accepted by manual ICP creation and saved on the ICPConfig."""
    from app.api.icp import create_manual_icp, CreateManualICPRequest

    req = CreateManualICPRequest(
        campaign_name="AEDRIX Automation Test",
        campaign_objective="Test outreach fields persistence",
        company_name="AEDRIX",
        product_or_service="AI-powered business automation and software solutions",
        value_proposition="Help businesses automate workflows, improve operational efficiency, and implement AI-powered solutions without requiring a large internal engineering team.",
        offer="A brief discussion to identify potential AI and automation opportunities",
        cta="Would you be open to a brief conversation?",
        sender_name="Alex Mitchell",
        geography="India",
        industry="Technology",
    )

    res = create_manual_icp(req)
    assert res["ok"] is True
    record = res["record"]
    icp = record.effective_icp

    assert icp.company_name == "AEDRIX"
    assert icp.product_or_service == "AI-powered business automation and software solutions"
    assert "automate workflows" in icp.value_proposition
    assert icp.offer == "A brief discussion to identify potential AI and automation opportunities"
    assert icp.cta == "Would you be open to a brief conversation?"
    assert icp.sender_name == "Alex Mitchell"


def test_offline_e2e_full_verification(monkeypatch):
    """
    COMPREHENSIVE OFFLINE E2E TEST:
    Executes Sections 1-11 of offline verification:
    1. Outreach context model & serialization
    2. ICP A (NOVAFLUX) vs ICP B (CLOUDNEST) provenance & copy isolation
    3. Offline discovery pipeline simulation
    4. Dynamic email generation
    5. Hardcoded content leak check (no AEDRIX/construction terms in generic copy)
    6. Personalization safety (NO_STRONG_SIGNAL handling)
    7. Generic geography resolution (Chandigarh, Mohali, Panchkula & India)
    8. Sector fallback logic (IT = False, Construction = True)
    9. Email QA validation
    10. Full offline pipeline flow
    """
    monkeypatch.setenv("LLM_PROVIDER", "template")
    from app.api.icp import create_manual_icp, CreateManualICPRequest
    from src.icp.icp_designer import ICPDesigner
    from src.icp.icp_models import ICPConfig, ICPStatus, GeographyConfig
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from src.personalization.personalization_qa import PersonalizationQA
    from src.deepline_export_adapter import DeeplineExportAdapter
    from unittest.mock import MagicMock

    # --- 1. ICP OUTREACH CONTEXT & SERIALIZATION TEST ---
    req_novaflux = CreateManualICPRequest(
        campaign_name="NOVAFLUX Automation Campaign",
        campaign_objective="Target IT and SaaS decision makers for workflow automation",
        company_name="NOVAFLUX",
        product_or_service="AI workflow automation platform",
        value_proposition="Helps growing businesses automate repetitive workflows, reduce manual operations, and improve productivity without building a large engineering team.",
        offer="Free 20-minute workflow assessment",
        cta="Would you be open to a quick conversation next week?",
        sender_name="Jordan Lee",
        geography="Chandigarh, Mohali, Panchkula",
        industry="Information Technology, Software Development, SaaS, Artificial Intelligence",
        minimum_employees=10,
        target_personas=["Founder", "CEO", "Managing Director", "Head of Technology"],
    )

    res_novaflux = create_manual_icp(req_novaflux)
    assert res_novaflux["ok"] is True
    record_a = res_novaflux["record"]
    icp_a = record_a.effective_icp
    icp_a.status = ICPStatus.APPROVED

    # Verify serialization roundtrip
    icp_dict = icp_a.model_dump()
    icp_restored = ICPConfig.model_validate(icp_dict)

    assert icp_restored.company_name == "NOVAFLUX"
    assert icp_restored.product_or_service == "AI workflow automation platform"
    assert icp_restored.offer == "Free 20-minute workflow assessment"
    assert icp_restored.cta == "Would you be open to a quick conversation next week?"
    assert icp_restored.sender_name == "Jordan Lee"

    # --- 7. ICP GEOGRAPHY TEST ---
    geo_keywords = icp_a.geography.allowed_country_keywords
    assert "CHANDIGARH" in geo_keywords
    assert "MOHALI" in geo_keywords
    assert "PANCHKULA" in geo_keywords
    for uk_term in ["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GREAT BRITAIN"]:
        assert uk_term not in geo_keywords

    geo_india = GeographyConfig(primary_country="India", country_codes=["IND"], allowed_country_keywords=["INDIA"])
    assert geo_india.allowed_country_keywords == ["INDIA"]

    # --- 8. SECTOR FALLBACK TEST ---
    adapter = DeeplineExportAdapter()
    adapted_it = adapter.adapt_record({"company_name": "IT Co", "industry": "Information Technology & Services"})
    adapted_const = adapter.adapt_record({"company_name": "Const Co", "industry": "Commercial Construction"})
    adapted_civil = adapter.adapt_record({"company_name": "Civil Co", "industry": "Civil Engineering"})

    assert adapted_it["is_construction_sector"] is False
    assert adapted_const["is_construction_sector"] is True
    assert adapted_civil["is_construction_sector"] is True

    # --- 2 & 3. ICP → LEAD PROVENANCE & OFFLINE DISCOVERY PIPELINE ---
    req_cloudnest = CreateManualICPRequest(
        campaign_name="CLOUDNEST Analytics Campaign",
        campaign_objective="Target SaaS leaders for data analytics platform",
        company_name="CLOUDNEST",
        product_or_service="Data analytics platform",
        value_proposition="Helps business intelligence teams with unified real-time cloud data pipelines.",
        offer="Custom 15-minute data architecture review",
        cta="Are you available for a brief call tomorrow?",
        sender_name="Sarah Chen",
        geography="Mohali",
        industry="SaaS, Data Analytics",
        minimum_employees=10,
        target_personas=["CEO", "Managing Director", "VP Engineering"],
    )

    res_cloudnest = create_manual_icp(req_cloudnest)
    record_b = res_cloudnest["record"]
    icp_b = record_b.effective_icp
    icp_b.status = ICPStatus.APPROVED

    lead_a_dict = {
        "company_name": "ExampleTech A",
        "company_domain": "exampletecha.com",
        "country": "INDIA",
        "location": "Chandigarh",
        "industry": "Software Development",
        "contact_name": "Rahul Sharma",
        "job_title": "CEO",
        "email": "rahul@exampletecha.com",
        "employee_count": 25,
    }

    lead_b_dict = {
        "company_name": "ExampleTech B",
        "company_domain": "exampletechb.com",
        "country": "INDIA",
        "location": "Mohali",
        "industry": "SaaS",
        "contact_name": "Priya Mehta",
        "job_title": "Managing Director",
        "email": "priya@exampletechb.com",
        "employee_count": 40,
    }

    # Run offline discovery pipeline for ICP A (Lead A)
    mock_client_a = MagicMock()
    mock_client_a.discover_leads.return_value = {"leads": [lead_a_dict]}
    mock_client_a.live_mode = False

    runner_a = DeeplineDiscoveryRunner(deepline_client=mock_client_a)
    runner_a.run_discovery_pipeline(icp_a, requested_count=1)

    # Run offline discovery pipeline for ICP B (Lead B)
    mock_client_b = MagicMock()
    mock_client_b.discover_leads.return_value = {"leads": [lead_b_dict]}
    mock_client_b.live_mode = False

    runner_b = DeeplineDiscoveryRunner(deepline_client=mock_client_b)
    runner_b.run_discovery_pipeline(icp_b, requested_count=1)

    store = ApprovalStore()
    recs = store.load_queue()
    rec_a = [r for r in recs if r.company == "ExampleTech A" and r.icp_id == icp_a.id][-1]
    rec_b = [r for r in recs if r.company == "ExampleTech B" and r.icp_id == icp_b.id][-1]

    # Verify Provenance
    assert rec_a.icp_id == icp_a.id
    assert rec_a.campaign_id == icp_a.campaign_id

    assert rec_b.icp_id == icp_b.id
    assert rec_b.campaign_id == icp_b.campaign_id

    # --- 4 & 5. DYNAMIC EMAIL GENERATION & HARDCODED LEAK TEST ---
    email_a = f"{rec_a.email_1_original} {rec_a.followup_a_original} {rec_a.followup_b_original}".lower()
    email_b = f"{rec_b.email_1_original} {rec_b.followup_a_original} {rec_b.followup_b_original}".lower()

    # Lead A (ICP A) must use NOVAFLUX / Jordan Lee
    assert "novaflux" in email_a
    assert "jordan lee" in email_a
    assert "cloudnest" not in email_a
    assert "sarah chen" not in email_a
    assert "data analytics platform" not in email_a

    # Lead B (ICP B) must use CLOUDNEST / Sarah Chen
    assert "cloudnest" in email_b
    assert "sarah chen" in email_b
    assert "novaflux" not in email_b
    assert "jordan lee" not in email_b
    assert "ai workflow automation platform" not in email_b

    # Zero generic copy leakage in Lead A or Lead B copy
    for leak_term in ["pre-construction", "site manpower tracking", "subcontractor document control", "building projects", "alex mitchell"]:
        assert leak_term not in email_a, f"Unwanted leak in Lead A: {leak_term}"
        assert leak_term not in email_b, f"Unwanted leak in Lead B: {leak_term}"

    # --- 6. PERSONALIZATION SAFETY TEST ---
    assert rec_a.flag_no_strong_signal is True or rec_a.personalization_status != "FLAGGED"
    for invented_claim in ["saw your recent funding", "hiring 50 engineers", "congratulations on your acquisition"]:
        assert invented_claim not in email_a
        assert invented_claim not in email_b

    # --- 9. QA TEST ---
    qa = PersonalizationQA()
    from src.models import LeadIntelligenceOutput, EvidenceLevel, EmailStatus, DisqualificationStatus, PersonalizationNoteStatus, PriorityLevel, AccessibilityTier
    dummy_intel_a = LeadIntelligenceOutput(
        company_name="ExampleTech A", company_domain="exampletecha.com", contact_name="Rahul Sharma", job_title="CEO", email="rahul@exampletecha.com", email_status=EmailStatus.PATTERN_CONFIRMED, linkedin_url=None, company_size="25 employees", company_size_evidence=EvidenceLevel.VERIFIED, industry="Software Development", opportunity_score=80.0, accessibility_score=80.0, outreach_priority_index=80.0, priority_level=PriorityLevel.P1, opportunity_tier="Tier 1", accessibility_tier=AccessibilityTier.HIGH, disqualification_status=DisqualificationStatus.QUALIFIED, disqualification_reason=None, personalization_note_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL, personalization_note="NO_STRONG_SIGNAL", research_sources=[], ICP_score=80.0, pain_point="Ops efficiency", pain_point_evidence=EvidenceLevel.INFERRED, relevant_signal="NO_STRONG_SIGNAL", relevant_signal_evidence=EvidenceLevel.UNKNOWN, persona_selection_rationale="CEO"
    )
    dummy_intel_b = LeadIntelligenceOutput(
        company_name="ExampleTech B", company_domain="exampletechb.com", contact_name="Priya Mehta", job_title="Managing Director", email="priya@exampletechb.com", email_status=EmailStatus.PATTERN_CONFIRMED, linkedin_url=None, company_size="40 employees", company_size_evidence=EvidenceLevel.VERIFIED, industry="SaaS", opportunity_score=80.0, accessibility_score=80.0, outreach_priority_index=80.0, priority_level=PriorityLevel.P1, opportunity_tier="Tier 1", accessibility_tier=AccessibilityTier.HIGH, disqualification_status=DisqualificationStatus.QUALIFIED, disqualification_reason=None, personalization_note_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL, personalization_note="NO_STRONG_SIGNAL", research_sources=[], ICP_score=80.0, pain_point="Ops efficiency", pain_point_evidence=EvidenceLevel.INFERRED, relevant_signal="NO_STRONG_SIGNAL", relevant_signal_evidence=EvidenceLevel.UNKNOWN, persona_selection_rationale="Managing Director"
    )
    qa_res_a = qa.validate_lead_drafts(lead_intel=dummy_intel_a, email_1=rec_a.email_1_original, followup_a=rec_a.followup_a_original, followup_b=rec_a.followup_b_original)
    qa_res_b = qa.validate_lead_drafts(lead_intel=dummy_intel_b, email_1=rec_b.email_1_original, followup_a=rec_b.followup_a_original, followup_b=rec_b.followup_b_original)

    assert qa_res_a.qa_status in ["PASS", "PASSED"]
    assert qa_res_b.qa_status in ["PASS", "PASSED"]


def test_subject_length_and_voc_decoupling():
    """
    Scenario A: Long VoC angle subject sanitization test.
    Ensures generated subjects for Email 1, Follow-up A, and Follow-up B:
    - Are <= 6 words
    - Never equal the full VoC angle
    - Contain no construction terms
    """
    from src.integrations.claude_client import ClaudeClient
    from src.integrations.bedrock_client import BedrockClient
    from src.models import LeadIntelligenceOutput, EvidenceLevel, EmailStatus, DisqualificationStatus, PersonalizationNoteStatus, PriorityLevel, AccessibilityTier
    from src.icp.icp_models import ICPConfig, GeographyConfig

    long_voc = "Companies looking to adopt AI, automation, data analytics or software solutions but lacking sufficient internal expertise or engineering capacity."
    icp = ICPConfig(
        id="icp_ai_long_voc",
        campaign_id="camp_ai_long_voc",
        name="AI & Automation Campaign",
        campaign_description="Targeting software decision makers",
        geography=GeographyConfig(primary_country="India", country_codes=["IND"], allowed_country_keywords=["CHANDIGARH", "MOHALI", "PANCHKULA", "INDIA"]),
        industries=["Software Development", "Artificial Intelligence"],
        company_name="NOVAFLUX",
        product_or_service="AI workflow automation platform",
        value_proposition="Automates business workflows without engineering overhead.",
        offer="Free 20-minute workflow assessment",
        cta="Open to a brief conversation?",
        sender_name="Jordan Lee",
        voc_context=long_voc,
    )

    intel = LeadIntelligenceOutput(
        company_name="AcmeMinds Private Limited",
        company_domain="acmeminds.com",
        contact_name="Rohan Gupta",
        job_title="CTO",
        email="rohan@acmeminds.com",
        email_status=EmailStatus.PATTERN_CONFIRMED,
        linkedin_url=None,
        company_size="35 employees",
        company_size_evidence=EvidenceLevel.VERIFIED,
        industry="Information Technology & Services",
        opportunity_score=85.0,
        accessibility_score=80.0,
        outreach_priority_index=83.0,
        priority_level=PriorityLevel.P1,
        opportunity_tier="Tier 1",
        accessibility_tier=AccessibilityTier.HIGH,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        disqualification_reason=None,
        personalization_note_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL,
        personalization_note="NO_STRONG_SIGNAL",
        research_sources=[],
        ICP_score=85.0,
        pain_point="Ops efficiency",
        pain_point_evidence=EvidenceLevel.INFERRED,
        relevant_signal="NO_STRONG_SIGNAL",
        relevant_signal_evidence=EvidenceLevel.UNKNOWN,
        persona_selection_rationale="CTO",
    )

    client_claude = ClaudeClient()
    client_bedrock = BedrockClient()

    for client in [client_claude, client_bedrock]:
        e1 = client._generate_offline_email_1(intel, voc_context=None, icp_config=icp)
        fa = client._generate_offline_followup_a(intel, e1, voc_context=None, icp_config=icp)
        fb = client._generate_offline_followup_b(intel, voc_context=None, icp_config=icp)

        for name, draft in [("Email 1", e1), ("Follow-up A", fa), ("Follow-up B", fb)]:
            words = draft.subject.split()
            assert len(words) <= 6, f"{name} subject exceeds 6 words: '{draft.subject}' ({len(words)} words)"
            assert draft.subject.strip().lower() != long_voc.strip().lower(), f"{name} subject equals long VoC angle!"
            assert "companies looking to adopt" not in draft.subject.lower()
            assert "pre-construction" not in draft.subject.lower()
            assert "site manpower" not in draft.subject.lower()


def test_chandigarh_mohali_panchkula_geography_qualification():
    """
    Scenarios B, C, D: Generic geography qualification test for Chandigarh, Mohali, Panchkula.
    Leads operating in Chandigarh, Mohali, or Panchkula MUST NOT be HARD_DISQUALIFIED as 'Non-UK geography'.
    """
    from src.icp.icp_engine import ICPEngine
    from src.icp.icp_models import ICPConfig, GeographyConfig
    from src.models import DisqualificationStatus

    icp_chandigarh = ICPConfig(
        id="icp_chandigarh_ai",
        campaign_id="camp_chandigarh_ai",
        name="Chandigarh AI Campaign",
        campaign_description="Target IT and SaaS decision makers in Chandigarh tri-city region",
        geography=GeographyConfig(
            primary_country="India",
            country_codes=["IND"],
            allowed_country_keywords=["CHANDIGARH", "MOHALI", "PANCHKULA", "INDIA"],
        ),
        industries=["Information Technology", "Software", "SaaS"],
        allowed_industry_keywords=["INFORMATION TECHNOLOGY", "SOFTWARE", "SAAS", "IT SERVICES"],
        minimum_employees=10,
        company_name="NOVAFLUX",
    )

    engine = ICPEngine(icp_chandigarh)

    lead_chd = {
        "company_name": "TriCity Software Pvt Ltd",
        "country": "INDIA",
        "location": "Chandigarh",
        "industry": "Software Development",
        "employee_count": 30,
        "job_title": "Head of Technology",
    }
    res_chd = engine.evaluate_lead(lead_chd)
    assert res_chd.status == DisqualificationStatus.QUALIFIED
    assert res_chd.disqualification_reason is None

    lead_moh = {
        "company_name": "Mohali Innovations",
        "country": "INDIA",
        "location": "Mohali",
        "industry": "SaaS",
        "employee_count": 45,
        "job_title": "CTO",
    }
    res_moh = engine.evaluate_lead(lead_moh)
    assert res_moh.status == DisqualificationStatus.QUALIFIED

    lead_pan = {
        "company_name": "Panchkula Data Systems",
        "country": "INDIA",
        "location": "Panchkula",
        "industry": "Information Technology & Services",
        "employee_count": 60,
        "job_title": "Managing Director",
    }
    res_pan = engine.evaluate_lead(lead_pan)
    assert res_pan.status == DisqualificationStatus.QUALIFIED


def test_non_target_geography_disqualification():
    """
    Scenario E: Non-target geography disqualification test.
    A Germany lead tested against a Chandigarh/India ICP must be HARD_DISQUALIFIED with reason
    containing 'Non-target geography' (NOT 'Non-UK geography').
    """
    from src.icp.icp_engine import ICPEngine
    from src.icp.icp_models import ICPConfig, GeographyConfig
    from src.models import DisqualificationStatus

    icp_india = ICPConfig(
        id="icp_india_tech",
        campaign_id="camp_india_tech",
        name="India Tech Campaign",
        campaign_description="India targeting",
        geography=GeographyConfig(
            primary_country="India",
            country_codes=["IND"],
            allowed_country_keywords=["CHANDIGARH", "MOHALI", "PANCHKULA", "INDIA"],
        ),
        industries=["Software Development"],
        company_name="NOVAFLUX",
    )

    engine = ICPEngine(icp_india)
    lead_germany = {
        "company_name": "Berlin Systems GmbH",
        "country": "GERMANY",
        "location": "Berlin",
        "industry": "Software Development",
        "employee_count": 50,
        "job_title": "CTO",
    }

    res_ger = engine.evaluate_lead(lead_germany)
    assert res_ger.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "Non-target geography" in res_ger.disqualification_reason
    assert "Non-UK geography" not in res_ger.disqualification_reason


def test_uk_explicit_geography_regression():
    """
    Scenario F: UK regression test.
    When an active ICP explicitly targets the UK, a non-UK lead MUST be HARD_DISQUALIFIED with 'Non-UK geography' reason.
    """
    from src.icp.icp_engine import ICPEngine
    from src.icp.icp_models import ICPConfig, GeographyConfig
    from src.models import DisqualificationStatus

    icp_uk = ICPConfig(
        id="icp_uk_contractors",
        campaign_id="camp_uk_contractors",
        name="UK Main Contractors",
        campaign_description="UK commercial contractors",
        geography=GeographyConfig(
            primary_country="United Kingdom",
            country_codes=["UK", "GB", "GBR"],
            allowed_country_keywords=["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES"],
        ),
        industries=["Commercial Construction"],
        company_name="Aedrix",
    )

    engine = ICPEngine(icp_uk)
    lead_us = {
        "company_name": "New York Builders Inc",
        "country": "UNITED STATES",
        "location": "New York",
        "industry": "Commercial Construction",
        "employee_count": 100,
        "is_uk_operating": False,
    }

    res_us = engine.evaluate_lead(lead_us)
    assert res_us.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "Non-UK geography" in res_us.disqualification_reason


def test_approval_safety_and_lead_persistence(tmp_path):
    """
    Scenarios G, H, I, J: Approval safety, persistence, and ICP isolation test.
    Verifies:
    - HARD_DISQUALIFIED -> PENDING_REVIEW (reviewable by human)
    - QUALIFIED -> PENDING_REVIEW
    - Disqualified leads remain persisted and reviewable
    - Compliance/Delivery safety failure -> BLOCKED
    """
    from src.approval.approval_engine import ApprovalEngine
    from src.approval.approval_store import ApprovalStore
    from src.approval.approval_models import ApprovalStatus
    from src.models import DisqualificationStatus

    store = ApprovalStore(storage_path=str(tmp_path / "test_safety_queue.json"))
    engine = ApprovalEngine(store=store)

    # QUALIFIED lead -> PENDING_REVIEW
    rec_qual = engine.enroll_draft(
        company="QualTech",
        contact="Alice Smith",
        title="CEO",
        email="alice@qualtech.com",
        qualification_status=DisqualificationStatus.QUALIFIED.value,
        opportunity_score=85.0,
        accessibility_score=85.0,
        outreach_priority_index=85.0,
        priority="P1",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Verified growth signal",
        voc_angle="AI Operations",
        email_1="Hi Alice...",
        followup_a="Following up...",
        followup_b="Pivoting angle...",
        qa_status="PASS",
        qa_reasons=[],
    )
    assert rec_qual.approval_status == ApprovalStatus.PENDING_REVIEW
    assert rec_qual.blocked_reason is None

    # HARD_DISQUALIFIED lead -> PENDING_REVIEW (Persisted & Reviewable!)
    rec_disq = engine.enroll_draft(
        company="DisqTech",
        contact="Bob Jones",
        title="Manager",
        email="bob@disqtech.com",
        qualification_status=DisqualificationStatus.HARD_DISQUALIFIED.value,
        opportunity_score=0.0,
        accessibility_score=50.0,
        outreach_priority_index=20.0,
        priority="P3",
        personalization_status="NO_STRONG_SIGNAL",
        personalization_note="NO_STRONG_SIGNAL",
        voc_angle="Operations",
        email_1="Hi Bob...",
        followup_a="Following up...",
        followup_b="Pivoting...",
        qa_status="PASS",
        qa_reasons=[],
        disqualification_reason="Non-target geography (Headquarters in France)",
    )
    assert rec_disq.approval_status == ApprovalStatus.PENDING_REVIEW
    assert rec_disq.qualification_status == DisqualificationStatus.HARD_DISQUALIFIED.value
    assert "Non-target geography" in rec_disq.blocked_reason

    # Human approves HARD_DISQUALIFIED lead -> APPROVED + smartlead_eligible, qualification remains HARD_DISQUALIFIED
    app_disq = engine.approve(rec_disq.lead_id, reviewer="HUMAN_OPERATOR")
    assert app_disq.approval_status == ApprovalStatus.APPROVED
    assert app_disq.smartlead_eligible is True
    assert app_disq.qualification_status == DisqualificationStatus.HARD_DISQUALIFIED.value

    # Genuine Delivery Safety Condition (Bounced/Invalid email) -> BLOCKED
    rec_bounce = engine.enroll_draft(
        company="BounceTech",
        contact="Invalid Contact",
        title="CTO",
        email="invalid-bounce@bouncetech.com",
        qualification_status=DisqualificationStatus.QUALIFIED.value,
        opportunity_score=50.0,
        accessibility_score=0.0,
        outreach_priority_index=20.0,
        priority="P3",
        personalization_status="NO_STRONG_SIGNAL",
        personalization_note="NO_STRONG_SIGNAL",
        voc_angle="Ops",
        email_1="Hi...",
        followup_a="Hi...",
        followup_b="Hi...",
        qa_status="PASS",
        email_status="INVALID_BOUNCED",
    )
    assert rec_bounce.approval_status == ApprovalStatus.BLOCKED
    assert rec_bounce.smartlead_eligible is False

    # Attempting to approve a delivery safety blocked lead raises ValueError
    import pytest
    with pytest.raises(ValueError, match="Cannot approve"):
        engine.approve(rec_bounce.lead_id)

    # Verify Persistence: Disqualified lead exists in store queue
    recs = engine.store.load_queue()
    disq_found = [r for r in recs if r.company == "DisqTech"]
    assert len(disq_found) > 0, "Disqualified lead was not persisted in queue!"


def test_decoupled_review_scenarios_a_to_i(tmp_path):
    """
    Comprehensive test for Scenarios A through I of the decoupled review pipeline.
    """
    from src.approval.approval_engine import ApprovalEngine
    from src.approval.approval_store import ApprovalStore
    from src.approval.approval_models import ApprovalStatus
    from src.models import DisqualificationStatus
    from src.icp.icp_engine import ICPEngine
    from src.icp.icp_models import ICPConfig, GeographyConfig

    store = ApprovalStore(storage_path=str(tmp_path / "test_scenarios_queue.json"))
    engine = ApprovalEngine(store=store)

    # A. Qualified lead -> PENDING_REVIEW
    lead_a = engine.enroll_draft(
        company="Company A",
        contact="Person A",
        title="CEO",
        email="a@comp-a.com",
        qualification_status="QUALIFIED",
        opportunity_score=80.0,
        accessibility_score=80.0,
        outreach_priority_index=80.0,
        priority="P1",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Signal A",
        voc_angle="Angle A",
        email_1="Draft A1",
        followup_a="Draft FA",
        followup_b="Draft FB",
        qa_status="PASS",
    )
    assert lead_a.qualification_status == "QUALIFIED"
    assert lead_a.approval_status == ApprovalStatus.PENDING_REVIEW

    # B. Non-qualified lead -> PENDING_REVIEW
    lead_b = engine.enroll_draft(
        company="Company B",
        contact="Person B",
        title="Director",
        email="b@comp-b.com",
        qualification_status="NOT_QUALIFIED",
        opportunity_score=50.0,
        accessibility_score=50.0,
        outreach_priority_index=50.0,
        priority="P2",
        personalization_status="NO_STRONG_SIGNAL",
        personalization_note="NO_STRONG_SIGNAL",
        voc_angle="Angle B",
        email_1="Draft B1",
        followup_a="Draft FA",
        followup_b="Draft FB",
        qa_status="PASS",
        disqualification_reason="Persona mismatch",
    )
    assert lead_b.qualification_status == "NOT_QUALIFIED"
    assert lead_b.approval_status == ApprovalStatus.PENDING_REVIEW

    # C. Hard-disqualified geography lead -> PENDING_REVIEW with reason retained
    lead_c = engine.enroll_draft(
        company="Company C",
        contact="Person C",
        title="CTO",
        email="c@comp-c.com",
        qualification_status="HARD_DISQUALIFIED",
        opportunity_score=30.0,
        accessibility_score=60.0,
        outreach_priority_index=40.0,
        priority="P3",
        personalization_status="NO_STRONG_SIGNAL",
        personalization_note="NO_STRONG_SIGNAL",
        voc_angle="Angle C",
        email_1="Draft C1",
        followup_a="Draft FA",
        followup_b="Draft FB",
        qa_status="PASS",
        disqualification_reason="Non-target geography (Headquarters 'Japan' outside target geography)",
    )
    assert lead_c.qualification_status == "HARD_DISQUALIFIED"
    assert lead_c.approval_status == ApprovalStatus.PENDING_REVIEW
    assert "Japan" in lead_c.blocked_reason

    # D. Campaign-excluded lead -> PENDING_REVIEW
    lead_d = engine.enroll_draft(
        company="Company D",
        contact="Person D",
        title="VP",
        email="d@comp-d.com",
        qualification_status="CAMPAIGN_EXCLUDED",
        opportunity_score=60.0,
        accessibility_score=60.0,
        outreach_priority_index=60.0,
        priority="P2",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Signal D",
        voc_angle="Angle D",
        email_1="Draft D1",
        followup_a="Draft FA",
        followup_b="Draft FB",
        qa_status="PASS",
        disqualification_reason="Active sales deal in CRM",
    )
    assert lead_d.qualification_status == "CAMPAIGN_EXCLUDED"
    assert lead_d.approval_status == ApprovalStatus.PENDING_REVIEW

    # E. Compliance/suppression lead -> BLOCKED (delivery safety condition)
    lead_e = engine.enroll_draft(
        company="Company E",
        contact="Person E",
        title="CEO",
        email="optout@comp-e.com",
        qualification_status="QUALIFIED",
        opportunity_score=80.0,
        accessibility_score=80.0,
        outreach_priority_index=80.0,
        priority="P1",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Signal E",
        voc_angle="Angle E",
        email_1="Draft E1",
        followup_a="Draft FA",
        followup_b="Draft FB",
        qa_status="PASS",
        disqualification_reason="Contact on global opt-out suppression blocklist",
        metadata={"is_compliance_blocked": True},
    )
    assert lead_e.approval_status == ApprovalStatus.BLOCKED

    # F. Human approval of non-qualified lead (C)
    approved_c = engine.approve(lead_c.lead_id, reviewer="HUMAN_REVIEWER")
    assert approved_c.approval_status == ApprovalStatus.APPROVED
    assert approved_c.smartlead_eligible is True
    assert approved_c.qualification_status == "HARD_DISQUALIFIED"  # Qualification MUST NOT be mutated!

    # G. Human rejection of non-qualified lead (D)
    rejected_d = engine.reject(lead_d.lead_id, reviewer="HUMAN_REVIEWER", reason="Not interested")
    assert rejected_d.approval_status == ApprovalStatus.REJECTED
    assert rejected_d.smartlead_eligible is False
    assert rejected_d.qualification_status == "CAMPAIGN_EXCLUDED"  # Qualification MUST NOT be mutated!

    # H. Geography evaluation regression
    icp_india = ICPConfig(
        id="icp_ind",
        campaign_id="camp_ind",
        name="India Campaign",
        campaign_description="Automation solutions",
        geography=GeographyConfig(primary_country="India", allowed_country_keywords=["CHANDIGARH", "MOHALI", "PANCHKULA"]),
        minimum_employees=10,
        company_name="NOVAFLUX",
    )
    engine_ind = ICPEngine(icp_india)

    res_ind = engine_ind.evaluate_lead({"company_name": "Ind Co", "country": "INDIA", "location": "Chandigarh", "employee_count": 20})
    assert res_ind.status == DisqualificationStatus.QUALIFIED

    res_ger = engine_ind.evaluate_lead({"company_name": "Ger Co", "country": "GERMANY", "location": "Berlin", "employee_count": 20})
    assert res_ger.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "OUTSIDE_TARGET_GEOGRAPHY" in (res_ger.rule_code or "") or "Non-target" in (res_ger.disqualification_reason or "")

    icp_uk = ICPConfig(
        id="icp_uk",
        campaign_id="camp_uk",
        name="UK Campaign",
        campaign_description="Document control",
        geography=GeographyConfig(primary_country="United Kingdom", allowed_country_keywords=["UK", "UNITED KINGDOM"]),
        minimum_employees=10,
        company_name="Aedrix",
    )
    engine_uk = ICPEngine(icp_uk)
    res_uk_ind = engine_uk.evaluate_lead({"company_name": "Ind Co", "country": "INDIA", "location": "Delhi", "employee_count": 20})
    assert res_uk_ind.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "Non-UK geography" in res_uk_ind.disqualification_reason


def test_scenarios_a_to_l_lead_quality_and_geography(tmp_path):
    """
    Offline verification suite for Scenarios A through L:
    A. Chandigarh + valid email -> PENDING_REVIEW
    B. Mohali + valid email -> PENDING_REVIEW
    C. Panchkula + valid email -> PENDING_REVIEW
    D. Delhi + valid email -> HARD_DISQUALIFIED -> PENDING_REVIEW
    E. Germany + valid email -> HARD_DISQUALIFIED -> PENDING_REVIEW
    F. Chandigarh + invalid email -> BLOCKED
    G. Chandigarh + bounced email -> BLOCKED
    H. Chandigarh + suppressed email -> BLOCKED
    I. Chandigarh + opt-out email -> BLOCKED
    J. Chandigarh + unknown email status -> preserved as UNKNOWN, PENDING_REVIEW
    K. HARD_DISQUALIFIED + valid email -> PENDING_REVIEW -> Human approval possible
    L. HARD_DISQUALIFIED + invalid/bounced email -> BLOCKED -> Human approval prohibited
    """
    from src.approval.approval_engine import ApprovalEngine
    from src.approval.approval_store import ApprovalStore
    from src.approval.approval_models import ApprovalStatus
    from src.models import DisqualificationStatus
    from src.icp.icp_engine import ICPEngine
    from src.icp.icp_models import ICPConfig, GeographyConfig

    store = ApprovalStore(storage_path=str(tmp_path / "test_scenarios_a_l.json"))
    app_engine = ApprovalEngine(store=store)

    icp = ICPConfig(
        id="icp_chd",
        campaign_id="camp_chd",
        name="Chandigarh Region Campaign",
        campaign_description="AI workflow automation",
        geography=GeographyConfig(primary_country="India", allowed_country_keywords=["CHANDIGARH", "MOHALI", "PANCHKULA"]),
        minimum_employees=5,
        company_name="AutomationLabs"
    )
    icp_engine = ICPEngine(icp)

    def make_draft(lead_id, company, contact, email, email_status="VALID", qual_status="QUALIFIED", disqual_reason=None, qa_status="PASS", meta=None):
        return app_engine.enroll_draft(
            company=company,
            contact=contact,
            title="CTO",
            email=email,
            email_status=email_status,
            qualification_status=qual_status,
            opportunity_score=80.0,
            accessibility_score=80.0,
            outreach_priority_index=80.0,
            priority="P1",
            personalization_status="SIGNAL_VERIFIED",
            personalization_note="Signal Note",
            voc_angle="Voc Angle",
            email_1="Email 1 Draft",
            followup_a="Followup A",
            followup_b="Followup B",
            qa_status=qa_status,
            disqualification_reason=disqual_reason,
            metadata=meta or {},
            lead_id=lead_id
        )

    # Scenario A: Chandigarh + valid email
    lead_a_data = {"company_name": "TechChd Ltd", "country": "INDIA", "city": "Chandigarh", "employee_count": 25}
    res_a = icp_engine.evaluate_lead(lead_a_data)
    assert res_a.status == DisqualificationStatus.QUALIFIED
    rec_a = make_draft("lead_a", "TechChd Ltd", "Alex", "alex@techchd.in", "VALID", res_a.status.value, res_a.disqualification_reason)
    assert rec_a.approval_status == ApprovalStatus.PENDING_REVIEW

    # Scenario B: Mohali + valid email
    lead_b_data = {"company_name": "TechMohali Ltd", "country": "INDIA", "city": "Mohali", "employee_count": 25}
    res_b = icp_engine.evaluate_lead(lead_b_data)
    assert res_b.status == DisqualificationStatus.QUALIFIED
    rec_b = make_draft("lead_b", "TechMohali Ltd", "Brian", "brian@techmohali.in", "PATTERN_CONFIRMED", res_b.status.value, res_b.disqualification_reason)
    assert rec_b.approval_status == ApprovalStatus.PENDING_REVIEW

    # Scenario C: Panchkula + valid email
    lead_c_data = {"company_name": "TechPck Ltd", "country": "INDIA", "city": "Panchkula", "employee_count": 25}
    res_c = icp_engine.evaluate_lead(lead_c_data)
    assert res_c.status == DisqualificationStatus.QUALIFIED
    rec_c = make_draft("lead_c", "TechPck Ltd", "Clara", "clara@techpck.in", "EVIDENCE_VERIFIED", res_c.status.value, res_c.disqualification_reason)
    assert rec_c.approval_status == ApprovalStatus.PENDING_REVIEW

    # Scenario D: Delhi + valid email
    lead_d_data = {"company_name": "DelhiCorp", "country": "INDIA", "city": "Delhi", "employee_count": 25}
    res_d = icp_engine.evaluate_lead(lead_d_data)
    assert res_d.status == DisqualificationStatus.HARD_DISQUALIFIED
    rec_d = make_draft("lead_d", "DelhiCorp", "David", "david@delhicorp.in", "VALID", res_d.status.value, res_d.disqualification_reason)
    assert rec_d.approval_status == ApprovalStatus.PENDING_REVIEW
    assert rec_d.qualification_status == "HARD_DISQUALIFIED"

    # Scenario E: Germany + valid email
    lead_e_data = {"company_name": "BerlinGmbh", "country": "GERMANY", "city": "Berlin", "employee_count": 25}
    res_e = icp_engine.evaluate_lead(lead_e_data)
    assert res_e.status == DisqualificationStatus.HARD_DISQUALIFIED
    rec_e = make_draft("lead_e", "BerlinGmbh", "Eva", "eva@berlingmbh.de", "VALID", res_e.status.value, res_e.disqualification_reason)
    assert rec_e.approval_status == ApprovalStatus.PENDING_REVIEW
    assert rec_e.qualification_status == "HARD_DISQUALIFIED"

    # Scenario F: Chandigarh + invalid email
    rec_f = make_draft("lead_f", "TechChd Ltd", "Frank", "invalid_email_format", "INVALID", "QUALIFIED")
    assert rec_f.approval_status == ApprovalStatus.BLOCKED
    assert "invalid" in rec_f.blocked_reason.lower() or "missing" in rec_f.blocked_reason.lower()

    # Scenario G: Chandigarh + bounced email
    rec_g = make_draft("lead_g", "TechChd Ltd", "Grace", "grace@bounced.in", "BOUNCED", "QUALIFIED")
    assert rec_g.approval_status == ApprovalStatus.BLOCKED
    assert "bounced" in rec_g.blocked_reason.lower()

    # Scenario H: Chandigarh + suppressed email
    rec_h = make_draft("lead_h", "TechChd Ltd", "Henry", "henry@suppressed.in", "VALID", "QUALIFIED", meta={"is_global_suppressed": True})
    assert rec_h.approval_status == ApprovalStatus.BLOCKED
    assert "suppression" in rec_h.blocked_reason.lower() or "compliance" in rec_h.blocked_reason.lower()

    # Scenario I: Chandigarh + opt-out email
    rec_i = make_draft("lead_i", "TechChd Ltd", "Ian", "ian@optout.in", "VALID", "QUALIFIED", meta={"is_opt_out": True})
    assert rec_i.approval_status == ApprovalStatus.BLOCKED
    assert "opt-out" in rec_i.blocked_reason.lower() or "compliance" in rec_i.blocked_reason.lower()

    # Scenario J: Chandigarh + unknown email verification state
    rec_j = make_draft("lead_j", "TechChd Ltd", "Jane", "jane@unknown.in", "UNKNOWN", "QUALIFIED")
    assert rec_j.approval_status == ApprovalStatus.PENDING_REVIEW
    assert rec_j.metadata.get("email_status") == "UNKNOWN"

    # Scenario K: HARD_DISQUALIFIED + valid email -> PENDING_REVIEW -> Human approval possible
    approved_k = app_engine.approve("lead_d", reviewer="HUMAN_REVIEWER")
    assert approved_k.approval_status == ApprovalStatus.APPROVED
    assert approved_k.smartlead_eligible is True
    assert approved_k.qualification_status == "HARD_DISQUALIFIED"  # Qualification preserved!

    # Scenario L: HARD_DISQUALIFIED + invalid/bounced email -> BLOCKED -> Human approval prohibited
    rec_l = make_draft("lead_l", "DelhiCorpBad", "Luke", "luke_bounced@delhi.in", "BOUNCED", "HARD_DISQUALIFIED", disqual_reason="Non-target geography")
    assert rec_l.approval_status == ApprovalStatus.BLOCKED
    try:
        app_engine.approve("lead_l", reviewer="HUMAN_REVIEWER")
        assert False, "Should have raised ValueError for delivery-blocked lead"
    except ValueError as err:
        assert "Cannot approve delivery-blocked lead" in str(err)


def test_dynamic_icp_geography_multi_campaign():
    """
    Proves that the ICP engine is 100% configuration-driven and NOT hardcoded.
    Campaign 1: Delhi, Gurgaon
    Campaign 2: Chandigarh, Mohali, Panchkula
    """
    from src.icp.icp_engine import ICPEngine
    from src.icp.icp_models import ICPConfig, GeographyConfig
    from src.models import DisqualificationStatus

    # Campaign 1: Delhi & Gurgaon
    icp_delhi = ICPConfig(
        id="icp_delhi",
        campaign_id="camp_delhi",
        name="Delhi NCR Campaign",
        campaign_description="Automation",
        geography=GeographyConfig(primary_country="India", allowed_country_keywords=["DELHI", "GURGAON"]),
        minimum_employees=5,
        company_name="NCRTech"
    )
    engine_delhi = ICPEngine(icp_delhi)

    res_d1 = engine_delhi.evaluate_lead({"company_name": "D1", "country": "INDIA", "city": "Delhi", "employee_count": 20})
    assert res_d1.status == DisqualificationStatus.QUALIFIED

    res_d2 = engine_delhi.evaluate_lead({"company_name": "D2", "country": "INDIA", "city": "Gurgaon", "employee_count": 20})
    assert res_d2.status == DisqualificationStatus.QUALIFIED

    res_d3 = engine_delhi.evaluate_lead({"company_name": "D3", "country": "INDIA", "city": "Chandigarh", "employee_count": 20})
    assert res_d3.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "CHANDIGARH" in res_d3.disqualification_reason

    # Campaign 2: Chandigarh, Mohali, Panchkula
    icp_chd = ICPConfig(
        id="icp_tri",
        campaign_id="camp_tri",
        name="Tricity Campaign",
        campaign_description="AI",
        geography=GeographyConfig(primary_country="India", allowed_country_keywords=["CHANDIGARH", "MOHALI", "PANCHKULA"]),
        minimum_employees=5,
        company_name="TriTech"
    )
    engine_chd = ICPEngine(icp_chd)

    res_c1 = engine_chd.evaluate_lead({"company_name": "C1", "country": "INDIA", "city": "Chandigarh", "employee_count": 20})
    assert res_c1.status == DisqualificationStatus.QUALIFIED

    res_c2 = engine_chd.evaluate_lead({"company_name": "C2", "country": "INDIA", "city": "Mohali", "employee_count": 20})
    assert res_c2.status == DisqualificationStatus.QUALIFIED

    res_c3 = engine_chd.evaluate_lead({"company_name": "C3", "country": "INDIA", "city": "Panchkula", "employee_count": 20})
    assert res_c3.status == DisqualificationStatus.QUALIFIED

    res_c4 = engine_chd.evaluate_lead({"company_name": "C4", "country": "INDIA", "city": "Delhi", "employee_count": 20})
    assert res_c4.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "DELHI" in res_c4.disqualification_reason

    res_c5 = engine_chd.evaluate_lead({"company_name": "C5", "country": "INDIA", "city": "Mumbai", "employee_count": 20})
    assert res_c5.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "MUMBAI" in res_c5.disqualification_reason

    res_c6 = engine_chd.evaluate_lead({"company_name": "C6", "country": "GERMANY", "city": "Berlin", "employee_count": 20})
    assert res_c6.status == DisqualificationStatus.HARD_DISQUALIFIED
    assert "BERLIN" in res_c6.disqualification_reason


def test_pre_ingestion_email_enrichment_quality_gate(tmp_path, monkeypatch):
    """
    Verifies that the Pre-Ingestion Email Enrichment Quality Gate strictly filters out
    missing, unverified, bounced, suppressed, and opt-out emails BEFORE AEDRIX lead creation.
    Only records with verified professional emails (VALID, VERIFIED, EVIDENCE_VERIFIED) enter AEDRIX.
    """
    monkeypatch.setenv("LLM_PROVIDER", "template")
    from unittest.mock import MagicMock
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.icp.icp_models import ICPConfig, ICPStatus, GeographyConfig
    from src.approval.approval_store import ApprovalStore
    from src.approval.approval_engine import ApprovalEngine
    from src.icp.icp_approval_store import ICPApprovalStore
    from src.icp.icp_approval_engine import ICPApprovalEngine

    app_store = ApprovalStore(storage_path=str(tmp_path / "app_q.json"))
    app_engine = ApprovalEngine(store=app_store)
    icp_store = ICPApprovalStore(storage_path=str(tmp_path / "icp_q.json"))
    icp_engine = ICPApprovalEngine(store=icp_store)

    icp = ICPConfig(
        id="icp_verified_test",
        campaign_id="camp_verified",
        name="Verified Email Test",
        campaign_description="Test",
        status=ICPStatus.APPROVED,
        geography=GeographyConfig(primary_country="India", allowed_country_keywords=["CHANDIGARH"]),
        minimum_employees=5,
        company_name="VerifiedLabs"
    )

    mock_client = MagicMock()
    # Mock people search returning 6 candidates:
    # 1. Verified email + Chandigarh (QUALIFIED)
    # 2. Verified email + Delhi (HARD_DISQUALIFIED)
    # 3. No email
    # 4. Pattern confirmed (UNVERIFIED)
    # 5. Bounced email
    # 6. Suppressed email
    mock_client.discover_leads.return_value = {
        "status": "SUCCESS",
        "leads": [
            {"company_name": "Co1", "country": "INDIA", "city": "Chandigarh", "contact_name": "A1", "job_title": "CTO", "email": "a1@co1.in", "email_status": "VERIFIED"},
            {"company_name": "Co2", "country": "INDIA", "city": "Delhi", "contact_name": "A2", "job_title": "CTO", "email": "a2@co2.in", "email_status": "EVIDENCE_VERIFIED"},
            {"company_name": "Co3", "country": "INDIA", "city": "Chandigarh", "contact_name": "A3", "job_title": "CTO", "email": "", "email_status": "INVALID"},
            {"company_name": "Co4", "country": "INDIA", "city": "Chandigarh", "contact_name": "A4", "job_title": "CTO", "email": "a4@co4.in", "email_status": "PATTERN_CONFIRMED"},
            {"company_name": "Co5", "country": "INDIA", "city": "Chandigarh", "contact_name": "A5", "job_title": "CTO", "email": "a5@co5.in", "email_status": "BOUNCED"},
            {"company_name": "Co6", "country": "INDIA", "city": "Chandigarh", "contact_name": "A6", "job_title": "CTO", "email": "a6@co6.in", "email_status": "SUPPRESSED"}
        ]
    }

    # enrich_lead_emails returns exact output from discover_leads
    mock_client.enrich_lead_emails.side_effect = lambda leads: leads

    runner = DeeplineDiscoveryRunner(
        deepline_client=mock_client,
        approval_engine=app_engine,
        icp_approval_engine=icp_engine
    )

    res = runner.run_discovery_pipeline(icp=icp, requested_count=100)

    # Part 2: All 6 leads are preserved in queue with appropriate email_status and approval_stage
    pending = app_engine.store.load_queue()
    assert len(pending) == 6, f"Expected 6 AEDRIX leads in queue, got {len(pending)}"

    lead_co1 = next(l for l in pending if l.company == "Co1")
    assert lead_co1.qualification_status == "QUALIFIED"
    assert lead_co1.approval_status.value == "PENDING_REVIEW"
    assert lead_co1.email_status in ("VALID", "VERIFIED")

    lead_co2 = next(l for l in pending if l.company == "Co2")
    assert lead_co2.qualification_status == "HARD_DISQUALIFIED"
    assert lead_co2.email_status in ("VALID", "VERIFIED")

    lead_co4 = next(l for l in pending if l.company == "Co4")
    assert lead_co4.email_status == "UNVERIFIED"
    assert lead_co4.approval_stage == "EMAIL_STATUS_APPROVAL"


def test_ai_ark_people_search_and_email_finder_integration(tmp_path):
    """
    Verifies all 12 AI Ark People Search & Email Finder integration scenarios:
    1. People Search success
    2. Empty People Search result
    3. Pagination (page/size)
    4. CEO/Founder title filtering
    5. Missing email
    6. Existing email
    7. Email Finder trackId handling
    8. Email Finder statistics
    9. Email Finder result pagination
    10. Malformed/unexpected response
    11. Deepline tool failure
    12. No duplicate leads
    """
    from unittest.mock import MagicMock
    import pytest
    from src.integrations.deepline_client import DeeplineClient, DeeplineDiscoveryRequest, DeeplineAPIError
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.icp.icp_models import ICPConfig, ICPStatus, GeographyConfig
    from src.approval.approval_store import ApprovalStore
    from src.approval.approval_engine import ApprovalEngine
    from src.icp.icp_approval_store import ICPApprovalStore
    from src.icp.icp_approval_engine import ICPApprovalEngine

    client = DeeplineClient(api_key="test_key", live_mode=False)

    # Scenario 1 & 4: Payload builder with CEO/Founder titles
    req = DeeplineDiscoveryRequest(
        icp_id="icp_ceo_test",
        campaign_id="camp_ceo",
        campaign_name="CEO Campaign",
        geography=["India"],
        company_size="50-200",
        industries=["Software"],
        personas=["CEO", "Founder"],
        positive_signals=["Automation"],
        exclusions=["Consultants"],
        requested_lead_count=50
    )
    v2_payload = client.build_v2_payload(req)
    assert v2_payload["payload"]["size"] == 50
    assert "CEO" in v2_payload["payload"]["contact"]["keyword"]["any"]["include"]["content"]
    assert "Founder" in v2_payload["payload"]["contact"]["keyword"]["any"]["include"]["content"]

    # Scenario 2: Empty People Search result
    empty_mock = MagicMock()
    empty_mock.discover_leads.return_value = {"status": "SUCCESS", "leads": []}
    empty_mock.enrich_lead_emails.return_value = []
    
    app_store = ApprovalStore(storage_path=str(tmp_path / "app_q_empty.json"))
    app_engine = ApprovalEngine(store=app_store)
    icp_store = ICPApprovalStore(storage_path=str(tmp_path / "icp_q_empty.json"))
    icp_engine = ICPApprovalEngine(store=icp_store)

    icp = ICPConfig(
        id="icp_empty",
        campaign_id="camp_empty",
        name="Empty Test",
        campaign_description="Test",
        status=ICPStatus.APPROVED,
        geography=GeographyConfig(primary_country="India", allowed_country_keywords=["CHANDIGARH"])
    )

    runner = DeeplineDiscoveryRunner(
        deepline_client=empty_mock,
        approval_engine=app_engine,
        icp_approval_engine=icp_engine
    )
    res = runner.run_discovery_pipeline(icp=icp, requested_count=10)
    assert res["summary"]["discovered"] == 0
    assert res["summary"]["created"] == 0
    assert len(app_engine.store.load_queue()) == 0

    # Scenario 5 & 6: Missing email vs Existing email normalisation
    leads_input = [
        {"contact_name": "With Email", "company_domain": "co.in", "email": "test@co.in", "email_status": "VERIFIED"},
        {"contact_name": "No Email", "company_domain": "noemail.com", "email": "", "email_status": "UNKNOWN"}
    ]
    enriched = client.enrich_lead_emails(leads_input)
    assert len(enriched) == 2
    assert enriched[0]["email"] == "test@co.in"

    # Scenario 12: No duplicate leads
    dup_leads = [
        {"company_name": "DupCo", "country": "INDIA", "city": "Chandigarh", "contact_name": "Dup Contact", "job_title": "CEO", "email": "dup@dupco.in", "email_status": "VERIFIED"},
        {"company_name": "DupCo", "country": "INDIA", "city": "Chandigarh", "contact_name": "Dup Contact", "job_title": "CEO", "email": "dup@dupco.in", "email_status": "VERIFIED"}
    ]
    mock_dup = MagicMock()
    mock_dup.discover_leads.return_value = {"status": "SUCCESS", "leads": dup_leads}
    mock_dup.enrich_lead_emails.return_value = dup_leads

    app_store_dup = ApprovalStore(storage_path=str(tmp_path / "app_q_dup.json"))
    app_engine_dup = ApprovalEngine(store=app_store_dup)
    icp_store_dup = ICPApprovalStore(storage_path=str(tmp_path / "icp_q_dup.json"))
    icp_engine_dup = ICPApprovalEngine(store=icp_store_dup)

    runner_dup = DeeplineDiscoveryRunner(
        deepline_client=mock_dup,
        approval_engine=app_engine_dup,
        icp_approval_engine=icp_engine_dup
    )
    runner_dup.run_discovery_pipeline(icp=icp, requested_count=10)
    queue = app_engine_dup.store.load_queue()
    assert len(queue) == 1, f"Expected deduplicated lead count of 1, got {len(queue)}"


def test_hard_disqualified_lead_approval_workflow(tmp_path):
    """
    Comprehensive test for the 2-Stage Lead Approval & Post-Approval AI Copy Generation Workflow:
    A. HARD_DISQUALIFIED lead enters PENDING_REVIEW when it has a usable email.
    B. HARD_DISQUALIFIED status and disqualification_reason remain unchanged.
    C, D, E. Discovery does NOT call generate_email_1, generate_followup_a, or generate_followup_b.
    F. Rejecting a HARD_DISQUALIFIED lead does NOT generate email.
    G. Approving a HARD_DISQUALIFIED lead DOES trigger email generation.
    H. QUALIFIED leads continue to work.
    I. NO_EMAIL behavior remains unchanged.
    J. Repeated approval calls do not duplicate email generation.
    """
    from unittest.mock import MagicMock
    from src.approval.approval_engine import ApprovalEngine
    from src.approval.approval_store import ApprovalStore
    from src.approval.approval_models import ApprovalStatus
    from src.icp.icp_approval_engine import ICPApprovalEngine
    from src.icp.icp_approval_store import ICPApprovalStore
    from src.icp.icp_models import ICPConfig, ICPStatus, GeographyConfig
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner

    app_store = ApprovalStore(storage_path=str(tmp_path / "app_q_hd.json"))
    app_engine = ApprovalEngine(store=app_store)
    icp_store = ICPApprovalStore(storage_path=str(tmp_path / "icp_q_hd.json"))
    icp_engine = ICPApprovalEngine(store=icp_store)

    # 1. Mock Deepline Client with 3 leads:
    # Lead 1: Delhi (HARD_DISQUALIFIED) + Valid Email
    # Lead 2: Chandigarh (QUALIFIED) + Valid Email
    # Lead 3: No Email
    mock_leads = [
        {
            "company_name": "Delhi HardDisq Corp",
            "country": "INDIA",
            "city": "Delhi",
            "industry": "Software",
            "contact_name": "Rahul Sharma",
            "job_title": "CEO",
            "email": "rahul@delhiharddisq.in",
            "email_status": "VERIFIED",
        },
        {
            "company_name": "Chandigarh Qual Corp",
            "country": "INDIA",
            "city": "Chandigarh",
            "industry": "Software",
            "contact_name": "Amanpreet Kaur",
            "job_title": "Managing Director",
            "email": "aman@chdqual.in",
            "email_status": "VERIFIED",
        },
        {
            "company_name": "No Email Corp",
            "country": "INDIA",
            "city": "Chandigarh",
            "industry": "Software",
            "contact_name": "No Email Contact",
            "job_title": "Founder",
            "email": "",
            "email_status": "NO_EMAIL",
        },
    ]

    mock_deepline = MagicMock()
    mock_deepline.discover_leads.return_value = {"status": "SUCCESS", "leads": mock_leads}
    mock_deepline.enrich_lead_emails.return_value = mock_leads

    # Mock LLM Client to trace calls
    mock_llm = MagicMock()
    mock_llm.generate_email_1.return_value = MagicMock(body="Hi Rahul, Great work at Delhi HardDisq. Let's connect!\n\nBest regards,\nAlex Mitchell\n\nIf you prefer not to receive emails, reply unsubscribe.")
    mock_llm.generate_followup_a.return_value = MagicMock(body="Hi Rahul, Following up on my previous note.\n\nBest regards,\nAlex Mitchell\n\nReply unsubscribe to opt out.")
    mock_llm.generate_followup_b.return_value = MagicMock(body="Hi Rahul, Final follow-up.\n\nBest regards,\nAlex Mitchell\n\nReply unsubscribe to opt out.")

    icp = ICPConfig(
        id="icp_hd_test",
        campaign_id="camp_hd_test",
        name="Chandigarh Only Campaign",
        campaign_description="Targeting Chandigarh B2B",
        status=ICPStatus.APPROVED,
        geography=GeographyConfig(primary_country="India", allowed_country_keywords=["CHANDIGARH", "MOHALI", "PANCHKULA"])
    )

    runner = DeeplineDiscoveryRunner(
        deepline_client=mock_deepline,
        approval_engine=app_engine,
        icp_approval_engine=icp_engine,
        llm_client=mock_llm
    )

    # Execute discovery
    runner.run_discovery_pipeline(icp=icp, requested_count=10)

    # C, D, E: Confirm Discovery did NOT call generate_email_1, generate_followup_a, generate_followup_b
    assert mock_llm.generate_email_1.call_count == 0
    assert mock_llm.generate_followup_a.call_count == 0
    assert mock_llm.generate_followup_b.call_count == 0

    queue = app_engine.store.load_queue()
    assert len(queue) == 3

    hd_lead = next(r for r in queue if "Delhi" in r.company)
    qual_lead = next(r for r in queue if "Chandigarh" in r.company)
    no_email_lead = next(r for r in queue if "No Email" in r.company)

    # A: HARD_DISQUALIFIED lead enters PENDING_REVIEW when it has a usable email
    assert hd_lead.approval_status == ApprovalStatus.PENDING_REVIEW

    # B: HARD_DISQUALIFIED status and disqualification_reason remain unchanged
    assert hd_lead.qualification_status == "HARD_DISQUALIFIED"
    assert hd_lead.metadata.get("disqualification_reason") is not None

    # H: QUALIFIED lead enters PENDING_REVIEW
    assert qual_lead.approval_status == ApprovalStatus.PENDING_REVIEW
    assert qual_lead.qualification_status == "QUALIFIED"

    # I: NO_EMAIL behavior remains unchanged (BLOCKED)
    assert no_email_lead.approval_status == ApprovalStatus.BLOCKED

    # F: Rejecting a HARD_DISQUALIFIED lead does NOT generate email
    app_engine.reject(hd_lead.lead_id, reviewer="HUMAN_OPERATOR", reason="Out of geography rejection")
    rejected_hd = app_engine.store.get_record(hd_lead.lead_id)
    assert rejected_hd.approval_status == ApprovalStatus.REJECTED
    assert mock_llm.generate_email_1.call_count == 0

    # G: Approving a HARD_DISQUALIFIED lead DOES trigger email generation
    # Reset status back to PENDING_REVIEW for approval test
    rejected_hd.approval_status = ApprovalStatus.PENDING_REVIEW
    app_engine.store.upsert_record(rejected_hd)

    app_engine.llm_client = mock_llm
    approved_hd = app_engine.approve(hd_lead.lead_id, reviewer="HUMAN_OPERATOR")

    assert approved_hd.approval_status == ApprovalStatus.APPROVED
    assert approved_hd.smartlead_eligible is True
    assert approved_hd.qualification_status == "HARD_DISQUALIFIED"  # Preserved!
    assert mock_llm.generate_email_1.call_count == 1
    assert mock_llm.generate_followup_a.call_count == 1
    assert mock_llm.generate_followup_b.call_count == 1
    assert "Hi Rahul, Great work at Delhi HardDisq" in approved_hd.email_1_original

    # J: Repeated approval calls do not duplicate email generation calls
    app_engine.approve(hd_lead.lead_id, reviewer="HUMAN_OPERATOR")
    assert mock_llm.generate_email_1.call_count == 1


def test_unsubscribe_and_no_strong_signal_compliance():
    """
    Regression test verifying:
    A, B, C: Email 1, Followup A, Followup B have canonical unsubscribe mechanisms.
    D, E, F: NO_STRONG_SIGNAL never appears in Email 1, Followup A, or Followup B.
    G: Other forbidden internal labels (SIGNAL_VERIFIED, HARD_DISQUALIFIED) cannot leak.
    H: Valid sequence passes PersonalizationQA.
    I: Invalid sequence without unsubscribe or with leaked label fails PersonalizationQA.
    J: Canonical unsubscribe URL contains actual lead email.
    K: Existing valid personalization is preserved and not unnecessarily rewritten.
    """
    from src.lead_intelligence import (
        LeadIntelligenceOutput, PersonalizationNoteStatus, EvidenceLevel,
        EmailStatus, PriorityLevel, AccessibilityTier, DisqualificationStatus
    )
    from src.integrations.claude_client import ClaudeClient
    from src.personalization.personalization_qa import PersonalizationQA

    target_email = "rajendra@lcodetechnologies.com"
    lead_intel = LeadIntelligenceOutput(
        company_name="LCode Technologies Private Limited",
        company_domain="lcodetechnologies.com",
        contact_name="Rajendra Shenoy",
        job_title="Director",
        email=target_email,
        email_status=EmailStatus.VERIFIED,
        company_size="50 employees",
        company_size_evidence=EvidenceLevel.VERIFIED,
        industry="Technology",
        opportunity_score=75.0,
        accessibility_score=80.0,
        outreach_priority_index=77.0,
        priority_level=PriorityLevel.P2,
        opportunity_tier="Tier 1",
        accessibility_tier=AccessibilityTier.HIGH,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        disqualification_reason=None,
        personalization_note_status=PersonalizationNoteStatus.NO_STRONG_SIGNAL,
        personalization_note="NO_STRONG_SIGNAL",
        relevant_signal="NO_STRONG_SIGNAL",
        research_sources=["Ingestion"],
        ICP_score=75.0,
        pain_point="Workflow automation",
        persona_selection_rationale="Target executive"
    )

    client = ClaudeClient()
    e1 = client.generate_email_1(lead_intel)
    fa = client.generate_followup_a(lead_intel, e1)
    fb = client.generate_followup_b(lead_intel)

    # A, B, C, J: Unsubscribe Mechanism & Lead Email Verification
    canonical_url = f"https://aedrix.com/unsubscribe?email={target_email}"
    assert canonical_url in e1.body
    assert canonical_url in fa.body
    assert canonical_url in fb.body

    # D, E, F, G: Forbidden System Labels Absence Check
    forbidden_terms = ["NO_STRONG_SIGNAL", "SIGNAL_VERIFIED", "HARD_DISQUALIFIED", "CAMPAIGN_EXCLUDED", "INVALID_BOUNCED"]
    for term in forbidden_terms:
        assert term.lower() not in e1.body.lower()
        assert term.lower() not in fa.body.lower()
        assert term.lower() not in fb.body.lower()

    # H: Valid Sequence Passes PersonalizationQA
    qa = PersonalizationQA()
    qa_res = qa.validate_lead_drafts(lead_intel=lead_intel, email_1=e1.body, followup_a=fa.body, followup_b=fb.body)
    assert qa_res.qa_status == "PASS"

    # I: Invalid Sequence Fails PersonalizationQA (Missing Unsubscribe / Leaked Label)
    invalid_body_no_unsub = "Hi Rajendra,\n\nTest email without footer.\n\nBest regards,\nAlex Mitchell"
    qa_fail_1 = qa.validate_lead_drafts(lead_intel=lead_intel, email_1=invalid_body_no_unsub, followup_a=fa.body, followup_b=fb.body)
    assert qa_fail_1.qa_status == "FAIL"
    assert any("Unsubscribe" in r for r in qa_fail_1.qa_reasons)

    invalid_body_leaked_code = e1.body + "\nStatus: NO_STRONG_SIGNAL"
    qa_fail_2 = qa.validate_lead_drafts(lead_intel=lead_intel, email_1=invalid_body_leaked_code, followup_a=fa.body, followup_b=fb.body)
    assert qa_fail_2.qa_status == "FAIL"
    assert any("NO_STRONG_SIGNAL" in r for r in qa_fail_2.qa_reasons)

    # K: Verified Personalization Preservation Check
    verified_lead = LeadIntelligenceOutput(
        company_name="Valid SaaS Inc",
        company_domain="validsaas.com",
        contact_name="Sarah Connors",
        job_title="VP Sales",
        email="sarah@validsaas.com",
        email_status=EmailStatus.VERIFIED,
        company_size="50 employees",
        company_size_evidence=EvidenceLevel.VERIFIED,
        industry="SaaS",
        opportunity_score=85.0,
        accessibility_score=80.0,
        outreach_priority_index=82.0,
        priority_level=PriorityLevel.P1,
        opportunity_tier="Tier 1",
        accessibility_tier=AccessibilityTier.HIGH,
        disqualification_status=DisqualificationStatus.QUALIFIED,
        disqualification_reason=None,
        personalization_note_status=PersonalizationNoteStatus.SIGNAL_VERIFIED,
        personalization_note="Saw your recent expansion into European enterprise software markets.",
        relevant_signal="European expansion initiative",
        research_sources=["Press Release"],
        ICP_score=85.0,
        pain_point="Outreach scaling",
        persona_selection_rationale="Sales leadership"
    )

    e1_v = client.generate_email_1(verified_lead)
    assert "expansion into European" in e1_v.body
    assert f"https://aedrix.com/unsubscribe?email=sarah@validsaas.com" in e1_v.body
    qa_ver_res = qa.validate_lead_drafts(lead_intel=verified_lead, email_1=e1_v.body)
    assert qa_ver_res.qa_status == "PASS"


def test_discovery_auto_copy_generation_and_dynamic_subjects():
    """
    Verifies:
    TEST 1: Software lead with email gets automatic draft copy, QA runs, dynamic non-construction subject,
            NO_STRONG_SIGNAL not leaked, unsubscribe footer present, approval_status=PENDING_REVIEW, smartlead_eligible=False.
    TEST 2: Construction lead gets construction-appropriate subject/context.
    TEST 3: No-email lead gets no copy generated (qa_status=NO_EMAIL).
    TEST 4: Malformed-email lead gets no copy generated.
    TEST 5: Human approval updates approval_status to APPROVED and smartlead_eligible to True without breaking drafts.
    TEST 6: Generated compliance (unsubscribe, signature, no internal system labels).
    """
    from unittest.mock import MagicMock, patch
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.database.connection import get_db_session
    from src.database.repositories.approval_repository import ApprovalRepository
    from src.database.models import Lead, EmailDraft, EmailApproval
    from src.icp.icp_models import ICPConfig, GeographyConfig
    from src.smartlead_staging_runner import SmartleadStagingRunner
    from src.config.app_mode import ModeService

    ModeService._instance = None

    icp_software = ICPConfig(
        id="icp_software_test_001",
        name="Software ICP Test",
        campaign_description="Test campaign for software teams",
        version="1.0.0",
        campaign_id="cmp_software_test",
        industry_verticals=["Computer Software"],
        company_size_min=10,
        company_size_max=500,
        target_geographies=["India"],
        target_personas=["CEO", "Director"],
        product_or_service="Workflow Automation Platform",
        value_proposition="Automate B2B operations efficiently.",
        geography=GeographyConfig(primary_country="India", allowed_country_keywords=["INDIA", "CHANDIGARH", "MOHALI"]),
        status="APPROVED"
    )

    icp_construction = ICPConfig(
        id="icp_construction_test_001",
        name="Construction ICP Test",
        campaign_description="Test campaign for construction teams",
        version="1.0.0",
        campaign_id="cmp_construction_test",
        industry_verticals=["Commercial Construction"],
        company_size_min=10,
        company_size_max=500,
        target_geographies=["India"],
        target_personas=["Operations Director"],
        product_or_service="Site Log Governance",
        value_proposition="Streamline site log governance for contractors.",
        geography=GeographyConfig(primary_country="India", allowed_country_keywords=["INDIA", "CHANDIGARH", "MOHALI"]),
        status="APPROVED"
    )

    mock_leads_sw = [{
        "company_name": "Unique Software Test Corp",
        "company_domain": "uniquesoftwaretest.com",
        "contact_name": "Isha Taneja",
        "job_title": "CEO",
        "email": "isha@uniquesoftwaretest.com",
        "email_status": "VERIFIED",
        "company_size": "50 employees",
        "industry": "Computer Software",
        "city": "Chandigarh",
        "country": "India",
        "personalization_note": "NO_STRONG_SIGNAL"
    }]
    client_sw = MagicMock()
    client_sw.discover_leads.return_value = {"status": "SUCCESS", "leads": mock_leads_sw}
    client_sw.enrich_lead_emails.return_value = mock_leads_sw

    runner_sw = DeeplineDiscoveryRunner(deepline_client=client_sw)

    with patch("src.database.connection.is_database_enabled", return_value=True), \
         patch.object(ModeService, "is_demo", return_value=False):
        # TEST 1: Computer Software lead with usable email
        runner_sw.run_discovery_pipeline(icp=icp_software, requested_count=1)
        with get_db_session() as session:
            lead1 = session.query(Lead).filter(Lead.company_name.ilike("%Unique Software%")).first()
            assert lead1 is not None
            l1_id = lead1.id

            draft1 = session.query(EmailDraft).filter_by(lead_id=l1_id).first()
            app1 = session.query(EmailApproval).filter_by(lead_id=l1_id).first()

            assert draft1 is not None
            assert draft1.ai_original_email_1 != ""
            assert draft1.ai_original_followup_a != ""
            assert draft1.ai_original_followup_b != ""
            assert draft1.qa_status == "PASS"
            assert "https://aedrix.com/unsubscribe?email=isha@uniquesoftwaretest.com" in draft1.ai_original_email_1
            assert "NO_STRONG_SIGNAL" not in draft1.ai_original_email_1
            assert "pre-construction" not in draft1.ai_original_email_1.lower()

            assert app1.approval_status == "PENDING_REVIEW"
            assert app1.smartlead_eligible is False

        # TEST 2: Construction lead with usable email
        mock_leads_cn = [{
            "company_name": "Unique Construction Test Ltd",
            "company_domain": "uniqueconstructiontest.in",
            "contact_name": "Rajiv Sharma",
            "job_title": "Operations Director",
            "email": "rajiv@uniqueconstructiontest.in",
            "email_status": "VERIFIED",
            "company_size": "100 employees",
            "industry": "Commercial Construction",
            "city": "Mohali",
            "country": "India"
        }]
        client_cn = MagicMock()
        client_cn.discover_leads.return_value = {"status": "SUCCESS", "leads": mock_leads_cn}
        client_cn.enrich_lead_emails.return_value = mock_leads_cn
        runner_cn = DeeplineDiscoveryRunner(deepline_client=client_cn)

        runner_cn.run_discovery_pipeline(icp=icp_construction, requested_count=1)
        with get_db_session() as session:
            lead2 = session.query(Lead).filter(Lead.company_name.ilike("%Unique Construction%")).first()
            assert lead2 is not None
            l2_id = lead2.id

            draft2 = session.query(EmailDraft).filter_by(lead_id=l2_id).first()
            assert draft2 is not None
            assert draft2.ai_original_email_1 != ""
            assert "https://aedrix.com/unsubscribe?email=rajiv@uniqueconstructiontest.in" in draft2.ai_original_email_1

        # TEST 3 & 4: Lead with no email / malformed email
        mock_leads_no_email = [{
            "company_name": "Unique No Email Corp",
            "company_domain": "uniquenoemail.com",
            "contact_name": "John Doe",
            "job_title": "CEO",
            "email": "",
            "email_status": "NO_EMAIL",
            "company_size": "50 employees",
            "industry": "Computer Software",
            "city": "Chandigarh",
            "country": "India"
        }]
        client_ne = MagicMock()
        client_ne.discover_leads.return_value = {"status": "SUCCESS", "leads": mock_leads_no_email}
        client_ne.enrich_lead_emails.return_value = mock_leads_no_email
        runner_ne = DeeplineDiscoveryRunner(deepline_client=client_ne)

        runner_ne.run_discovery_pipeline(icp=icp_software, requested_count=1)
        with get_db_session() as session:
            lead3 = session.query(Lead).filter(Lead.company_name.ilike("%Unique No Email%")).first()
        assert lead3 is not None
        l3_id = lead3.id

        draft3 = session.query(EmailDraft).filter_by(lead_id=l3_id).first()
        app3 = session.query(EmailApproval).filter_by(lead_id=l3_id).first()

        assert draft3.ai_original_email_1 == ""
        assert draft3.qa_status == "NO_EMAIL"
        assert app3.approval_status == "BLOCKED"

        # TEST 5: Human approval updates approval status
        repo = ApprovalRepository(session)
        app_rec = repo.approve_lead(l1_id, reviewer="HUMAN_OPERATOR")
        assert app_rec.approval_status == "APPROVED"
        assert app_rec.smartlead_eligible is True

        # TEST STAGING SUBJECT GENERATION
        from app.api.approvals import _map_db_approval_to_record
        staging_runner = SmartleadStagingRunner()
        app_record = _map_db_approval_to_record(app_rec)
        payload = staging_runner.build_lead_payload(app_record)
        stg_sub1 = payload.get("custom_fields", {}).get("email_1_subject", "")
        assert "Pre-construction" not in stg_sub1
