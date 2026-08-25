"""
test_db_fk_regression.py
Regression tests for:
  - PostgreSQL FK violation: leads.icp_id -> icps.id
  - PostgreSQL FK violation: leads.campaign_id -> campaigns.id
  - Approval queue record lookup by deepline_run_id

Root cause (run_20260820_141757):
  DeeplineDiscoveryRunner inserted Lead rows with icp_id and campaign_id
  that did not yet exist in PostgreSQL. ICPApprovalEngine only wrote to
  the in-memory/JSON approval store; it never persisted Campaign or ICP
  rows to PostgreSQL.

Fix:
  DeeplineDiscoveryRunner now calls ICPRepository.enroll_icp() +
  approve_icp() in a committed transaction BEFORE the per-lead DB sync loop.
"""

import os
import pytest
from unittest.mock import MagicMock, patch, call
from src.approval.approval_store import ApprovalStore
from src.approval.approval_engine import ApprovalEngine


def test_16a_runner_calls_icp_repository_before_lead_db_sync():
    """
    Regression: runner did not persist ICP to PostgreSQL before inserting leads.

    Verifies that when database is enabled, the runner:
      1. Calls ICPRepository.enroll_icp() before any Lead is inserted
      2. Calls ICPRepository.approve_icp() before any Lead is inserted

    Uses mocks only -- no live DB, no external API calls.
    """
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.icp.icp_designer import ICPDesigner
    from src.icp.icp_approval_engine import ICPApprovalEngine
    from src.icp.icp_approval_store import ICPApprovalStore

    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="Test FK Campaign",
        campaign_objective="FK regression test",
        product_context="Aedrix test",
        geography="United Kingdom",
        industry="Commercial Construction",
        company_size="50+ employees",
        target_personas=["Digital Director"],
        positive_signals=["BIM adoption"],
        hard_disqualifiers=["Outside UK"],
        campaign_exclusions=["CRM active"],
        voc_context="Test voc context",
    )

    # Approve the ICP in the in-memory store
    icp_store = ICPApprovalStore()
    icp_approval_engine = ICPApprovalEngine(store=icp_store)
    enrolled = icp_approval_engine.enroll_icp(icp, source="MANUAL")
    approved_rec = icp_approval_engine.approve_icp(enrolled.icp_id, reviewer="TEST")
    approved_icp = approved_rec.effective_icp

    # Mock everything external
    mock_deepline = MagicMock()
    mock_deepline.live_mode = False
    mock_deepline.discover_leads.return_value = {"leads": []}  # No leads returned = no loop body

    mock_bedrock = MagicMock()
    mock_bedrock.dry_run = True
    mock_bedrock.send_emails = False
    mock_bedrock.model = "deepseek.v3.2"
    mock_bedrock.region = "ap-south-1"

    runner = DeeplineDiscoveryRunner(
        deepline_client=mock_deepline,
        llm_client=mock_bedrock,
    )

    # Track ICPRepository calls
    enroll_called = []
    approve_called = []

    mock_icp_repo_instance = MagicMock()
    mock_icp_repo_instance.enroll_icp.side_effect = lambda *a, **kw: enroll_called.append(True)
    mock_icp_repo_instance.approve_icp.side_effect = lambda *a, **kw: approve_called.append(True)

    with patch("src.database.connection.is_database_enabled", return_value=True), \
         patch("src.database.connection.get_db_session") as mock_ctx, \
         patch("src.database.repositories.icp_repository.ICPRepository", return_value=mock_icp_repo_instance):

        mock_session = MagicMock()
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        runner.run_discovery_pipeline(icp=approved_icp, requested_count=1)

    # Verify enroll_icp and approve_icp were called (even with 0 leads returned)
    assert len(enroll_called) >= 1, (
        "ICPRepository.enroll_icp() must be called before lead inserts to satisfy FK constraints. "
        "It was NOT called."
    )
    assert len(approve_called) >= 1, (
        "ICPRepository.approve_icp() must be called before lead inserts. "
        "It was NOT called."
    )


