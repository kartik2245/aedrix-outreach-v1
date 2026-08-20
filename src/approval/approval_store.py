"""
approval_store.py

Persistence store for the Human Approval Queue in the Aedrix Cold Outreach System.

Primary storage:
    PostgreSQL / Supabase

Fallback storage:
    data/approval_queue.json

The database is the source of truth whenever DATABASE_ENABLED=True
and a valid DATABASE_URL is configured.

The JSON store remains available as an offline fallback.
"""

import json
import os
from typing import Any, Dict, List, Optional, Union

from src.approval.approval_models import ApprovalRecord, ApprovalStatus
from src.database.connection import get_db_session, is_database_enabled
from src.database.repositories.approval_repository import ApprovalRepository


class ApprovalStore:
    """
    Unified approval store.

    PostgreSQL is used as the primary persistence layer.
    JSON is used only when PostgreSQL is unavailable.
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
    ):
        if not storage_path:
            base_dir = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.abspath(__file__)
                    )
                )
            )

            storage_path = os.path.join(
                base_dir,
                "data",
                "approval_queue.json",
            )

        self.storage_path = storage_path

    # ================================================================
    # SAFE CONVERSION HELPERS
    # ================================================================

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        """Safely converts a value to float."""

        try:
            if value is None:
                return default

            return float(value)

        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_list(
        value: Any,
    ) -> List[str]:
        """Safely converts a value into a list of strings."""

        if value is None:
            return []

        if isinstance(value, list):
            return [
                str(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                str(item)
                for item in value
            ]

        if isinstance(value, str):
            return [value]

        return []

    @staticmethod
    def _safe_metadata(
        value: Any,
    ) -> Dict[str, Any]:
        """Safely converts metadata into a dictionary."""

        if isinstance(value, dict):
            return dict(value)

        return {}

    # ================================================================
    # DATABASE -> ApprovalRecord
    # ================================================================

    @classmethod
    def _map_db_approval_to_record(
        cls,
        db_approval: Any,
    ) -> ApprovalRecord:
        """
        Converts a SQLAlchemy EmailApproval object and its related
        Lead / EmailDraft objects into an ApprovalRecord.

        Database models can evolve independently from the approval
        queue model, so fields are accessed defensively.
        """

        # ------------------------------------------------------------
        # Related objects
        # ------------------------------------------------------------

        lead = getattr(
            db_approval,
            "lead",
            None,
        )

        draft = None

        if lead is not None:
            draft = getattr(
                lead,
                "email_draft",
                None,
            )

        # ------------------------------------------------------------
        # Metadata
        # ------------------------------------------------------------

        metadata = cls._safe_metadata(
            getattr(
                db_approval,
                "metadata_json",
                None,
            )
        )

        if lead is not None:

            lead_metadata_fields = {
                "company_domain": "company_domain",
                "linkedin_url": "linkedin_url",
                "environment": "environment",
                "campaign_id": "campaign_id",
                "icp_id": "icp_id",
                "icp_version": "icp_version",
                "website": "website",
            }

            for (
                metadata_key,
                attribute_name,
            ) in lead_metadata_fields.items():

                value = getattr(
                    lead,
                    attribute_name,
                    None,
                )

                if (
                    value is not None
                    and value != ""
                ):
                    metadata.setdefault(
                        metadata_key,
                        value,
                    )

        # ------------------------------------------------------------
        # Approval status
        # ------------------------------------------------------------

        raw_status = getattr(
            db_approval,
            "approval_status",
            ApprovalStatus.PENDING_REVIEW.value,
        )

        if hasattr(
            raw_status,
            "value",
        ):
            raw_status = raw_status.value

        try:
            approval_status = ApprovalStatus(
                str(raw_status).upper()
            )

        except (
            ValueError,
            TypeError,
        ):
            approval_status = (
                ApprovalStatus.PENDING_REVIEW
            )

        # ------------------------------------------------------------
        # Reviewed timestamp
        # ------------------------------------------------------------

        reviewed_at = getattr(
            db_approval,
            "reviewed_at",
            None,
        )

        if reviewed_at is not None:

            try:
                reviewed_at_value = (
                    reviewed_at.isoformat()
                )

            except AttributeError:
                reviewed_at_value = str(
                    reviewed_at
                )

        else:
            reviewed_at_value = None

        # ------------------------------------------------------------
        # Lead identity
        # ------------------------------------------------------------

        company = (
            getattr(
                lead,
                "company_name",
                None,
            )
            if lead is not None
            else None
        ) or "Unknown"

        contact = (
            getattr(
                lead,
                "contact_name",
                None,
            )
            if lead is not None
            else None
        ) or "Unknown"

        title = (
            getattr(
                lead,
                "job_title",
                None,
            )
            if lead is not None
            else None
        ) or ""

        email = (
            getattr(
                lead,
                "email",
                None,
            )
            if lead is not None
            else None
        ) or ""

        # ------------------------------------------------------------
        # Qualification
        # ------------------------------------------------------------

        qualification_status = (
            getattr(
                lead,
                "qualification_status",
                None,
            )
            if lead is not None
            else None
        ) or "UNKNOWN"

        priority = (
            getattr(
                lead,
                "priority_level",
                None,
            )
            if lead is not None
            else None
        ) or "P2"

        # ------------------------------------------------------------
        # Personalization
        # ------------------------------------------------------------

        personalization_status = (
            getattr(
                lead,
                "personalization_status",
                None,
            )
            if lead is not None
            else None
        ) or "UNKNOWN"

        personalization_note = (
            getattr(
                lead,
                "personalization_note",
                None,
            )
            if lead is not None
            else None
        ) or ""

        voc_angle = (
            getattr(
                lead,
                "voc_angle",
                None,
            )
            if lead is not None
            else None
        ) or ""

        # ------------------------------------------------------------
        # Scores
        # ------------------------------------------------------------

        opportunity_score = cls._safe_float(
            getattr(
                lead,
                "opportunity_score",
                0.0,
            )
            if lead is not None
            else 0.0
        )

        accessibility_score = cls._safe_float(
            getattr(
                lead,
                "accessibility_score",
                0.0,
            )
            if lead is not None
            else 0.0
        )

        outreach_priority_index = cls._safe_float(
            getattr(
                lead,
                "outreach_priority_index",
                0.0,
            )
            if lead is not None
            else 0.0
        )

        # ------------------------------------------------------------
        # Original email drafts
        # ------------------------------------------------------------

        email_1_original = (
            getattr(
                draft,
                "ai_original_email_1",
                None,
            )
            if draft is not None
            else None
        ) or ""

        followup_a_original = (
            getattr(
                draft,
                "ai_original_followup_a",
                None,
            )
            if draft is not None
            else None
        ) or ""

        followup_b_original = (
            getattr(
                draft,
                "ai_original_followup_b",
                None,
            )
            if draft is not None
            else None
        ) or ""

        # ------------------------------------------------------------
        # Human-edited email drafts
        # ------------------------------------------------------------

        edited_email_1 = (
            getattr(
                draft,
                "edited_email_1",
                None,
            )
            if draft is not None
            else None
        )

        edited_followup_a = (
            getattr(
                draft,
                "edited_followup_a",
                None,
            )
            if draft is not None
            else None
        )

        edited_followup_b = (
            getattr(
                draft,
                "edited_followup_b",
                None,
            )
            if draft is not None
            else None
        )

        # ------------------------------------------------------------
        # QA
        # ------------------------------------------------------------

        qa_status = (
            getattr(
                draft,
                "qa_status",
                None,
            )
            if draft is not None
            else None
        ) or "PASS"

        qa_reasons = cls._safe_list(
            getattr(
                draft,
                "qa_reasons",
                [],
            )
            if draft is not None
            else []
        )

        # ------------------------------------------------------------
        # Campaign / ICP
        # ------------------------------------------------------------

        campaign_id = (
            getattr(
                lead,
                "campaign_id",
                None,
            )
            if lead is not None
            else None
        )

        icp_id = (
            getattr(
                lead,
                "icp_id",
                None,
            )
            if lead is not None
            else None
        )

        icp_version = (
            getattr(
                lead,
                "icp_version",
                None,
            )
            if lead is not None
            else None
        )

        # ------------------------------------------------------------
        # Build ApprovalRecord
        # ------------------------------------------------------------

        return ApprovalRecord(

            lead_id=str(
                getattr(
                    db_approval,
                    "lead_id",
                    "",
                )
            ),

            company=company,
            contact=contact,
            title=title,
            email=email,

            qualification_status=qualification_status,

            opportunity_score=opportunity_score,
            accessibility_score=accessibility_score,
            outreach_priority_index=outreach_priority_index,

            priority=priority,

            personalization_status=personalization_status,
            personalization_note=personalization_note,
            voc_angle=voc_angle,

            email_1_original=email_1_original,
            followup_a_original=followup_a_original,
            followup_b_original=followup_b_original,

            qa_status=qa_status,
            qa_reasons=qa_reasons,

            approval_status=approval_status,

            reviewer=getattr(
                db_approval,
                "reviewer",
                None,
            ),

            reviewed_at=reviewed_at_value,

            edited_email_1=edited_email_1,
            edited_followup_a=edited_followup_a,
            edited_followup_b=edited_followup_b,

            smartlead_eligible=bool(
                getattr(
                    db_approval,
                    "smartlead_eligible",
                    False,
                )
            ),

            blocked_reason=getattr(
                db_approval,
                "blocked_reason",
                None,
            ),

            flag_no_strong_signal=bool(
                getattr(
                    db_approval,
                    "flag_no_strong_signal",
                    False,
                )
            ),

            campaign_id=campaign_id,
            icp_id=icp_id,
            icp_version=icp_version,

            metadata=metadata,
        )

    # ================================================================
    # JSON FALLBACK
    # ================================================================

    def _load_json_queue(
        self,
    ) -> List[ApprovalRecord]:
        """
        Loads approval records from data/approval_queue.json.

        This is strictly an offline fallback.
        """

        if not os.path.exists(
            self.storage_path
        ):
            return []

        try:
            with open(
                self.storage_path,
                "r",
                encoding="utf-8",
            ) as f:

                raw_data = json.load(f)

        except (
            json.JSONDecodeError,
            OSError,
        ):
            return []

        if not isinstance(
            raw_data,
            list,
        ):
            return []

        records: List[ApprovalRecord] = []

        for item in raw_data:

            try:

                records.append(
                    ApprovalRecord.model_validate(
                        item
                    )
                )

            except Exception:
                # One malformed record must not break
                # the complete offline queue.
                continue

        return records

    def _save_json_queue(
        self,
        records: List[ApprovalRecord],
    ) -> None:
        """
        Saves approval records to the offline JSON store.
        """

        directory = os.path.dirname(
            self.storage_path
        )

        if directory:
            os.makedirs(
                directory,
                exist_ok=True,
            )

        data = [
            record.model_dump(
                mode="json"
            )
            for record in records
        ]

        with open(
            self.storage_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False,
            )

    # ================================================================
    # LOAD QUEUE
    # ================================================================

    def load_queue(
        self,
    ) -> List[ApprovalRecord]:
        """
        Loads the complete approval queue.

        Priority:

            1. PostgreSQL / Supabase
            2. JSON fallback

        The JSON fallback is used only when the database operation
        itself fails.

        An empty database result is NOT considered an error.
        """

        if is_database_enabled():

            try:

                with get_db_session() as session:

                    repository = ApprovalRepository(
                        session
                    )

                    db_approvals = (
                        repository.list_approvals()
                    )

                    records: List[
                        ApprovalRecord
                    ] = []

                    for db_approval in db_approvals:

                        try:

                            record = (
                                self._map_db_approval_to_record(
                                    db_approval
                                )
                            )

                            records.append(
                                record
                            )

                        except Exception as mapping_error:

                            print(
                                "[WARNING] "
                                "Skipping invalid database approval record."
                            )

                            print(
                                f"[WARNING] Mapping error type: "
                                f"{type(mapping_error).__name__}"
                            )

                            print(
                                f"[WARNING] Mapping error: "
                                f"{mapping_error}"
                            )

                    return records

            except Exception as exc:
                import traceback

                print(
                    "[ERROR] Database approval load failed."
                )

                print(
                    f"[ERROR] Exception type: "
                    f"{type(exc).__name__}"
                )

                print(
                    f"[ERROR] Exception: "
                    f"{exc}"
                )

                traceback.print_exc()

                print(
                    "[WARNING] Falling back to "
                    "data/approval_queue.json."
                )

        return self._load_json_queue()

    # ================================================================
    # SAVE QUEUE
    # ================================================================

    def save_queue(
        self,
        records: List[ApprovalRecord],
    ) -> None:
        """
        Saves the queue to JSON.

        Database mutations should be performed through
        ApprovalRepository so transaction handling and audit
        logging remain intact.

        This method remains for backwards compatibility.
        """

        self._save_json_queue(
            records
        )

    # ================================================================
    # GET ONE
    # ================================================================

    def get_record(
        self,
        lead_id: str,
    ) -> Optional[ApprovalRecord]:
        """
        Retrieves one approval record.

        PostgreSQL is primary.
        JSON is fallback.
        """

        if is_database_enabled():

            try:

                with get_db_session() as session:

                    repository = ApprovalRepository(
                        session
                    )

                    db_approval = (
                        repository.get_by_lead_id(
                            lead_id
                        )
                    )

                    if db_approval is None:
                        return None

                    return (
                        self._map_db_approval_to_record(
                            db_approval
                        )
                    )

            except Exception as exc:

                print(
                    "[WARNING] Database approval lookup failed. "
                    "Falling back to JSON."
                )

                print(
                    f"[WARNING] Database error type: "
                    f"{type(exc).__name__}"
                )

                print(
                    f"[WARNING] Database error: "
                    f"{exc}"
                )

        queue = self._load_json_queue()

        for record in queue:

            if record.lead_id == lead_id:
                return record

        return None

    # ================================================================
    # UPSERT
    # ================================================================

    def upsert_record(
        self,
        record: ApprovalRecord,
    ) -> None:
        """
        Updates/inserts a record in the offline JSON queue.

        Production database mutations should use ApprovalRepository
        or the approval service layer.
        """

        queue = self._load_json_queue()

        updated = False

        for index, existing in enumerate(
            queue
        ):

            if existing.lead_id == record.lead_id:

                queue[index] = record
                updated = True
                break

        if not updated:

            queue.append(
                record
            )

        self._save_json_queue(
            queue
        )

    # ================================================================
    # LIST
    # ================================================================

    def list_records(
        self,
        status_filter: Optional[
            Union[ApprovalStatus, str]
        ] = None,
    ) -> List[ApprovalRecord]:
        """
        Lists approval records.

        PostgreSQL is primary.

        Optional status filtering is performed after mapping
        database records into ApprovalRecord objects.
        """

        if is_database_enabled():

            try:

                with get_db_session() as session:

                    repository = ApprovalRepository(
                        session
                    )

                    status_value: Optional[str] = None

                    if status_filter is not None:

                        if isinstance(
                            status_filter,
                            ApprovalStatus,
                        ):

                            status_value = (
                                status_filter.value
                            )

                        else:

                            status_value = str(
                                status_filter
                            ).upper()

                    db_approvals = (
                        repository.list_approvals(
                            status=status_value
                        )
                    )

                    records: List[
                        ApprovalRecord
                    ] = []

                    for db_approval in db_approvals:

                        try:

                            records.append(
                                self._map_db_approval_to_record(
                                    db_approval
                                )
                            )

                        except Exception as mapping_error:

                            print(
                                "[WARNING] "
                                "Skipping invalid database approval record."
                            )

                            print(
                                f"[WARNING] Mapping error type: "
                                f"{type(mapping_error).__name__}"
                            )

                            print(
                                f"[WARNING] Mapping error: "
                                f"{mapping_error}"
                            )

                    return records

            except Exception as exc:
                import traceback

                print(
                    "[ERROR] Database approval list failed."
                )

                print(
                    f"[ERROR] Exception type: "
                    f"{type(exc).__name__}"
                )

                print(
                    f"[ERROR] Exception: "
                    f"{exc}"
                )

                traceback.print_exc()

                print(
                    "[WARNING] Falling back to "
                    "data/approval_queue.json."
                )

        # ------------------------------------------------------------
        # JSON fallback
        # ------------------------------------------------------------

        queue = self._load_json_queue()

        if status_filter is None:
            return queue

        if isinstance(
            status_filter,
            ApprovalStatus,
        ):

            filter_value = (
                status_filter.value
            )

        else:

            filter_value = str(
                status_filter
            ).upper()

        return [
            record
            for record in queue
            if record.approval_status.value
            == filter_value
        ]