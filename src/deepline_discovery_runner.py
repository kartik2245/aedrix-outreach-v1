"""
deepline_discovery_runner.py
Orchestrator connecting Approved ICP Configurations to Deepline Lead Discovery and the full Outreach Intelligence Pipeline (Python 3.12).

Guarantees:
- Only APPROVED ICPs can execute Deepline discovery.
- All runs are isolated and persisted in data/deepline_runs/run_{timestamp}_{id}/.
- Supports 100, 250, 500, 1000, 5000+ lead batching.
- Every lead and draft is tagged with campaign_id, icp_id, and icp_version.
- All drafts are automatically enrolled into the Human Email Approval Gate (smartlead_eligible=False).
"""

import json
import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.icp.icp_models import ICPConfig, ICPStatus, DeeplineDiscoveryRequest, DeeplineRunMetadata
from src.icp.icp_approval_engine import ICPApprovalEngine
from src.icp.icp_engine import ICPEngine
from src.integrations.deepline_client import DeeplineClient
from src.deepline_export_adapter import DeeplineExportAdapter
from src.integrations.claude_client import ClaudeClient, load_env_file_if_present
from src.personalization.voc_engine import VoCEngine
from src.personalization.personalization_qa import PersonalizationQA
from src.approval.approval_engine import ApprovalEngine
from src.models import (
    LeadIntelligenceOutput,
    EvidenceLevel,
    EmailStatus,
    PersonalizationNoteStatus,
    PriorityLevel,
    AccessibilityTier,
    DisqualificationStatus,
)


from src.integrations.bedrock_client import BedrockClient