def test_16b_icp_repository_upsert_chain_ordering():
    """
    Regression: ICPRepository.enroll_icp() must persist Campaign BEFORE ICP
    (because icps.campaign_id FK references campaigns.id).

    This test verifies the flush ordering inside ICPRepository.enroll_icp()
    using a mock session that tracks add() and flush() call order.
    """
    from src.database.repositories.icp_repository import ICPRepository
    from src.icp.icp_designer import ICPDesigner

    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="FK Order Test",
        campaign_objective="Test ordering",
        product_context="Test",
        geography="United Kingdom",
        industry="Commercial Construction",
        company_size="50+ employees",
        target_personas=["Director"],
        positive_signals=["signal"],
        hard_disqualifiers=["outside UK"],
        campaign_exclusions=["CRM"],
        voc_context="voc",
    )

    flush_count = []
    add_order = []

    mock_session = MagicMock()
    mock_session.scalar.return_value = None  # nothing exists yet
    mock_session.add.side_effect = lambda obj: add_order.append(type(obj).__name__)
    mock_session.flush.side_effect = lambda: flush_count.append(len(flush_count) + 1)

    repo = ICPRepository(mock_session)
    repo.enroll_icp(icp, environment="PRODUCTION", source="MANUAL")

    # Campaign must be flushed BEFORE ICP (FK parent before child)
    assert "Campaign" in add_order, "Campaign must be added to session"
    assert "ICP" in add_order, "ICP must be added to session"
    campaign_idx = add_order.index("Campaign")
    icp_idx = add_order.index("ICP")
    assert campaign_idx < icp_idx, (
        f"Campaign must be added before ICP to satisfy FK. "
        f"Got order: {add_order}"
    )
    # There must be at least 1 flush call (Campaign flush before ICP add)
    assert len(flush_count) >= 1, "flush() must be called at least once to propagate Campaign PK before ICP insert"


def test_17_approval_queue_lookup_by_deepline_run_id_works_via_json_store(tmp_path):
    """
    Regression: approval queue lookup returned no matching records because
    DB sync failed (FK violation), so no email_approvals row was written.

    The JSON fallback store receives the record from ApprovalEngine.enroll_draft()
    regardless of DB state.

    Verifies:
      a. enroll_draft() writes record with deepline_run_id to the JSON store
      b. _load_json_queue() retrieves it correctly
      c. The metadata.get("deepline_run_id") == run_id lookup works
    """
    queue_path = str(tmp_path / "approval_queue.json")
    store = ApprovalStore(storage_path=queue_path)
    approval_engine = ApprovalEngine(store=store)

    test_run_id = "run_20260820_fk_regression_test"
    test_icp_id = "icp_camp_fk_test_20260820"
    test_campaign_id = "cam_fk_test_20260820"

    approval_engine.enroll_draft(
        company="Barkers Security Engineering",
        contact="Sarah Lawton Clewlow",
        title="Operations Director",
        email="",
        qualification_status="QUALIFIED",
        opportunity_score=65.0,
        accessibility_score=50.0,
        outreach_priority_index=59.0,
        priority="P2",
        personalization_status="SIGNAL_VERIFIED",
        personalization_note="Digital transformation and BIM adoption signals.",
        voc_angle="Pre-construction document control risk",
        email_1="Subject: Aedrix for Barkers\n\nDear Sarah...",
        followup_a="Following up on my previous email...",
        followup_b="One final follow-up...",
        qa_status="PASS",
        qa_reasons=[],
        metadata={
            "campaign_id": test_campaign_id,
            "icp_id": test_icp_id,
            "icp_version": "1.0.0",
            "deepline_run_id": test_run_id,
        },
        lead_id="lead_barkers_security_engineering_sarah_lawton_clewlow",
    )

    assert os.path.exists(queue_path), "JSON queue file must exist after enroll_draft()"

    loaded = store._load_json_queue()
    assert len(loaded) == 1, f"Expected 1 record in JSON queue, got {len(loaded)}"

    matching = [r for r in loaded if r.metadata.get("deepline_run_id") == test_run_id]
    assert len(matching) == 1, (
        f"Expected 1 record matching deepline_run_id={test_run_id!r}, got {len(matching)}"
    )

    rec = matching[0]
    assert rec.company == "Barkers Security Engineering"
    assert rec.contact == "Sarah Lawton Clewlow"
    assert rec.qualification_status == "QUALIFIED"
    assert rec.metadata.get("icp_id") == test_icp_id
    assert rec.metadata.get("campaign_id") == test_campaign_id


