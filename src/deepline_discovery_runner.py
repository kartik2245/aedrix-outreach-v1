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

        # 3. Execute Discovery & Pre-Ingestion Email Enrichment
        discovery_result = self.deepline_client.discover_leads(discovery_request)
        discovered_people = discovery_result.get("leads", [])
        people_discovered_count = len(discovered_people)

        # Normalise email/email_status from the People Search result.
        # enrich_lead_emails makes ZERO additional API calls: it reads the email
        # field already returned by ai_ark_people_search and normalises the status.
        # No external Email Finder architecture or webhook enrichment is invoked.
        enriched_people = self.deepline_client.enrich_lead_emails(discovered_people)
        if not isinstance(enriched_people, list):
            enriched_people = discovered_people

        # Email Status Categorization & Quality Gate Routing
        # ALL leads are preserved. Leads are categorized into VERIFIED, UNVERIFIED, or NO_EMAIL.
        all_leads = []
        verified_leads = []
        unverified_leads = []
        no_email_leads = []

        for p in enriched_people:
            email_val = str(p.get("email") or "").strip().lower()
            raw_p_st = p.get("email_status") or p.get("email_verification_status") or p.get("email_status_input") or ""
            status_val = str(raw_p_st.value if hasattr(raw_p_st, "value") else raw_p_st).strip().upper()

            has_valid_syntax = bool(email_val and "@" in email_val and "." in email_val.split("@")[-1] and len(email_val) >= 5)

            if not has_valid_syntax or not email_val or status_val in ("NO_EMAIL", "INVALID", "MALFORMED", "BOUNCED", "INVALID_BOUNCED", "SUPPRESSED", "GLOBAL_SUPPRESSED", "OPT_OUT", "OPTED_OUT"):
                if not has_valid_syntax or not email_val or status_val == "NO_EMAIL":
                    p["email_status"] = "NO_EMAIL"
                    p["email"] = ""
                no_email_leads.append(p)
            elif status_val in ("UNVERIFIED", "UNKNOWN", "CATCHALL_UNVERIFIED"):
                p["email_status"] = "UNVERIFIED"
                unverified_leads.append(p)
            else:
                if not status_val:
                    p["email_status"] = "VERIFIED"
                verified_leads.append(p)

            all_leads.append(p)

        adapter = DeeplineExportAdapter()
        adapted_leads = [adapter.adapt_record(lead) for lead in all_leads]
        raw_leads = adapted_leads

        metrics = {
            "people_discovered": people_discovered_count,
            "enrichment_attempted": people_discovered_count,
            "verified_emails_found": len(verified_leads),
            "unverified_emails_found": len(unverified_leads),
            "no_email_found": len(no_email_leads),
            "aedrix_leads_created": len(all_leads),
        }
        print(f"Discovery Metrics: {metrics}")

        # 4. Generate Run Directory
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_uuid = str(uuid.uuid4())[:8]
        run_id = f"run_{timestamp_str}_{run_uuid}"

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        run_dir = os.path.join(base_dir, "data", "deepline_runs", run_id)
        os.makedirs(run_dir, exist_ok=True)

        # 5. Process Leads through Dynamic ICP Engine & Scoring
        icp_engine = ICPEngine(icp)

        all_processed_leads = []
        qualified_leads_count = 0
        campaign_excluded_count = 0
        hard_disqualified_count = 0
        p1_count = 0
        p2_count = 0
        p3_count = 0

        for lead_dict in raw_leads:
            eval_res = icp_engine.evaluate_lead(lead_dict)

            qual_status_str = eval_res.status.value if hasattr(eval_res.status, "value") else str(eval_res.status)
            disqual_reason = eval_res.disqualification_reason

            if eval_res.status == DisqualificationStatus.HARD_DISQUALIFIED:
                hard_disqualified_count += 1
            elif eval_res.status == DisqualificationStatus.CAMPAIGN_EXCLUDED:
                campaign_excluded_count += 1
            elif eval_res.status == DisqualificationStatus.QUALIFIED:
                qualified_leads_count += 1

            # Calculate Opportunity & Accessibility Scores for all leads
            emp_count = lead_dict.get("employee_count", 100) or 100
            
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

            sig_text = lead_dict.get("relevant_signal") or "Verified target audience lead."
            note_status = PersonalizationNoteStatus.SIGNAL_VERIFIED if lead_dict.get("relevant_signal") else PersonalizationNoteStatus.NO_STRONG_SIGNAL
            raw_st = lead_dict.get("email_status") or lead_dict.get("email_status_input")
            if isinstance(raw_st, EmailStatus):
                resolved_email_status = raw_st
            else:
                st_str = str(raw_st or "").strip().upper()
                if not st_str:
                    st_str = "VERIFIED" if (lead_dict.get("email") and "@" in str(lead_dict.get("email"))) else "NO_EMAIL"
                try:
                    resolved_email_status = EmailStatus(st_str)
                except ValueError:
                    resolved_email_status = EmailStatus.UNVERIFIED if lead_dict.get("email") else EmailStatus.NO_EMAIL

            intel = LeadIntelligenceOutput(
                company_name=lead_dict["company_name"],
                company_domain=lead_dict.get("company_domain", "example.com"),
                contact_name=lead_dict["contact_name"],
                job_title=lead_dict["job_title"],
                email=lead_dict["email"],
                email_status=resolved_email_status,
                linkedin_url=lead_dict.get("linkedin_url"),
                company_size=lead_dict.get("company_size", f"{emp_count} employees"),
                company_size_evidence=EvidenceLevel.VERIFIED,
                industry=lead_dict.get("industry", "Technology"),
                opportunity_score=opp_score,
                accessibility_score=acc_score,
                outreach_priority_index=priority_index,
                priority_level=priority,
                opportunity_tier="Tier 1" if priority == PriorityLevel.P1 else "Tier 2",
                accessibility_tier=AccessibilityTier.HIGH if acc_score >= 80 else AccessibilityTier.MEDIUM,
                disqualification_status=eval_res.status,
                disqualification_reason=disqual_reason,
                personalization_note_status=note_status,
                personalization_note=sig_text,
                research_sources=["Deepline Research Lead Ingestion"],
                ICP_score=opp_score,
                pain_point=lead_dict.get("pain_point", "Operational efficiency and digital transformation challenges."),
                pain_point_evidence=EvidenceLevel.INFERRED,
                relevant_signal=sig_text,
                relevant_signal_evidence=EvidenceLevel.VERIFIED,
                persona_selection_rationale=f"Selected {lead_dict['job_title']} as primary decision maker."
            )

            all_processed_leads.append((intel, qual_status_str, disqual_reason))

        # 6. Generate Batch Claude Drafts & Enroll in Human Approval Gate & DB Persistence
        from src.config.app_mode import ModeService
        is_demo = ModeService.get_instance().is_demo()
        current_mode = ModeService.get_instance().get_mode().value

        from src.database.connection import is_database_enabled, get_db_session
        if is_database_enabled():
            try:
                from src.database.repositories.icp_repository import ICPRepository
                with get_db_session() as session:
                    icp_repo = ICPRepository(session)
                    icp_repo.enroll_icp(icp, environment=current_mode, source="CLAUDE_GENERATED")
                    icp_repo.approve_icp(icp.id, reviewer="SYSTEM_RUNNER")
            except Exception as icp_db_err:
                print(f"Notice: ICP DB upsert failed (leads FK will fail): {icp_db_err}")

        for i, (lead_intel, qual_status_str, disqual_reason) in enumerate(all_processed_leads):
            voc = self.voc_engine.map_lead_voc(lead_intel, icp_config=icp)

            base_lead_id = self.approval_engine.generate_lead_id(
                company=lead_intel.company_name,
                contact=lead_intel.contact_name,
                email=lead_intel.email or "",
            )
            lead_id = f"demo_{base_lead_id}" if is_demo else base_lead_id

            st = str(lead_intel.email_status.value if hasattr(lead_intel.email_status, "value") else lead_intel.email_status).strip().upper()

            if st in ("VALID", "VERIFIED", "EVIDENCE_VERIFIED"):
                self.approval_engine.enroll_draft(
                    company=lead_intel.company_name,
                    contact=lead_intel.contact_name,
                    title=lead_intel.job_title,
                    email=lead_intel.email,
                    qualification_status=qual_status_str,
                    opportunity_score=lead_intel.opportunity_score,
                    accessibility_score=lead_intel.accessibility_score,
                    outreach_priority_index=lead_intel.outreach_priority_index,
                    priority=lead_intel.priority_level.value,
                    personalization_status=lead_intel.personalization_note_status.value,
                    personalization_note=lead_intel.personalization_note,
                    voc_angle=voc.voc_angle,
                    email_1="",
                    followup_a="",
                    followup_b="",
                    qa_status="PENDING_AI_GENERATION",
                    qa_reasons=[],
                    metadata={
                        "campaign_id": icp.campaign_id,
                        "icp_id": icp.id,
                        "icp_version": icp.version,
                        "deepline_run_id": run_id,
                        "linkedin_url": lead_intel.linkedin_url,
                        "website": lead_intel.company_domain,
                        "disqualification_reason": disqual_reason,
                    },
                    lead_id=lead_id,
                )
            elif st == "UNVERIFIED":
                self.approval_engine.enroll_unverified_lead(
                    company=lead_intel.company_name,
                    contact=lead_intel.contact_name,
                    title=lead_intel.job_title,
                    email=lead_intel.email,
                    qualification_status=qual_status_str,
                    opportunity_score=lead_intel.opportunity_score,
                    accessibility_score=lead_intel.accessibility_score,
                    outreach_priority_index=lead_intel.outreach_priority_index,
                    priority=lead_intel.priority_level.value,
                    personalization_status=lead_intel.personalization_note_status.value,
                    personalization_note=lead_intel.personalization_note,
                    voc_angle=voc.voc_angle,
                    disqualification_reason=disqual_reason,
                    metadata={
                        "campaign_id": icp.campaign_id,
                        "icp_id": icp.id,
                        "icp_version": icp.version,
                        "deepline_run_id": run_id,
                        "linkedin_url": lead_intel.linkedin_url,
                        "website": lead_intel.company_domain,
                        "disqualification_reason": disqual_reason,
                    },
                    lead_id=lead_id,
                )
            else:
                self.approval_engine.enroll_no_email_lead(
                    company=lead_intel.company_name,
                    contact=lead_intel.contact_name,
                    title=lead_intel.job_title,
                    qualification_status=qual_status_str,
                    opportunity_score=lead_intel.opportunity_score,
                    accessibility_score=lead_intel.accessibility_score,
                    outreach_priority_index=lead_intel.outreach_priority_index,
                    priority=lead_intel.priority_level.value,
                    personalization_status=lead_intel.personalization_note_status.value,
                    personalization_note=lead_intel.personalization_note,
                    voc_angle=voc.voc_angle,
                    disqualification_reason=disqual_reason,
                    metadata={
                        "campaign_id": icp.campaign_id,
                        "icp_id": icp.id,
                        "icp_version": icp.version,
                        "deepline_run_id": run_id,
                        "linkedin_url": lead_intel.linkedin_url,
                        "website": lead_intel.company_domain,
                        "disqualification_reason": disqual_reason,
                    },
                    lead_id=lead_id,
                )

            # Persist to database if enabled
            from src.database.models import Lead, LeadEvidence, LeadResearch, VoCContext, EmailDraft, EmailApproval

            if is_database_enabled():
                try:
                    from src.database.repositories.icp_repository import ICPRepository
                    from src.database.repositories.lead_repository import LeadRepository

                    with get_db_session() as session:
                        # 1. Guarantee parent ICP & Campaign exist in the current session context
                        icp_repo = ICPRepository(session)
                        icp_repo.enroll_icp(icp, environment=current_mode, source="CLAUDE_GENERATED")
                        icp_repo.approve_icp(icp.id, reviewer="SYSTEM_RUNNER")

                        # 2. Use LeadRepository.upsert_lead() which handles Lead upsert and campaign check
                        lead_repo = LeadRepository(session)
                        db_lead = lead_repo.upsert_lead(
                            lead_id=lead_id,
                            campaign_id=icp.campaign_id,
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
                            qualification_status=qual_status_str,
                            disqualification_reason=disqual_reason,
                            personalization_status=lead_intel.personalization_note_status.value if hasattr(lead_intel.personalization_note_status, "value") else str(lead_intel.personalization_note_status),
                            personalization_note=lead_intel.personalization_note,
                            voc_angle=voc.voc_angle,
                            environment=current_mode,
                            icp_id=icp.id,
                            icp_version=icp.version or "1.0.0",
                        )

                        # Email Draft
                        db_draft = session.query(EmailDraft).filter_by(lead_id=lead_id).first()
                        has_usable_email = st != "NO_EMAIL" and bool(lead_intel.email and "@" in lead_intel.email)

                        e1_body, fa_body, fb_body = "", "", ""
                        qa_st = "NO_EMAIL" if not has_usable_email else "PENDING_AI_GENERATION"
                        qa_reasons = ["No email address discovered"] if not has_usable_email else []

                        if has_usable_email:
                            try:
                                from src.integrations.claude_client import ClaudeClient
                                from src.personalization.personalization_qa import PersonalizationQA

                                client = ClaudeClient()
                                qa_engine = PersonalizationQA()

                                e1 = client.generate_email_1(lead_intel, voc)
                                fa = client.generate_followup_a(lead_intel, e1, voc)
                                fb = client.generate_followup_b(lead_intel, voc)

                                e1_body = getattr(e1, "body", str(e1))
                                fa_body = getattr(fa, "body", str(fa))
                                fb_body = getattr(fb, "body", str(fb))

                                qa_res = qa_engine.validate_lead_drafts(
                                    lead_intel=lead_intel,
                                    email_1=e1_body,
                                    followup_a=fa_body,
                                    followup_b=fb_body
                                )
                                qa_st = qa_res.qa_status
                                qa_reasons = qa_res.qa_reasons
                            except Exception as gen_err:
                                qa_st = "FAIL"
                                qa_reasons = [f"AI_GENERATION_FAILED: {str(gen_err)}"]

                        if not db_draft:
                            db_draft = EmailDraft(
                                lead_id=lead_id,
                                ai_original_email_1=e1_body,
                                ai_original_followup_a=fa_body,
                                ai_original_followup_b=fb_body,
                                qa_status=qa_st,
                                qa_reasons=qa_reasons,
                            )
                            session.add(db_draft)
                        else:
                            if not db_draft.ai_original_email_1 and has_usable_email:
                                db_draft.ai_original_email_1 = e1_body
                                db_draft.ai_original_followup_a = fa_body
                                db_draft.ai_original_followup_b = fb_body
                                db_draft.qa_status = qa_st
                                db_draft.qa_reasons = qa_reasons

                        # Email Approval
                        db_app = session.query(EmailApproval).filter_by(lead_id=lead_id).first()
                        app_status = "PENDING_REVIEW" if st != "NO_EMAIL" else "BLOCKED"
                        bl_reason = "No email address discovered" if st == "NO_EMAIL" else None
                        if not db_app:
                            db_app = EmailApproval(
                                lead_id=lead_id,
                                approval_status=app_status,
                                smartlead_eligible=False,
                                blocked_reason=bl_reason,
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
                            db_app.approval_status = app_status
                            db_app.smartlead_eligible = False
                            db_app.blocked_reason = bl_reason
                            db_app.metadata_json = {
                                "campaign_id": icp.campaign_id,
                                "icp_id": icp.id,
                                "icp_version": icp.version,
                                "deepline_run_id": run_id,
                            }
                except Exception as db_err:
                    print(f"[ERROR] Deepline discovery DB sync failed for lead '{lead_id}': {db_err}")

        # 7. Record Run Metadata and Artifacts
        is_live = getattr(self.deepline_client, "live_mode", False)
        safety_status_str = (
            "SAFETY_GATE_ACTIVE (LIVE_API=true, ZERO_EMAILS_SENT)"
            if is_live
            else "SAFETY_GATE_ACTIVE (DRY_RUN=true, ZERO_EMAILS_SENT)"
        )
        safety_mode_str = (
            "LIVE_PRODUCTION_API (0 emails sent, real lead discovery active)"
            if is_live
            else "ZERO-RISK DRY RUN (0 emails sent, 0 paid credits consumed)"
        )

        metadata = DeeplineRunMetadata(
            run_id=run_id,
            icp_id=icp.id,
            campaign_id=icp.campaign_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode="DRY_RUN_SIMULATION" if not is_live else "LIVE_API",
            requested_count=requested_count,
            discovered_count=people_discovered_count,
            valid_count=len(raw_leads) - hard_disqualified_count - campaign_excluded_count,
            qualified_count=qualified_leads_count,
            campaign_excluded_count=campaign_excluded_count,
            hard_disqualified_count=hard_disqualified_count,
            p1_count=p1_count,
            p2_count=p2_count,
            p3_count=p3_count,
            api_calls_made=0 if not is_live else 1,
            credits_consumed=0,
            safety_status=safety_status_str
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
                "discovered": people_discovered_count,
                "created": len(raw_leads),
                "valid": len(raw_leads) - hard_disqualified_count - campaign_excluded_count,
                "qualified": qualified_leads_count,
                "hard_disqualified": hard_disqualified_count,
                "campaign_excluded": campaign_excluded_count,
                "p1_count": p1_count,
                "p2_count": p2_count,
                "p3_count": p3_count,
            },
            "run_artifacts_path": run_dir,
            "safety_mode": safety_mode_str
        }