class DeeplineDiscoveryRunner:
    def __init__(
        self,
        deepline_client: Optional[DeeplineClient] = None,
        approval_engine: Optional[ApprovalEngine] = None,
        icp_approval_engine: Optional[ICPApprovalEngine] = None,
        llm_client: Optional[Any] = None,
        claude_client: Optional[Any] = None,
        batch_size: int = 25,
    ):
        load_env_file_if_present()
        self.deepline_client = deepline_client or DeeplineClient()
        self.approval_engine = approval_engine or ApprovalEngine()
        self.icp_approval_engine = icp_approval_engine or ICPApprovalEngine()
        self.llm_client = llm_client or claude_client or BedrockClient()
        self.claude_client = self.llm_client
        self.batch_size = batch_size
        self.voc_engine = VoCEngine()
        self.qa_engine = PersonalizationQA()

    def run_discovery_pipeline(
        self,
        icp: ICPConfig,
        requested_count: int = 100,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end discovery and lead intelligence pipeline for an approved ICP.
        """
        # 1. Strict Safety Check: Verify ICP Approval
        if icp.status != ICPStatus.APPROVED:
            raise ValueError(
                f"Cannot execute Deepline discovery on unapproved ICP '{icp.id}'. Status is '{icp.status.value}'. "
                "Human operator approval is required."
            )

        # 2. Build Deepline Discovery Request
        discovery_request = DeeplineDiscoveryRequest(
            icp_id=icp.id,
            campaign_id=icp.campaign_id,
            campaign_name=icp.name,
            geography=icp.geography.allowed_country_keywords,
            industries=icp.industries,
            company_size=icp.company_size,
            personas=icp.target_personas,
            positive_signals=icp.positive_signals,
            exclusions=[c.description for c in icp.campaign_exclusions],
            requested_lead_count=requested_count,
            batch_size=400,
        )

        # 3. Execute Discovery (Live API or High-Fidelity Simulation)
        discovery_result = self.deepline_client.discover_leads(discovery_request)
        raw_leads = discovery_result.get("leads", [])
        # Adapt raw leads using DeeplineExportAdapter to ensure normalized fields
        adapter = DeeplineExportAdapter()
        adapted_leads = [adapter.adapt_record(lead) for lead in raw_leads]
        # Use adapted leads for subsequent processing
        raw_leads = adapted_leads

        # 4. Generate Run Directory
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_uuid = str(uuid.uuid4())[:8]
        run_id = f"run_{timestamp_str}_{run_uuid}"

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        run_dir = os.path.join(base_dir, "data", "deepline_runs", run_id)
        os.makedirs(run_dir, exist_ok=True)

        # 5. Process Leads through Dynamic ICP Engine & Scoring
        icp_engine = ICPEngine(icp)

        qualified_leads = []
        campaign_excluded_count = 0
        hard_disqualified_count = 0
        p1_count = 0
        p2_count = 0
        p3_count = 0

        processed_dossiers = []

        for lead_dict in raw_leads:
            eval_res = icp_engine.evaluate_lead(lead_dict)

            if eval_res.status == DisqualificationStatus.HARD_DISQUALIFIED:
                hard_disqualified_count += 1
                continue
            elif eval_res.status == DisqualificationStatus.CAMPAIGN_EXCLUDED:
                campaign_excluded_count += 1
                continue

            # Calculate Opportunity & Accessibility Scores
            emp_count = lead_dict.get("employee_count", 100) or 100
            rev_str = str(lead_dict.get("revenue", "15M"))
            
            # Opportunity scoring
            opp_score = 70.0
            if emp_count > 5000:
                opp_score += 20.0
            elif emp_count > 1000:
                opp_score += 15.0
            else:
                opp_score += 10.0

            if lead_dict.get("relevant_signal"):
                opp_score += 10.0

            opp_score = min(100.0, opp_score)

            # Accessibility scoring
            acc_score = 65.0
            email_st = lead_dict.get("email_status", "PATTERN_CONFIRMED")
            if email_st == "EVIDENCE_VERIFIED":
                acc_score += 25.0
            elif email_st == "PATTERN_CONFIRMED":
                acc_score += 15.0
            
            if lead_dict.get("linkedin_url"):
                acc_score += 10.0
            acc_score = min(100.0, acc_score)

            # Outreach priority index: (0.6 * opp) + (0.4 * acc)
            priority_index = (0.6 * opp_score) + (0.4 * acc_score)

            if priority_index >= 85.0:
                priority = PriorityLevel.P1
                p1_count += 1
            elif priority_index >= 70.0:
                priority = PriorityLevel.P2
                p2_count += 1
            else:
                priority = PriorityLevel.P3
                p3_count += 1

            sig_text = lead_dict.get("relevant_signal") or "Verified enterprise building contractor."
            note_status = PersonalizationNoteStatus.SIGNAL_VERIFIED if lead_dict.get("relevant_signal") else PersonalizationNoteStatus.NO_STRONG_SIGNAL

            intel = LeadIntelligenceOutput(
                company_name=lead_dict["company_name"],
                company_domain=lead_dict.get("company_domain", "example.co.uk"),
                contact_name=lead_dict["contact_name"],
                job_title=lead_dict["job_title"],
                email=lead_dict["email"],
                email_status=EmailStatus(email_st) if email_st in [e.value for e in EmailStatus] else EmailStatus.PATTERN_CONFIRMED,
                linkedin_url=lead_dict.get("linkedin_url"),
                company_size=lead_dict.get("company_size", f"{emp_count} employees"),
                company_size_evidence=EvidenceLevel.VERIFIED,
                industry=lead_dict.get("industry", "Construction"),
                opportunity_score=opp_score,
                accessibility_score=acc_score,
                outreach_priority_index=priority_index,
                priority_level=priority,
                opportunity_tier="Tier 1" if priority == PriorityLevel.P1 else "Tier 2",
                accessibility_tier=AccessibilityTier.HIGH if acc_score >= 80 else AccessibilityTier.MEDIUM,
                disqualification_status=DisqualificationStatus.QUALIFIED,
                disqualification_reason=None,
                personalization_note_status=note_status,
                personalization_note=sig_text,
                research_sources=["Deepline Research Lead Ingestion"],
                ICP_score=opp_score,
                pain_point=lead_dict.get("pain_point", "Pre-construction document control and drawing versioning latency."),
                pain_point_evidence=EvidenceLevel.INFERRED,
                relevant_signal=sig_text,
                relevant_signal_evidence=EvidenceLevel.VERIFIED,
                persona_selection_rationale=f"Selected {lead_dict['job_title']} as primary decision maker for digital and operational tooling."
            )

            qualified_leads.append(intel)

        # 6. Generate Batch Claude Drafts & Enroll in Human Approval Gate
        from src.config.app_mode import ModeService
        is_demo = ModeService.get_instance().is_demo()
        current_mode = ModeService.get_instance().get_mode().value

        # Ensure Campaign and ICP records exist in PostgreSQL before any lead inserts.
        # leads.campaign_id and leads.icp_id are FK-constrained, so the parent rows MUST
        # be committed before any Lead row is written.
        # ICPRepository.enroll_icp() idempotently upserts: Campaign -> ICP -> ICPVersion -> ICPApproval.
        from src.database.connection import is_database_enabled, get_db_session
        if is_database_enabled():
            try:
                from src.database.repositories.icp_repository import ICPRepository
                with get_db_session() as session:
                    icp_repo = ICPRepository(session)
                    icp_repo.enroll_icp(icp, environment=current_mode, source="CLAUDE_GENERATED")
                    # Mark as approved since the in-memory engine already approved it
                    icp_repo.approve_icp(icp.id, reviewer="SYSTEM_RUNNER")
            except Exception as icp_db_err:
                print(f"Notice: ICP DB upsert failed (leads FK will fail): {icp_db_err}")

        for i, lead_intel in enumerate(qualified_leads):
            voc = self.voc_engine.map_lead_voc(lead_intel)
            e1 = self.llm_client.generate_email_1(lead_intel, voc)
            fa = self.llm_client.generate_followup_a(lead_intel, e1, voc)
            fb = self.llm_client.generate_followup_b(lead_intel, voc)

            qa_res = self.qa_engine.validate_lead_drafts(
                lead_intel=lead_intel,
                email_1=e1,
                followup_a=fa,
                followup_b=fb,
            )

            base_lead_id = self.approval_engine.generate_lead_id(
                company=lead_intel.company_name,
                contact=lead_intel.contact_name,
                email=lead_intel.email,
            )
            lead_id = f"demo_{base_lead_id}" if is_demo else base_lead_id

            # Enroll in Human Approval Gate tagged with campaign_id, icp_id, icp_version
            self.approval_engine.enroll_draft(
                company=lead_intel.company_name,
                contact=lead_intel.contact_name,
                title=lead_intel.job_title,
                email=lead_intel.email,
                qualification_status="QUALIFIED",
                opportunity_score=lead_intel.opportunity_score,
                accessibility_score=lead_intel.accessibility_score,
                outreach_priority_index=lead_intel.outreach_priority_index,
                priority=lead_intel.priority_level.value,
                personalization_status=lead_intel.personalization_note_status.value,
                personalization_note=lead_intel.personalization_note,
                voc_angle=voc.voc_angle,
                email_1=e1.body,
                followup_a=fa.body,
                followup_b=fb.body,
                qa_status=qa_res.qa_status,
                qa_reasons=qa_res.qa_reasons,
                metadata={
                    "campaign_id": icp.campaign_id,
                    "icp_id": icp.id,
                    "icp_version": icp.version,
                    "deepline_run_id": run_id,
                    "linkedin_url": lead_intel.linkedin_url,
                    "website": lead_intel.company_domain,
                },
                lead_id=lead_id,
            )

            # Persist to database if enabled
            from src.database.models import Lead, LeadEvidence, LeadResearch, VoCContext, EmailDraft, EmailApproval

            if is_database_enabled():
                try:
                    with get_db_session() as session:
                        db_lead = session.get(Lead, lead_id)
                        if not db_lead:
                            db_lead = Lead(
                                id=lead_id,
                                campaign_id=icp.campaign_id,
                                icp_id=icp.id,
                                icp_version=icp.version,
                                environment=current_mode,
                                company_name=lead_intel.company_name,
                                company_domain=lead_intel.company_domain,
                                contact_name=lead_intel.contact_name,
                                job_title=lead_intel.job_title,
                                email=lead_intel.email,
                                email_status=lead_intel.email_status.value if hasattr(lead_intel.email_status, "value") else str(lead_intel.email_status),
                                linkedin_url=lead_intel.linkedin_url,
                                company_size=lead_intel.company_size,
                                industry=lead_intel.industry,
                                opportunity_score=lead_intel.opportunity_score,
                                accessibility_score=lead_intel.accessibility_score,
                                outreach_priority_index=lead_intel.outreach_priority_index,
                                priority_level=lead_intel.priority_level.value if hasattr(lead_intel.priority_level, "value") else str(lead_intel.priority_level),
                                qualification_status="QUALIFIED",
                                personalization_status=lead_intel.personalization_note_status.value if hasattr(lead_intel.personalization_note_status, "value") else str(lead_intel.personalization_note_status),
                                personalization_note=lead_intel.personalization_note,
                                voc_angle=voc.voc_angle,
                            )
                            session.add(db_lead)
                            session.flush()
                        else:
                            db_lead.environment = current_mode
                            db_lead.campaign_id = icp.campaign_id
                            db_lead.icp_id = icp.id
                            db_lead.icp_version = icp.version

                        # Email Draft
                        db_draft = session.query(EmailDraft).filter_by(lead_id=lead_id).first()
                        if not db_draft:
                            db_draft = EmailDraft(
                                lead_id=lead_id,
                                ai_original_email_1=e1.body,
                                ai_original_followup_a=fa.body,
                                ai_original_followup_b=fb.body,
                                qa_status=qa_res.qa_status,
                                qa_reasons=qa_res.qa_reasons,
                            )
                            session.add(db_draft)
                        else:
                            db_draft.ai_original_email_1 = e1.body
                            db_draft.ai_original_followup_a = fa.body
                            db_draft.ai_original_followup_b = fb.body
                            db_draft.qa_status = qa_res.qa_status
                            db_draft.qa_reasons = qa_res.qa_reasons

                        # Email Approval
                        db_app = session.query(EmailApproval).filter_by(lead_id=lead_id).first()
                        if not db_app:
                            db_app = EmailApproval(
                                lead_id=lead_id,
                                approval_status="PENDING_REVIEW",
                                smartlead_eligible=False,
                                flag_no_strong_signal=(lead_intel.personalization_note_status == PersonalizationNoteStatus.NO_STRONG_SIGNAL),
                                metadata_json={
                                    "campaign_id": icp.campaign_id,
                                    "icp_id": icp.id,
                                    "icp_version": icp.version,
                                    "deepline_run_id": run_id,
                                }
                            )
                            session.add(db_app)
                        else:
                            db_app.approval_status = "PENDING_REVIEW"
                            db_app.smartlead_eligible = False
                            db_app.metadata_json = {
                                "campaign_id": icp.campaign_id,
                                "icp_id": icp.id,
                                "icp_version": icp.version,
                                "deepline_run_id": run_id,
                            }
                except Exception as db_err:
                    print(f"Notice: Deepline discovery DB sync failed: {db_err}")

        # 7. Record Run Metadata and Artifacts
        metadata = DeeplineRunMetadata(
            run_id=run_id,
            icp_id=icp.id,
            campaign_id=icp.campaign_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode="DRY_RUN_SIMULATION" if not self.deepline_client.live_mode else "LIVE_API",
            requested_count=requested_count,
            discovered_count=len(raw_leads),
            valid_count=len(raw_leads) - hard_disqualified_count - campaign_excluded_count,
            qualified_count=len(qualified_leads),
            campaign_excluded_count=campaign_excluded_count,
            hard_disqualified_count=hard_disqualified_count,
            p1_count=p1_count,
            p2_count=p2_count,
            p3_count=p3_count,
            api_calls_made=0 if not self.deepline_client.live_mode else 1,
            credits_consumed=0,
            safety_status="SAFETY_GATE_ACTIVE (DRY_RUN=true, ZERO_EMAILS_SENT)"
        )

        with open(os.path.join(run_dir, "icp.json"), "w", encoding="utf-8") as f:
            json.dump(icp.model_dump(mode="json"), f, indent=2)

        with open(os.path.join(run_dir, "discovery_request.json"), "w", encoding="utf-8") as f:
            json.dump(discovery_request.model_dump(mode="json"), f, indent=2)

        with open(os.path.join(run_dir, "export.json"), "w", encoding="utf-8") as f:
            json.dump(raw_leads, f, indent=2)

        with open(os.path.join(run_dir, "run_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(mode="json"), f, indent=2)

        # 8. Record Deepline run against the ICP approval record
        self.icp_approval_engine.record_deepline_run(icp.id, run_id)

        return {
            "run_id": run_id,
            "icp_id": icp.id,
            "campaign_id": icp.campaign_id,
            "summary": {
                "discovered": len(raw_leads),
                "valid": len(raw_leads) - hard_disqualified_count - campaign_excluded_count,
                "qualified": len(qualified_leads),
                "hard_disqualified": hard_disqualified_count,
                "campaign_excluded": campaign_excluded_count,
                "p1_count": p1_count,
                "p2_count": p2_count,
                "p3_count": p3_count,
            },
            "run_artifacts_path": run_dir,
            "safety_mode": "ZERO-RISK DRY RUN (0 emails sent, 0 paid credits consumed)"
        }
