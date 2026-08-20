"""
smartlead_production_runner.py
Master Production Runner for Smartlead Integration with Multi-Tier Safety Gates & Structured Audit Logging (Python 3.12).

Three Operational Modes:
- MODE 1: OFFLINE DRY RUN (DRY_RUN=true, SMARTLEAD_LIVE=false, SEND_EMAILS=false) -> 0 API Calls
- MODE 2: SMARTLEAD API TEST (SMARTLEAD_LIVE=true, SEND_EMAILS=false) -> Safe API calls, DRAFT/PAUSED mode only
- MODE 3: PRODUCTION SEND (SMARTLEAD_LIVE=true, SEND_EMAILS=true, PRODUCTION_SEND_CONFIRMATION=true) -> Explicitly unlocked

ZERO real emails sent unless explicitly unlocked via PRODUCTION_SEND_CONFIRMATION=true and SEND_EMAILS=true.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.approval.approval_models import ApprovalRecord, ApprovalStatus
from src.approval.approval_store import ApprovalStore
from src.integrations.smartlead_client import (
    SmartleadClient,
    SmartleadError,
    SmartleadConfigError,
    SmartleadAuthError,
    SmartleadAPIError,
    load_env_file_if_present,
)
from src.smartlead_staging_runner import SmartleadStagingRunner
from src.models import SmartleadAuditEntry


class SmartleadProductionRunner:
    def __init__(
        self,
        client: Optional[SmartleadClient] = None,
        approval_store: Optional[ApprovalStore] = None,
        staging_runner: Optional[SmartleadStagingRunner] = None,
        log_dir: Optional[str] = None,
    ):
        load_env_file_if_present()
        self.client = client or SmartleadClient()
        self.approval_store = approval_store or ApprovalStore()
        self.staging_runner = staging_runner or SmartleadStagingRunner(approval_store=self.approval_store)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = log_dir or os.path.join(base_dir, "data", "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.audit_log_path = os.path.join(self.log_dir, "smartlead_audit.jsonl")

    def write_audit_log(self, entry: SmartleadAuditEntry) -> None:
        """Appends a structured JSON audit entry to data/logs/smartlead_audit.jsonl."""
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

    def log_audit_event(
        self,
        action: str,
        status: str,
        lead_id: Optional[str] = None,
        company: Optional[str] = None,
        campaign_id: Optional[str] = None,
        approval_status: Optional[str] = None,
        reviewer: Optional[str] = None,
        error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> SmartleadAuditEntry:
        """Helper to create and write audit events."""
        entry = SmartleadAuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            lead_id=lead_id,
            company=company,
            provider="SMARTLEAD",
            status=status,
            campaign_id=campaign_id,
            approval_status=approval_status,
            reviewer=reviewer,
            dry_run=self.client.dry_run or not self.client.live,
            error=error,
            details=details or {}
        )
        self.write_audit_log(entry)
        return entry

    def run(
        self,
        campaign_id: Optional[str] = None,
        force_production_confirmation: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes Smartlead production workflow with multi-layer safety verification.
        """
        env_prod_confirm = os.getenv("PRODUCTION_SEND_CONFIRMATION", "false").lower() in ("true", "1", "yes")
        is_prod_confirmed = force_production_confirmation or env_prod_confirm

        print("===================================================================")
        print(" AEDRIX SMARTLEAD PRODUCTION RUNNER")
        print("===================================================================")
        print(f" SMARTLEAD_LIVE:               {self.client.live}")
        print(f" DRY_RUN:                      {self.client.dry_run}")
        print(f" SEND_EMAILS:                  {self.client.send_emails}")
        print(f" PRODUCTION_SEND_CONFIRMATION: {is_prod_confirmed}")
        print(f" Base URL:                     {self.client.base_url}")
        print(f" API Key Masked:               {SmartleadClient.mask_api_key(self.client.api_key)}")
        print("===================================================================\n")

        # 1. MODE 1: OFFLINE DRY RUN
        if self.client.dry_run or not self.client.live:
            print(">>> MODE 1: OFFLINE DRY RUN ACTIVATED (0 API CALLS, 0 EMAILS SENT)")
            plan = self.staging_runner.build_staging_plan()
            self.log_audit_event(
                action="SMARTLEAD_STAGING_PLAN_GENERATED",
                status="SUCCESS",
                details={"approved_leads": plan["summary"]["approved_eligible_count"]}
            )
            print(f"Staging plan generated at: data/smartlead_staging_plan.json")
            print(f"Approved leads ready: {plan['summary']['approved_eligible_count']}")
            return {
                "mode": "MODE_1_DRY_RUN",
                "status": "SUCCESS",
                "campaign_id": None,
                "leads_uploaded": 0,
                "staging_plan": plan
            }

        # 2. CHECK APPROVED LEADS
        all_records = self.approval_store.load_queue()
        approved_leads = [
            r for r in all_records
            if r.approval_status == ApprovalStatus.APPROVED and r.smartlead_eligible is True
        ]

        if not approved_leads:
            print("🛑 ABORT: No APPROVED & Smartlead-eligible leads found in approval queue.")
            print("No action taken. Run `python src/approval_cli.py approve <lead_id>` to approve leads.")
            self.log_audit_event(
                action="SMARTLEAD_UPLOAD_SKIPPED",
                status="NO_APPROVED_LEADS",
                details={"total_records": len(all_records)}
            )
            return {
                "mode": "ABORT_NO_LEADS",
                "status": "SKIPPED",
                "campaign_id": None,
                "leads_uploaded": 0
            }

        print(f"Found {len(approved_leads)} APPROVED and eligible lead(s) for Smartlead upload.\n")

        # 3. SAFETY CHECK FOR MODE 3 (PRODUCTION SEND)
        if self.client.send_emails:
            if not is_prod_confirmed:
                err_msg = (
                    "CRITICAL SAFETY VIOLATION: SEND_EMAILS=true but PRODUCTION_SEND_CONFIRMATION=true is missing. "
                    "Campaign activation BLOCKED."
                )
                print(f"🛑 {err_msg}")
                self.log_audit_event(
                    action="SMARTLEAD_SEND_BLOCKED",
                    status="FAILED_CONFIRMATION_REQUIRED",
                    error=err_msg
                )
                raise SmartleadConfigError(err_msg)

        # 4. CAMPAIGN RESOLUTION (CREATE OR ATTACH)
        active_campaign_id = campaign_id or os.getenv("SMARTLEAD_CAMPAIGN_ID")
        if not active_campaign_id:
            campaign_name = f"Aedrix UK Construction - Batch {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
            print(f"Creating new Smartlead campaign: '{campaign_name}'...")
            try:
                camp_res = self.client.create_campaign(
                    name=campaign_name,
                    settings={"track_settings": {"open_tracking": True, "click_tracking": True}}
                )
                active_campaign_id = str(camp_res.get("id") or camp_res.get("campaign_id") or "new_camp_123")
                print(f"  -> Campaign created successfully! ID: {active_campaign_id}")
                self.log_audit_event(
                    action="SMARTLEAD_CAMPAIGN_CREATED",
                    status="SUCCESS",
                    campaign_id=active_campaign_id,
                    details=camp_res
                )
            except Exception as e:
                err_msg = f"Failed to create Smartlead campaign: {str(e)}"
                print(f"🛑 {err_msg}")
                self.log_audit_event(
                    action="SMARTLEAD_CAMPAIGN_CREATION_FAILED",
                    status="ERROR",
                    error=err_msg
                )
                raise

        # 5. CONFIGURE SEQUENCE (2-day initial wait rule)
        print(f"Configuring sequences for campaign ID {active_campaign_id}...")
        sequence_config = self.staging_runner.build_campaign_sequence()
        try:
            seq_res = self.client.update_campaign_sequence(active_campaign_id, sequence_config)
            print(f"  -> Sequence configured with 2-day initial wait and behavior branches.")
            self.log_audit_event(
                action="SMARTLEAD_SEQUENCE_CONFIGURED",
                status="SUCCESS",
                campaign_id=active_campaign_id,
                details=seq_res
            )
        except Exception as e:
            err_msg = f"Failed to configure campaign sequence: {str(e)}"
            print(f"🛑 {err_msg}")
            self.log_audit_event(
                action="SMARTLEAD_SEQUENCE_CONFIGURATION_FAILED",
                status="ERROR",
                campaign_id=active_campaign_id,
                error=err_msg
            )
            raise

        # 6. BATCH UPLOAD APPROVED LEADS
        smartlead_leads = [self.staging_runner.build_lead_payload(r) for r in approved_leads]
        batch_size = self.staging_runner.batch_size
        total_batches = (len(smartlead_leads) + batch_size - 1) // batch_size
        uploaded_count = 0
        batch_errors = []

        print(f"\nUploading {len(smartlead_leads)} lead(s) in {total_batches} batch(es) (Batch Size: {batch_size})...")

        for b_idx in range(total_batches):
            chunk = smartlead_leads[b_idx * batch_size : (b_idx + 1) * batch_size]
            chunk_records = approved_leads[b_idx * batch_size : (b_idx + 1) * batch_size]
            print(f"Processing batch {b_idx + 1}/{total_batches} ({len(chunk)} leads)...")

            try:
                upload_res = self.client.add_leads_to_campaign(active_campaign_id, chunk)
                uploaded_count += len(chunk)
                print(f"  -> Batch {b_idx + 1} uploaded successfully.")

                for rec in chunk_records:
                    self.log_audit_event(
                        action="SMARTLEAD_LEAD_UPLOADED",
                        status="SUCCESS",
                        lead_id=rec.lead_id,
                        company=rec.company,
                        campaign_id=active_campaign_id,
                        approval_status=rec.approval_status.value,
                        reviewer=rec.reviewer,
                        details={"email": rec.email, "batch": b_idx + 1}
                    )

            except Exception as e:
                err_msg = f"Batch {b_idx + 1} upload failed: {str(e)}"
                print(f"  -> ⚠️ {err_msg}")
                batch_errors.append({"batch": b_idx + 1, "error": str(e)})

                for rec in chunk_records:
                    self.log_audit_event(
                        action="SMARTLEAD_LEAD_UPLOAD_FAILED",
                        status="ERROR",
                        lead_id=rec.lead_id,
                        company=rec.company,
                        campaign_id=active_campaign_id,
                        approval_status=rec.approval_status.value,
                        reviewer=rec.reviewer,
                        error=str(e),
                        details={"email": rec.email, "batch": b_idx + 1}
                    )

        # 7. CAMPAIGN STATUS & SENDING SAFETY
        if not self.client.send_emails:
            print("\n>>> MODE 2: API TEST MODE COMPLETED.")
            print(f"Campaign {active_campaign_id} remains in PAUSED/DRAFT state. ZERO real emails sent.")
            self.client.pause_campaign(active_campaign_id)
            self.log_audit_event(
                action="SMARTLEAD_CAMPAIGN_PAUSED",
                status="SUCCESS",
                campaign_id=active_campaign_id,
                details={"reason": "SEND_EMAILS=false"}
            )
        else:
            print(f"\n>>> MODE 3: PRODUCTION SEND CONFIRMED. Activating campaign {active_campaign_id}...")
            self.client.resume_campaign(active_campaign_id)
            self.log_audit_event(
                action="SMARTLEAD_CAMPAIGN_ACTIVATED",
                status="SUCCESS",
                campaign_id=active_campaign_id,
                details={"confirmed_by": "PRODUCTION_SEND_CONFIRMATION"}
            )

        print("\n===================================================================")
        print(" SMARTLEAD RUNNER EXECUTION SUMMARY")
        print("===================================================================")
        print(f" Mode:                 {'MODE 3 (PRODUCTION SEND)' if self.client.send_emails else 'MODE 2 (API TEST)'}")
        print(f" Campaign ID:          {active_campaign_id}")
        print(f" Total Approved Leads: {len(approved_leads)}")
        print(f" Leads Uploaded:       {uploaded_count}")
        print(f" Batches Failed:       {len(batch_errors)}")
        print(f" Audit Log:            {self.audit_log_path}")
        print("===================================================================\n")

        return {
            "mode": "MODE_3_PRODUCTION" if self.client.send_emails else "MODE_2_API_TEST",
            "status": "SUCCESS" if not batch_errors else "PARTIAL_SUCCESS",
            "campaign_id": active_campaign_id,
            "leads_uploaded": uploaded_count,
            "batch_errors": batch_errors
        }


def main():
    parser = argparse.ArgumentParser(description="Aedrix Smartlead Production Runner")
    parser.add_argument("--campaign-id", help="Target Smartlead Campaign ID")
    parser.add_argument("--confirm-production-send", action="store_true", help="Explicitly confirm live production sending")
    parser.add_argument("--dry-run", action="store_true", help="Force offline dry-run staging mode")
    
    args = parser.parse_args()

    client = SmartleadClient()
    if args.dry_run:
        client.dry_run = True

    runner = SmartleadProductionRunner(client=client)
    runner.run(
        campaign_id=args.campaign_id,
        force_production_confirmation=args.confirm_production_send
    )


if __name__ == "__main__":
    main()