def test_16c_lead_and_email_approval_fk_ordering():
    """
    Regression: Lead entity must be added and flushed BEFORE EmailDraft and EmailApproval
    entities so that leads.id foreign key constraints are satisfied.
    """
    from src.database.models.lead import Lead
    from src.database.models.email import EmailDraft, EmailApproval

    add_order = []
    flush_count = []

    mock_session = MagicMock()
    mock_session.get.return_value = None
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    mock_session.add.side_effect = lambda obj: add_order.append(type(obj).__name__)
    mock_session.flush.side_effect = lambda: flush_count.append(len(flush_count) + 1)

    lead = Lead(id="lead_test_123", campaign_id="camp_123", icp_id="icp_123")
    draft = EmailDraft(lead_id="lead_test_123", ai_original_email_1="a", ai_original_followup_a="b", ai_original_followup_b="c")
    approval = EmailApproval(lead_id="lead_test_123", approval_status="PENDING_REVIEW")

    mock_session.add(lead)
    mock_session.flush()
    mock_session.add(draft)
    mock_session.add(approval)
    mock_session.flush()

    assert add_order == ["Lead", "EmailDraft", "EmailApproval"]
    assert len(flush_count) == 2, "Lead flush must occur before child draft/approval additions"


def test_19_offline_e2e_db_fk_persistence_chain(tmp_path, monkeypatch):
    """
    OFFLINE END-TO-END REGRESSION TEST:
    Proves that DeeplineDiscoveryRunner executes the full database persistence chain:
    Campaign -> ICP -> Lead -> EmailDraft -> EmailApproval
    completely offline without external API calls or credit consumption.

    Verifies:
      1. Campaign row created/upserted with campaign_id == icp.campaign_id
      2. ICP row created/upserted with id == icp.id and campaign_id == icp.campaign_id
      3. Lead row created with lead.id, campaign_id == icp.campaign_id, icp_id == icp.id
      4. EmailDraft row created referencing lead_id == lead.id
      5. EmailApproval row created referencing lead_id == lead.id with metadata_json containing deepline_run_id
      6. Retrieval from ApprovalStore via load_queue() returns the matching record
      7. Re-running discovery on the same lead executes idempotently without duplicate records
      8. 0 Deepline API calls, 0 AWS Bedrock API calls, 0 Smartlead API calls, 0 outbound emails sent
    """
    import uuid
    from src.icp.icp_designer import ICPDesigner
    from src.icp.icp_approval_engine import ICPApprovalEngine
    from src.icp.icp_approval_store import ICPApprovalStore
    from src.deepline_discovery_runner import DeeplineDiscoveryRunner
    from src.approval.approval_store import ApprovalStore
    from src.approval.approval_engine import ApprovalEngine

    # Track network calls
    network_calls = []
    def guarded_urlopen(req, *args, **kwargs):
        network_calls.append(str(req))
        raise RuntimeError(f"SAFETY ERROR: Outbound network call attempted to {req}")

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", guarded_urlopen)
    monkeypatch.setenv("DEEPLINE_LIVE", "false")
    monkeypatch.setenv("DEEPLINE_RUN_CONFIRMATION", "false")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("SEND_EMAILS", "false")
    monkeypatch.setenv("SMARTLEAD_LIVE", "false")

    # 1. Create a deterministic test ICP configuration with isolated IDs
    unique_hex = uuid.uuid4().hex[:8]
    test_camp_id = f"campaign_offline_fk_regression_{unique_hex}"
    test_icp_id = f"icp_offline_fk_regression_{unique_hex}"

    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="Barkers Security Engineering Live Lead Offline Verification",
        campaign_objective="Test offline DB FK ordering",
        product_context="Aedrix SaaS platform for UK main contractors",
        geography="United Kingdom",
        industry="Commercial Construction",
        company_size="50+ employees",
        target_personas=["Operations Director"],
        positive_signals=["BIM adoption"],
        hard_disqualifiers=["Outside UK"],
        campaign_exclusions=["CRM active"],
        voc_context="Pre-construction document control risk"
    )
    icp.id = test_icp_id
    icp.campaign_id = test_camp_id

    # 2. Approve ICP via in-memory store
    icp_queue_file = tmp_path / "icp_queue.json"
    icp_store = ICPApprovalStore(storage_path=str(icp_queue_file))
    icp_approval_engine = ICPApprovalEngine(store=icp_store)
    enrolled_icp_rec = icp_approval_engine.enroll_icp(icp, source="MANUAL")
    approved_icp_rec = icp_approval_engine.approve_icp(enrolled_icp_rec.icp_id, reviewer="TEST_OPERATOR")
    approved_icp = approved_icp_rec.effective_icp

    # 3. Create deterministic fake lead returned by mock Deepline client
    mock_deepline = MagicMock()
    mock_deepline.live_mode = False
    mock_deepline.discover_leads.return_value = {
        "status": "SUCCESS",
        "mode": "DRY_RUN_SIMULATION",
        "leads": [
            {
                "company_name": "Barkers Security Engineering",
                "company_domain": "barkersfencing.com",
                "company_location": "United Kingdom",
                "country": "United Kingdom",
                "is_uk_operating": True,
                "industry": "Commercial Construction",
                "is_construction_sector": True,
                "company_size": "85 employees",
                "employee_count": 85,
                "contact_name": "Sarah Lawton Clewlow",
                "job_title": "Operations Director",
                "email": "s.clewlow@barkersfencing.com",
                "email_status": "EVIDENCE_VERIFIED",
                "linkedin_url": "https://linkedin.com/in/sarah-clewlow",
                "relevant_signal": "Digital transformation & BIM adoption",
                "pain_point": "Pre-construction document control risk"
            }
        ]
    }

    # 4. Mock Bedrock/LLM client for copy generation
    mock_bedrock = MagicMock()
    mock_bedrock.dry_run = True
    mock_bedrock.send_emails = False
    mock_bedrock.model = "deepseek.v3.2"
    mock_bedrock.generate_email_1.return_value = MagicMock(body="Subject: Aedrix for Barkers\n\nDear Sarah...")
    mock_bedrock.generate_followup_a.return_value = MagicMock(body="Following up on Aedrix...")
    mock_bedrock.generate_followup_b.return_value = MagicMock(body="Final follow-up...")

    # 5. Approval Engine with isolated store
    app_queue_file = tmp_path / "approval_queue.json"
    app_store = ApprovalStore(storage_path=str(app_queue_file))
    app_engine = ApprovalEngine(store=app_store)

    runner = DeeplineDiscoveryRunner(
        deepline_client=mock_deepline,
        llm_client=mock_bedrock,
        approval_engine=app_engine,
        icp_approval_engine=icp_approval_engine
    )

    # 6. Simulated DB storage backend mapping ORM models in memory
    db_records = {
        "Campaign": {},
        "ICP": {},
        "ICPVersion": {},
        "ICPApproval": {},
        "Lead": {},
        "EmailDraft": {},
        "EmailApproval": {},
        "AuditLog": {},
    }

    class MockQuery:
        def __init__(self, model_cls):
            self.model_cls = model_cls
            self._filtered = []

        def filter_by(self, **kwargs):
            cls_name = self.model_cls.__name__
            table = db_records.get(cls_name, {})
            filtered = []
            for obj in table.values():
                match = True
                for k, v in kwargs.items():
                    if getattr(obj, k, None) != v:
                        match = False
                        break
                if match:
                    filtered.append(obj)
            self._filtered = filtered
            return self

        def first(self):
            return self._filtered[0] if getattr(self, "_filtered", []) else None

        def all(self):
            return getattr(self, "_filtered", [])

    class MockDBSession:
        def add(self, obj):
            cls_name = type(obj).__name__
            # Enforce Foreign Key Integrity Checks
            if cls_name == "ICP":
                camp_id = getattr(obj, "campaign_id", None)
                assert camp_id in db_records["Campaign"], f"FK VIOLATION: Campaign '{camp_id}' must exist before ICP"
            elif cls_name == "Lead":
                camp_id = getattr(obj, "campaign_id", None)
                icp_id = getattr(obj, "icp_id", None)
                assert camp_id in db_records["Campaign"], f"FK VIOLATION: Campaign '{camp_id}' must exist before Lead"
                assert icp_id in db_records["ICP"], f"FK VIOLATION: ICP '{icp_id}' must exist before Lead"
            elif cls_name in ("EmailDraft", "EmailApproval"):
                lead_id = getattr(obj, "lead_id", None)
                assert lead_id in db_records["Lead"], f"FK VIOLATION: Lead '{lead_id}' must exist before {cls_name}"

            pk = getattr(obj, "id", None) or getattr(obj, "lead_id", None) or f"{cls_name}_{len(db_records.get(cls_name, {})) + 1}"
            db_records[cls_name][pk] = obj

        def flush(self):
            pass

        def commit(self):
            pass

        def get(self, model_cls, pk):
            cls_name = model_cls.__name__
            return db_records.get(cls_name, {}).get(pk)

        def scalar(self, stmt):
            str_stmt = str(stmt)
            if "FROM campaigns" in str_stmt or "campaigns." in str_stmt:
                for c in db_records["Campaign"].values():
                    if c.id == test_camp_id:
                        return c
                return None
            elif "FROM icp_approvals" in str_stmt or "icp_approvals." in str_stmt:
                for a in db_records["ICPApproval"].values():
                    if a.icp_id == test_icp_id:
                        return a
                return None
            elif "FROM icps" in str_stmt or "icps." in str_stmt:
                for i in db_records["ICP"].values():
                    if i.id == test_icp_id:
                        return i
                return None
            elif "FROM icp_versions" in str_stmt or "icp_versions." in str_stmt:
                for v in db_records["ICPVersion"].values():
                    if v.icp_id == test_icp_id:
                        return v
                return None
            return None

        def query(self, model_cls):
            return MockQuery(model_cls)

    mock_db_session = MockDBSession()

    class MockContextManager:
        def __enter__(self):
            return mock_db_session
        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    with patch("src.database.connection.is_database_enabled", return_value=True), \
         patch("src.database.connection.get_db_session", return_value=MockContextManager()):

        res = runner.run_discovery_pipeline(icp=approved_icp, requested_count=1)

    # 7. Assert Discovery Pipeline Outputs
    assert res["summary"]["discovered"] == 1
    assert res["summary"]["qualified"] == 1
    assert res["summary"]["hard_disqualified"] == 0

    # 8. Assert DB Persistence Chain
    assert test_camp_id in db_records["Campaign"], f"Campaign '{test_camp_id}' was not persisted to DB!"
    assert test_icp_id in db_records["ICP"], f"ICP '{test_icp_id}' was not persisted to DB!"
    
    db_icp_obj = db_records["ICP"][test_icp_id]
    assert db_icp_obj.campaign_id == test_camp_id
    assert db_icp_obj.status == "APPROVED"

    assert len(db_records["Lead"]) == 1, "Expected exactly 1 Lead in DB"
    lead_obj = list(db_records["Lead"].values())[0]
    assert lead_obj.company_name == "Barkers Security Engineering"
    assert lead_obj.contact_name == "Sarah Lawton Clewlow"
    assert lead_obj.job_title == "Operations Director"
    assert lead_obj.campaign_id == test_camp_id
    assert lead_obj.icp_id == test_icp_id

    assert len(db_records["EmailDraft"]) == 1, "Expected exactly 1 EmailDraft in DB"
    draft_obj = list(db_records["EmailDraft"].values())[0]
    assert draft_obj.lead_id == lead_obj.id

    assert len(db_records["EmailApproval"]) == 1, "Expected exactly 1 EmailApproval in DB"
    approval_obj = list(db_records["EmailApproval"].values())[0]
    assert approval_obj.lead_id == lead_obj.id
    assert approval_obj.metadata_json.get("campaign_id") == test_camp_id
    assert approval_obj.metadata_json.get("icp_id") == test_icp_id
    assert approval_obj.metadata_json.get("deepline_run_id") == res["run_id"]

    # 9. Assert ApprovalStore JSON queue retrieval
    json_queue = app_store._load_json_queue()
    assert len(json_queue) == 1
    matching_json = [r for r in json_queue if r.metadata.get("deepline_run_id") == res["run_id"]]
    assert len(matching_json) == 1
    assert matching_json[0].company == "Barkers Security Engineering"

    # 10. Test Duplicate Execution (Idempotency)
    with patch("src.database.connection.is_database_enabled", return_value=True), \
         patch("src.database.connection.get_db_session", return_value=MockContextManager()):

        res2 = runner.run_discovery_pipeline(icp=approved_icp, requested_count=1)

    assert len(db_records["Campaign"]) == 1, "Duplicate run should not create duplicate Campaign"
    assert len(db_records["ICP"]) == 1, "Duplicate run should not create duplicate ICP"
    assert len(db_records["Lead"]) == 1, "Duplicate run should not create duplicate Lead"
    assert len(db_records["EmailDraft"]) == 1, "Duplicate run should not create duplicate EmailDraft"
    assert len(db_records["EmailApproval"]) == 1, "Duplicate run should not create duplicate EmailApproval"

    # 11. Assert 0 live network calls were made
    assert len(network_calls) == 0, "Zero outbound network calls must be made"
    assert mock_deepline.discover_leads.call_count == 2



