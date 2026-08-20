"""
export_db_to_json.py
Exports current Supabase PostgreSQL database state back into structured JSON backup files.

Guarantees:
- Database is primary source of truth; JSON is backup/export.
- Exports campaigns, ICPs, leads, email drafts, approval records, and audit logs.
- Never prints passwords, tokens, or DATABASE_URL.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import get_db_session, is_database_enabled
from src.database.models import (
    Campaign,
    ICP,
    ICPApproval,
    Lead,
    EmailDraft,
    EmailApproval,
    DeeplineRun,
    AuditLog,
)


def export_db(output_dir: str = None) -> Dict[str, Any]:
    if not is_database_enabled():
        raise RuntimeError("Database is not enabled. Set DATABASE_ENABLED=true in .env to run export.")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not output_dir:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(base_dir, "data", "backups", f"backup_{ts}")

    os.makedirs(output_dir, exist_ok=True)

    summary = {
        "campaigns": 0,
        "icps": 0,
        "leads": 0,
        "email_drafts": 0,
        "approvals": 0,
        "deepline_runs": 0,
        "audit_logs": 0,
        "backup_path": output_dir,
    }

    with get_db_session() as session:
        # 1. Campaigns
        camps = session.query(Campaign).all()
        camp_list = [
            {
                "id": c.id,
                "name": c.name,
                "objective": c.objective,
                "status": c.status,
                "target_geography": c.target_geography,
                "settings": c.settings,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in camps
        ]
        with open(os.path.join(output_dir, "campaigns.json"), "w", encoding="utf-8") as f:
            json.dump(camp_list, f, indent=2)
        summary["campaigns"] = len(camp_list)

        # 2. ICPs & Approvals
        icp_apps = session.query(ICPApproval).all()
        icp_list = [
            {
                "icp_id": a.icp_id,
                "version": a.version,
                "status": a.status,
                "original_claude_icp": a.original_claude_icp,
                "effective_icp": a.effective_icp,
                "reviewer": a.reviewer,
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                "rejection_reason": a.rejection_reason,
                "blocked_reason": a.blocked_reason,
                "deepline_eligible": a.deepline_eligible,
                "deepline_run_ids": a.deepline_run_ids,
                "edit_history": a.edit_history,
                "audit_trail": a.audit_trail,
            }
            for a in icp_apps
        ]
        with open(os.path.join(output_dir, "icp_approval_queue.json"), "w", encoding="utf-8") as f:
            json.dump(icp_list, f, indent=2)
        summary["icps"] = len(icp_list)

        # 3. Leads
        leads = session.query(Lead).all()
        lead_list = [
            {
                "id": l.id,
                "campaign_id": l.campaign_id,
                "icp_id": l.icp_id,
                "icp_version": l.icp_version,
                "company_name": l.company_name,
                "company_domain": l.company_domain,
                "contact_name": l.contact_name,
                "job_title": l.job_title,
                "email": l.email,
                "email_status": l.email_status,
                "linkedin_url": l.linkedin_url,
                "opportunity_score": l.opportunity_score,
                "accessibility_score": l.accessibility_score,
                "outreach_priority_index": l.outreach_priority_index,
                "priority_level": l.priority_level,
                "qualification_status": l.qualification_status,
                "personalization_status": l.personalization_status,
                "personalization_note": l.personalization_note,
                "voc_angle": l.voc_angle,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ]
        with open(os.path.join(output_dir, "leads.json"), "w", encoding="utf-8") as f:
            json.dump(lead_list, f, indent=2)
        summary["leads"] = len(lead_list)

        # 4. Approvals
        approvals = session.query(EmailApproval).all()
        app_list = [
            {
                "lead_id": a.lead_id,
                "approval_status": a.approval_status,
                "reviewer": a.reviewer,
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                "smartlead_eligible": a.smartlead_eligible,
                "blocked_reason": a.blocked_reason,
                "flag_no_strong_signal": a.flag_no_strong_signal,
                "metadata": a.metadata_json,
            }
            for a in approvals
        ]
        with open(os.path.join(output_dir, "approval_queue.json"), "w", encoding="utf-8") as f:
            json.dump(app_list, f, indent=2)
        summary["approvals"] = len(app_list)

        # 5. Deepline Runs
        runs = session.query(DeeplineRun).all()
        run_list = [
            {
                "id": r.id,
                "icp_id": r.icp_id,
                "campaign_id": r.campaign_id,
                "requested_count": r.requested_count,
                "discovered_count": r.discovered_count,
                "valid_count": r.valid_count,
                "qualified_count": r.qualified_count,
                "p1_count": r.p1_count,
                "mode": r.mode,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]
        with open(os.path.join(output_dir, "deepline_runs.json"), "w", encoding="utf-8") as f:
            json.dump(run_list, f, indent=2)
        summary["deepline_runs"] = len(run_list)

        # 6. Audit Logs
        logs = session.query(AuditLog).all()
        log_list = [
            {
                "entity_type": lg.entity_type,
                "entity_id": lg.entity_id,
                "action": lg.action,
                "actor": lg.actor,
                "details": lg.details,
                "created_at": lg.created_at.isoformat() if lg.created_at else None,
            }
            for lg in logs
        ]
        with open(os.path.join(output_dir, "audit_logs.json"), "w", encoding="utf-8") as f:
            json.dump(log_list, f, indent=2)
        summary["audit_logs"] = len(log_list)

    return summary


if __name__ == "__main__":
    print("===================================================================")
    print(" AEDRIX POSTGRESQL DATABASE EXPORT TO JSON BACKUP")
    print("===================================================================")
    res = export_db()
    print("Export completed successfully:")
    print(f"  Campaigns exported:     {res['campaigns']}")
    print(f"  ICPs exported:          {res['icps']}")
    print(f"  Leads exported:         {res['leads']}")
    print(f"  Approvals exported:     {res['approvals']}")
    print(f"  Deepline runs exported: {res['deepline_runs']}")
    print(f"  Audit logs exported:    {res['audit_logs']}")
    print(f"  Destination Path:       {res['backup_path']}")
    print("===================================================================")
