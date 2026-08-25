"""
smartlead_staging_runner.py

Offline Staging Runner for Smartlead Production Integration.

Reads approval records from the primary PostgreSQL / Supabase database
when DATABASE_ENABLED=True.

Falls back to data/approval_queue.json when the database is disabled
or unavailable.

Selects ONLY:
    APPROVED
    AND
    smartlead_eligible=True

Then constructs the Smartlead staging payload.

IMPORTANT SAFETY GUARANTEES:
    - ZERO Smartlead API calls
    - ZERO credits consumed
    - ZERO emails sent
    - DRY_RUN=True
    - SMARTLEAD_LIVE=False

The database-to-ApprovalRecord mapping is intentionally delegated to
ApprovalStore so that there is only ONE canonical mapping implementation.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------
# Ensure project root is available on PYTHONPATH
# ---------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(
    0,
    PROJECT_ROOT,
)


# ---------------------------------------------------------------------
# Windows UTF-8 output
# ---------------------------------------------------------------------

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8"
    )


# ---------------------------------------------------------------------
# Application imports
# ---------------------------------------------------------------------

from src.approval.approval_models import (
    ApprovalRecord,
    ApprovalStatus,
)

from src.approval.approval_store import (
    ApprovalStore,
)

from src.integrations.smartlead_client import (
    load_env_file_if_present,
)


class SmartleadStagingRunner:
    """
    Offline Smartlead staging runner.

    The runner NEVER communicates with Smartlead.

    Its responsibility is only to:

        1. Load the approval queue.
        2. Select APPROVED + eligible leads.
        3. Build the Smartlead-compatible payload.
        4. Build the campaign sequence.
        5. Write the staging plan to JSON.

    Database access and DB -> ApprovalRecord mapping are delegated
    entirely to ApprovalStore.
    """

    def __init__(
        self,
        approval_store: Optional[ApprovalStore] = None,
        batch_size: Optional[int] = None,
        campaign_name: str = (
            "Aedrix UK Construction - High Priority Main Contractors"
        ),
    ) -> None:

        # -------------------------------------------------------------
        # Load environment variables
        # -------------------------------------------------------------

        load_env_file_if_present()

        # -------------------------------------------------------------
        # Canonical approval store
        # -------------------------------------------------------------

        self.approval_store = (
            approval_store
            if approval_store is not None
            else ApprovalStore()
        )

        # -------------------------------------------------------------
        # Batch configuration
        # -------------------------------------------------------------

        try:
            env_batch_size = int(
                os.getenv(
                    "BATCH_SIZE",
                    "400",
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            env_batch_size = 400

        self.batch_size = (
            batch_size
            if batch_size is not None
            else env_batch_size
        )

        # Prevent invalid batch sizes.
        if self.batch_size <= 0:
            self.batch_size = 400

        self.campaign_name = campaign_name

    # =================================================================
    # LOAD APPROVAL RECORDS
    # =================================================================

    def _load_approval_records(
        self,
    ) -> List[ApprovalRecord]:
        """
        Loads approval records through the canonical ApprovalStore.

        ApprovalStore is responsible for:

            PostgreSQL / Supabase
                    |
                    v
            ApprovalRecord mapping
                    |
                    v
            JSON fallback

        IMPORTANT:

        We deliberately do NOT duplicate the database mapping logic
        here.

        This prevents schema mismatches between the Approval API,
        Smartlead staging, and the persistence layer.
        """

        return self.approval_store.load_queue()

    # =================================================================
    # BUILD SMARTLEAD LEAD PAYLOAD
    # =================================================================

    def build_lead_payload(
        self,
        record: ApprovalRecord,
    ) -> Dict[str, Any]:
        """
        Converts an ApprovalRecord into the Smartlead staging structure.

        No API calls are made here.
        """

        # -------------------------------------------------------------
        # Contact name
        # -------------------------------------------------------------

        contact = (
            record.contact.strip()
            if record.contact
            else ""
        )

        names = contact.split()

        first_name = (
            names[0]
            if names
            else ""
        )

        last_name = (
            " ".join(names[1:])
            if len(names) > 1
            else ""
        )

        # -------------------------------------------------------------
        # Email content
        #
        # Human edits take priority over AI-generated originals.
        # -------------------------------------------------------------

        email_1_body = (
            record.edited_email_1
            or record.email_1_original
            or ""
        )

        followup_a_body = (
            record.edited_followup_a
            or record.followup_a_original
            or ""
        )

        followup_b_body = (
            record.edited_followup_b
            or record.followup_b_original
            or ""
        )

        # -------------------------------------------------------------
        # Removed Touches 3, 4, 5
        # -------------------------------------------------------------


        # -------------------------------------------------------------
        # Subjects (Dynamic & ICP-Aware via sanitize_subject)
        # -------------------------------------------------------------
        from src.utils.subject_sanitizer import sanitize_subject

        industry_val = getattr(record, "industry", None) or (record.metadata.get("industry") if isinstance(getattr(record, "metadata", None), dict) else None)

        email_1_subject = sanitize_subject(
            getattr(record, "email_1_subject", None),
            company_name=record.company,
            product_or_industry=industry_val,
            voc_angle=record.voc_angle,
            email_type="EMAIL_1",
            max_words=6,
        )

        followup_a_subject = sanitize_subject(
            f"Re: {email_1_subject}",
            company_name=record.company,
            product_or_industry=industry_val,
            voc_angle=record.voc_angle,
            email_type="FOLLOWUP_A",
            max_words=6,
        )

        followup_b_subject = sanitize_subject(
            getattr(record, "followup_b_subject", None),
            company_name=record.company,
            product_or_industry=industry_val,
            voc_angle=record.voc_angle,
            email_type="FOLLOWUP_B",
            max_words=6,
        )

        # -------------------------------------------------------------
        # Custom fields
        # -------------------------------------------------------------

        custom_fields = {
            "lead_id": record.lead_id,
            "company_name": record.company,
            "job_title": record.title,

            "priority": record.priority,

            "opportunity_score": (
                record.opportunity_score
            ),

            "accessibility_score": (
                record.accessibility_score
            ),

            "outreach_priority_index": (
                record.outreach_priority_index
            ),

            "personalization_status": (
                record.personalization_status
            ),

            "personalization_note": (
                record.personalization_note
            ),

            "voc_angle": (
                record.voc_angle
            ),

            "email_1_subject": (
                email_1_subject
            ),

            "email_1_body": (
                email_1_body
            ),

            "followup_a_subject": (
                followup_a_subject
            ),

            "followup_a_body": (
                followup_a_body
            ),

            "followup_b_subject": (
                followup_b_subject
            ),

            "followup_b_body": (
                followup_b_body
            ),
        }

        # -------------------------------------------------------------
        # Website
        #
        # Never fabricate a website.
        # -------------------------------------------------------------

        website = (
            record.metadata.get(
                "website"
            )
            or record.metadata.get(
                "company_domain"
            )
            or None
        )

        # -------------------------------------------------------------
        # LinkedIn
        # -------------------------------------------------------------

        linkedin = (
            record.metadata.get(
                "linkedin_url"
            )
            or None
        )

        # -------------------------------------------------------------
        # Final Smartlead-compatible lead structure
        # -------------------------------------------------------------

        return {
            "email": record.email,

            "first_name": first_name,

            "last_name": last_name,

            "company_name": record.company,

            "website": website,

            "linkedin_profile": linkedin,

            "custom_fields": custom_fields,
        }

    # =================================================================
    # CAMPAIGN SEQUENCE
    # =================================================================

    def build_campaign_sequence(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Builds the campaign sequence.
        """

        return [
            {
                "seq_number": 1,

                "seq_delay_details": {
                    "delay_in_days": 0,
                },

                "subject": (
                    "{{email_1_subject}}"
                ),

                "body": (
                    "{{email_1_body}}"
                ),

                "step_type": (
                    "INITIAL_EMAIL"
                ),
            },

            {
                "seq_number": 2,

                "seq_delay_details": {
                    "delay_in_days": 2,
                },

                "subject": (
                    "{{followup_a_subject}}"
                ),

                "body": (
                    "{{followup_a_body}}"
                ),

                "step_type": (
                    "FOLLOW_UP_OPENED_BRANCH_A"
                ),

                "trigger_condition": (
                    "IF_OPENED_WITHIN_48_HOURS"
                ),
            },

            {
                "seq_number": 3,

                "seq_delay_details": {
                    "delay_in_days": 2,
                },

                "subject": (
                    "{{followup_b_subject}}"
                ),

                "body": (
                    "{{followup_b_body}}"
                ),

                "step_type": (
                    "FOLLOW_UP_UNOPENED_BRANCH_B"
                ),

                "trigger_condition": (
                    "IF_UNOPENED_AFTER_48_HOURS"
                ),
            },
        ]

    # =================================================================
    # BUILD STAGING PLAN
    # =================================================================

    def build_staging_plan(
        self,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds the complete offline Smartlead staging plan.

        The database is used through ApprovalStore when enabled.

        Only leads satisfying BOTH conditions are staged:

            approval_status == APPROVED
            smartlead_eligible == True
        """

        # -------------------------------------------------------------
        # Output path
        # -------------------------------------------------------------

        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )

        if not output_path:

            output_path = os.path.join(
                base_dir,
                "data",
                "smartlead_staging_plan.json",
            )

        # -------------------------------------------------------------
        # Load approval records
        # -------------------------------------------------------------

        all_records = (
            self._load_approval_records()
        )

        # -------------------------------------------------------------
        # Separate approved/eligible from excluded
        # -------------------------------------------------------------

        approved_leads: List[
            ApprovalRecord
        ] = []

        excluded_leads: List[
            Dict[str, Any]
        ] = []

        for record in all_records:

            is_approved = (
                record.approval_status
                == ApprovalStatus.APPROVED
            )

            is_eligible = (
                record.smartlead_eligible
                is True
            )

            # ---------------------------------------------------------
            # Approved + eligible
            # ---------------------------------------------------------

            if (
                is_approved
                and is_eligible
            ):

                approved_leads.append(
                    record
                )

                continue

            # ---------------------------------------------------------
            # Excluded
            # ---------------------------------------------------------

            reason = (
                record.blocked_reason
                or (
                    f"Status is "
                    f"{record.approval_status.value} "
                    f"(not APPROVED)"
                )
            )

            excluded_leads.append(
                {
                    "lead_id": record.lead_id,

                    "company": record.company,

                    "contact": record.contact,

                    "email": record.email,

                    "approval_status": (
                        record.approval_status.value
                    ),

                    "smartlead_eligible": (
                        record.smartlead_eligible
                    ),

                    "reason": reason,
                }
            )

        # -------------------------------------------------------------
        # Build Smartlead lead payloads
        # -------------------------------------------------------------

        smartlead_leads = [
            self.build_lead_payload(
                record
            )
            for record in approved_leads
        ]

        # -------------------------------------------------------------
        # Chunk into batches
        # -------------------------------------------------------------

        batches: List[
            Dict[str, Any]
        ] = []

        for i in range(
            0,
            len(smartlead_leads),
            self.batch_size,
        ):

            batch_chunk = smartlead_leads[
                i : i + self.batch_size
            ]

            batches.append(
                {
                    "batch_index": (
                        len(batches) + 1
                    ),

                    "batch_size": (
                        len(batch_chunk)
                    ),

                    "leads": batch_chunk,
                }
            )

        # -------------------------------------------------------------
        # Campaign sequence
        # -------------------------------------------------------------

        sequence_config = (
            self.build_campaign_sequence()
        )

        # -------------------------------------------------------------
        # Complete staging plan
        # -------------------------------------------------------------

        staging_plan = {

            "mode": (
                "OFFLINE_DRY_RUN_STAGING"
            ),

            "branch_mode": "WEBHOOK_OPEN_TRIGGER",

            "safety_status": {

                "dry_run": True,

                "send_emails": False,

                "smartlead_live": False,

                "api_calls_made": 0,

                "real_emails_sent": 0,

                "production_ready": True,
            },

            "summary": {

                "total_queue_records": (
                    len(all_records)
                ),

                "approved_eligible_count": (
                    len(approved_leads)
                ),

                "excluded_count": (
                    len(excluded_leads)
                ),

                "batch_size": (
                    self.batch_size
                ),

                "total_batches": (
                    len(batches)
                ),
            },

            "campaign_payload": {

                "name": (
                    self.campaign_name
                ),

                "status": "DRAFT",

                "client_id": None,

                "track_settings": {

                    "open_tracking": True,

                    "click_tracking": True,
                },
            },

            "sequence_configuration": (
                sequence_config
            ),

            "batches": batches,

            "excluded_leads": (
                excluded_leads
            ),
        }

        # -------------------------------------------------------------
        # Save staging plan
        # -------------------------------------------------------------

        output_directory = (
            os.path.dirname(
                output_path
            )
        )

        if output_directory:

            os.makedirs(
                output_directory,
                exist_ok=True,
            )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                staging_plan,
                f,
                indent=2,
                ensure_ascii=False,
            )

        return staging_plan


# =====================================================================
# PRINT SUMMARY
# =====================================================================

def print_staging_summary(
    plan: Dict[str, Any],
) -> None:
    """
    Prints a human-readable staging summary.
    """

    summary = plan[
        "summary"
    ]

    safety = plan[
        "safety_status"
    ]

    print(
        "==================================================================="
    )

    print(
        " AEDRIX SMARTLEAD STAGING RUNNER - OFFLINE VERIFICATION"
    )

    print(
        "==================================================================="
    )

    print(
        f" Total Records Evaluated:       "
        f"{summary['total_queue_records']}"
    )

    print(
        f" Approved & Eligible Leads:     "
        f"{summary['approved_eligible_count']}"
    )

    print(
        f" Excluded / Blocked Leads:      "
        f"{summary['excluded_count']}"
    )

    print(
        f" Configured Batch Size:         "
        f"{summary['batch_size']}"
    )

    print(
        f" Batches Prepared:              "
        f"{summary['total_batches']}"
    )

    print(
        "-------------------------------------------------------------------"
    )

    print(
        " SAFETY VERIFICATION:"
    )

    print(
        f"  -> DRY_RUN:                   "
        f"{safety['dry_run']}"
    )

    print(
        f"  -> SEND_EMAILS:               "
        f"{safety['send_emails']}"
    )

    print(
        f"  -> SMARTLEAD_LIVE:            "
        f"{safety['smartlead_live']}"
    )

    print(
        f"  -> Smartlead API Calls:       "
        f"{safety['api_calls_made']}"
    )

    print(
        f"  -> Real Emails Sent:          "
        f"{safety['real_emails_sent']}"
    )

    print(
        "==================================================================="
    )

    # -----------------------------------------------------------------
    # Approved leads
    # -----------------------------------------------------------------

    if plan["batches"]:

        print(
            "\n--- STAGED APPROVED LEADS ---"
        )

        for batch in plan[
            "batches"
        ]:

            print(
                f"[Batch "
                f"{batch['batch_index']}/"
                f"{len(plan['batches'])}] "
                f"({batch['batch_size']} leads):"
            )

            for lead in batch[
                "leads"
            ]:

                print(
                    f"  * "
                    f"{lead['company_name']} | "
                    f"{lead['first_name']} "
                    f"{lead['last_name']} "
                    f"<{lead['email']}>"
                )

                print(
                    f"    - Note Status: "
                    f"{lead['custom_fields']['personalization_status']}"
                )

                print(
                    f"    - Index: "
                    f"{lead['custom_fields']['outreach_priority_index']} "
                    f"[{lead['custom_fields']['priority']}]"
                )

    else:

        print(
            "\n[NOTE] No leads currently approved "
            "for Smartlead staging."
        )

        print(
            "Verify the approval status in the "
            "database or data/approval_queue.json."
        )

    # -----------------------------------------------------------------
    # Excluded leads
    # -----------------------------------------------------------------

    if plan[
        "excluded_leads"
    ]:

        print(
            f"\n--- EXCLUDED LEADS "
            f"({len(plan['excluded_leads'])}) ---"
        )

        for exc in plan[
            "excluded_leads"
        ]:

            print(
                f"  * "
                f"{exc['company']} "
                f"({exc['contact']}): "
                f"{exc['approval_status']} -> "
                f"{exc['reason']}"
            )

    print(
        "\nStaging plan saved to "
        "data/smartlead_staging_plan.json "
        "(0 Smartlead API calls executed).\n"
    )


# =====================================================================
# MAIN
# =====================================================================

def main() -> None:
    """
    Entry point for offline Smartlead staging.
    """

    runner = (
        SmartleadStagingRunner()
    )

    plan = (
        runner.build_staging_plan()
    )

    print_staging_summary(
        plan
    )


if __name__ == "__main__":
    main()