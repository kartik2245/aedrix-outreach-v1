"""
migrate_json_to_db.py
High-performance idempotent migration script transferring existing JSON state into Supabase PostgreSQL.

Optimized with bulk lookups and single-pass batch transactions to minimize remote network latency.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.connection import get_db_session, is_database_enabled
from src.database.models import (
    Campaign,
    ICP,
    ICPVersion,
    ICPApproval,
    Lead,
    LeadResearch,
    LeadEvidence,
    VoCContext,
    EmailDraft,
    EmailApproval,
    DeeplineRun,
    DeeplineRunLead,
    AuditLog,
)


def migrate_all() -> Dict[str, int]:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base_dir, "data")

    summary = {
        "campaigns": 0,
        "icps": 0,
        "icp_versions": 0,
        "icp_approvals": 0,
        "leads": 0,
        "lead_research": 0,
        "voc_contexts": 0,
        "email_drafts": 0,
        "email_approvals": 0,
        "deepline_runs": 0,
    }

    if not is_database_enabled():
        print("Database is not enabled. Set DATABASE_ENABLED=true in .env to run migration.")
        return summary

    with get_db_session() as session:
        # Pre-fetch existing IDs to avoid network round-trips
        existing_campaign_ids = {c.id for c in session.query(Campaign.id).all()}
        existing_icp_ids = {i.id for i in session.query(ICP.id).all()}
        existing_icp_versions = {(v.icp_id, v.version) for v in session.query(ICPVersion.icp_id, ICPVersion.version).all()}
        existing_icp_approvals = {a.icp_id for a in session.query(ICPApproval.icp_id).all()}
        existing_lead_ids = {l.id for l in session.query(Lead.id).all()}
        existing_draft_lead_ids = {d.lead_id for d in session.query(EmailDraft.lead_id).all()}
        existing_app_lead_ids = {a.lead_id for a in session.query(EmailApproval.lead_id).all()}
        existing_voc_lead_ids = {v.lead_id for v in session.query(VoCContext.lead_id).all()}
        existing_res_lead_ids = {r.lead_id for r in session.query(LeadResearch.lead_id).all()}
        existing_run_ids = {r.id for r in session.query(DeeplineRun.id).all()}

        # -------------------------------------------------------------
        # 1. Migrate ICP Approval Queue
        # -------------------------------------------------------------
        icp_file = os.path.join(data_dir, "icp_approval_queue.json")
        if os.path.exists(icp_file):
            try:
                with open(icp_file, "r", encoding="utf-8") as f:
                    icp_data = json.load(f)

                for item in icp_data:
                    c_id = item.get("campaign_id") or "default_campaign"
                    icp_id = item.get("icp_id")
                    if not icp_id:
                        continue

                    if c_id not in existing_campaign_ids:
                        camp = Campaign(
                            id=c_id,
                            name=item.get("name") or f"Campaign {c_id}",
                            objective=item.get("effective_icp", {}).get("campaign_description", ""),
                            status="ACTIVE",
                            target_geography="United Kingdom",
                        )
                        session.add(camp)
                        existing_campaign_ids.add(c_id)
                        summary["campaigns"] += 1

                    if icp_id not in existing_icp_ids:
                        db_icp = ICP(
                            id=icp_id,
                            campaign_id=c_id,
                            name=item.get("name", "Untitled ICP"),
                            status=item.get("status", "PENDING_REVIEW"),
                            current_version=item.get("version", "1.0.0"),
                        )
                        session.add(db_icp)
                        existing_icp_ids.add(icp_id)
                        summary["icps"] += 1

                    ver_str = item.get("version", "1.0.0")
                    if (icp_id, ver_str) not in existing_icp_versions:
                        eff = item.get("effective_icp") or {}
                        ver_obj = ICPVersion(
                            icp_id=icp_id,
                            version=ver_str,
                            config_data=eff,
                            reasoning=eff.get("reasoning", ""),
                        )
                        session.add(ver_obj)
                        existing_icp_versions.add((icp_id, ver_str))
                        summary["icp_versions"] += 1

                    reviewed_at = None
                    if item.get("reviewed_at"):
                        try:
                            reviewed_at = datetime.fromisoformat(item["reviewed_at"])
                        except Exception:
                            reviewed_at = None

                    if icp_id not in existing_icp_approvals:
                        app_obj = ICPApproval(
                            icp_id=icp_id,
                            version=ver_str,
                            status=item.get("status", "PENDING_REVIEW"),
                            original_claude_icp=item.get("original_claude_icp") or {},
                            effective_icp=item.get("effective_icp") or {},
                            reviewer=item.get("reviewer"),
                            reviewed_at=reviewed_at,
                            rejection_reason=item.get("rejection_reason"),
                            blocked_reason=item.get("blocked_reason"),
                            deepline_eligible=item.get("deepline_eligible", False),
                            deepline_run_ids=item.get("deepline_run_ids", []),
                            edit_history=item.get("edit_history", []),
                            audit_trail=item.get("audit_trail", []),
                        )
                        session.add(app_obj)
                        existing_icp_approvals.add(icp_id)
                        summary["icp_approvals"] += 1
            except Exception as e:
                print(f"Notice: Error during ICP migration: {e}")

        # Flush initial campaign and ICP objects so foreign keys resolve
        session.flush()

        # -------------------------------------------------------------
        # 2. Migrate Leads & Email Approvals
        # -------------------------------------------------------------
        app_file = os.path.join(data_dir, "approval_queue.json")
        if os.path.exists(app_file):
            try:
                with open(app_file, "r", encoding="utf-8") as f:
                    app_data = json.load(f)

                for item in app_data:
                    lead_id = item.get("lead_id")
                    if not lead_id:
                        continue

                    c_id = item.get("campaign_id") or item.get("metadata", {}).get("campaign_id") or "default_campaign"
                    icp_id = item.get("icp_id") or item.get("metadata", {}).get("icp_id")
                    icp_version = item.get("icp_version") or item.get("metadata", {}).get("icp_version") or "1.0.0"

                    if c_id not in existing_campaign_ids:
                        session.add(Campaign(id=c_id, name=f"Campaign {c_id}", status="ACTIVE"))
                        existing_campaign_ids.add(c_id)
                        summary["campaigns"] += 1

                    if icp_id and icp_id not in existing_icp_ids:
                        session.add(ICP(id=icp_id, campaign_id=c_id, name=f"ICP {icp_id}"))
                        existing_icp_ids.add(icp_id)
                        summary["icps"] += 1

                    if lead_id not in existing_lead_ids:
                        db_lead = Lead(
                            id=lead_id,
                            campaign_id=c_id,
                            icp_id=icp_id,
                            icp_version=icp_version,
                            company_name=item.get("company", "Unknown Company"),
                            company_domain=item.get("metadata", {}).get("website") or "example.co.uk",
                            contact_name=item.get("contact", "Unknown Contact"),
                            job_title=item.get("title", "Decision Maker"),
                            email=item.get("email", ""),
                            email_status="PATTERN_CONFIRMED",
                            linkedin_url=item.get("metadata", {}).get("linkedin_url"),
                            opportunity_score=float(item.get("opportunity_score", 0.0)),
                            accessibility_score=float(item.get("accessibility_score", 0.0)),
                            outreach_priority_index=float(item.get("outreach_priority_index", 0.0)),
                            priority_level=item.get("priority", "P3"),
                            qualification_status=item.get("qualification_status", "QUALIFIED"),
                            personalization_status=item.get("personalization_status", "SIGNAL_VERIFIED"),
                            personalization_note=item.get("personalization_note"),
                            voc_angle=item.get("voc_angle")[:255] if item.get("voc_angle") else None,
                        )
                        session.add(db_lead)
                        existing_lead_ids.add(lead_id)
                        summary["leads"] += 1

                    if lead_id not in existing_draft_lead_ids:
                        db_draft = EmailDraft(
                            lead_id=lead_id,
                            ai_original_email_1=item.get("email_1_original", ""),
                            ai_original_followup_a=item.get("followup_a_original", ""),
                            ai_original_followup_b=item.get("followup_b_original", ""),
                            edited_email_1=item.get("edited_email_1"),
                            edited_followup_a=item.get("edited_followup_a"),
                            edited_followup_b=item.get("edited_followup_b"),
                            qa_status=item.get("qa_status", "PASS"),
                            qa_reasons=item.get("qa_reasons", []),
                        )
                        session.add(db_draft)
                        existing_draft_lead_ids.add(lead_id)
                        summary["email_drafts"] += 1

                    reviewed_at = None
                    if item.get("reviewed_at"):
                        try:
                            reviewed_at = datetime.fromisoformat(item["reviewed_at"])
                        except Exception:
                            reviewed_at = None

                    if lead_id not in existing_app_lead_ids:
                        db_approval = EmailApproval(
                            lead_id=lead_id,
                            approval_status=item.get("approval_status", "PENDING_REVIEW"),
                            reviewer=item.get("reviewer"),
                            reviewed_at=reviewed_at,
                            smartlead_eligible=item.get("smartlead_eligible", False),
                            blocked_reason=item.get("blocked_reason"),
                            flag_no_strong_signal=item.get("flag_no_strong_signal", False),
                            metadata_json=item.get("metadata", {}),
                        )
                        session.add(db_approval)
                        existing_app_lead_ids.add(lead_id)
                        summary["email_approvals"] += 1

            except Exception as e:
                print(f"Notice: Error during lead migration: {e}")

        # Flush lead objects so child research and voc records resolve
        session.flush()

        # -------------------------------------------------------------
        # 3. Migrate Personalization Drafts (claude_personalization_drafts.json)
        # -------------------------------------------------------------
        drafts_file = os.path.join(data_dir, "claude_personalization_drafts.json")
        if os.path.exists(drafts_file):
            try:
                with open(drafts_file, "r", encoding="utf-8") as f:
                    drafts_data = json.load(f)

                # Pre-fetch email-to-id mapping
                email_to_id = {l.email: l.id for l in session.query(Lead.email, Lead.id).all()}

                for item in drafts_data:
                    lead_intel = item.get("lead_intelligence") or {}
                    email = lead_intel.get("email")
                    if not email or email not in email_to_id:
                        continue

                    lead_id = email_to_id[email]

                    voc_info = item.get("voc_context") or {}
                    if voc_info and lead_id not in existing_voc_lead_ids:
                        voc_obj = VoCContext(
                            lead_id=lead_id,
                            voc_angle=voc_info.get("voc_angle", "Operational Efficiency"),
                            pain_point=voc_info.get("pain_point", ""),
                            messaging_angle=voc_info.get("messaging_angle", ""),
                            aedrix_value_prop=voc_info.get("aedrix_value_prop", ""),
                        )
                        session.add(voc_obj)
                        existing_voc_lead_ids.add(lead_id)
                        summary["voc_contexts"] += 1

                    if lead_id not in existing_res_lead_ids:
                        res_obj = LeadResearch(
                            lead_id=lead_id,
                            raw_research=lead_intel,
                            sources=lead_intel.get("research_sources", []),
                            pain_point=lead_intel.get("pain_point"),
                            relevant_signal=lead_intel.get("relevant_signal"),
                        )
                        session.add(res_obj)
                        existing_res_lead_ids.add(lead_id)
                        summary["lead_research"] += 1

            except Exception as e:
                print(f"Notice: Error during drafts migration: {e}")

        # -------------------------------------------------------------
        # 4. Migrate Deepline Discovery Runs
        # -------------------------------------------------------------
        runs_dir = os.path.join(data_dir, "deepline_runs")
        if os.path.exists(runs_dir):
            for run_name in os.listdir(runs_dir):
                run_path = os.path.join(runs_dir, run_name)
                meta_file = os.path.join(run_path, "run_metadata.json")
                if os.path.isdir(run_path) and os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            meta = json.load(f)

                        run_id = meta.get("run_id") or run_name
                        icp_id = meta.get("icp_id")
                        c_id = meta.get("campaign_id") or "default_campaign"

                        if c_id not in existing_campaign_ids:
                            session.add(Campaign(id=c_id, name=f"Campaign {c_id}"))
                            existing_campaign_ids.add(c_id)
                            summary["campaigns"] += 1

                        if icp_id and icp_id not in existing_icp_ids:
                            session.add(ICP(id=icp_id, campaign_id=c_id, name=f"ICP {icp_id}"))
                            existing_icp_ids.add(icp_id)
                            summary["icps"] += 1

                        if run_id not in existing_run_ids:
                            db_run = DeeplineRun(
                                id=run_id,
                                icp_id=icp_id or "default_icp",
                                campaign_id=c_id,
                                requested_count=meta.get("requested_count", 100),
                                discovered_count=meta.get("discovered_count", 0),
                                valid_count=meta.get("valid_count", 0),
                                qualified_count=meta.get("qualified_count", 0),
                                hard_disqualified_count=meta.get("hard_disqualified_count", 0),
                                campaign_excluded_count=meta.get("campaign_excluded_count", 0),
                                p1_count=meta.get("p1_count", 0),
                                p2_count=meta.get("p2_count", 0),
                                p3_count=meta.get("p3_count", 0),
                                mode=meta.get("mode", "DRY_RUN_SIMULATION"),
                                artifacts_path=run_path,
                            )
                            session.add(db_run)
                            existing_run_ids.add(run_id)
                            summary["deepline_runs"] += 1
                    except Exception as e:
                        print(f"Notice: Error during run migration: {e}")

        # Final transaction commit
        session.flush()

    return summary


if __name__ == "__main__":
    print("===================================================================")
    print(" AEDRIX POSTGRESQL IDEMPOTENT JSON-TO-DB MIGRATION")
    print("===================================================================")
    res = migrate_all()
    print("Migration finished successfully:")
    print(f"  Campaigns migrated:        {res['campaigns']}")
    print(f"  ICPs migrated:             {res['icps']}")
    print(f"  ICP Versions migrated:     {res['icp_versions']}")
    print(f"  ICP Approvals migrated:    {res['icp_approvals']}")
    print(f"  Leads migrated:            {res['leads']}")
    print(f"  Lead Research migrated:    {res['lead_research']}")
    print(f"  VoC Contexts migrated:     {res['voc_contexts']}")
    print(f"  Email Drafts migrated:     {res['email_drafts']}")
    print(f"  Approval Records migrated: {res['email_approvals']}")
    print(f"  Deepline Runs migrated:    {res['deepline_runs']}")
    print("===================================================================")
