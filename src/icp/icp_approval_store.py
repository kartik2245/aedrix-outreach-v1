"""
icp_approval_store.py
Persistence store for the Human ICP Approval Queue targeting data/icp_approval_queue.json.
"""

import json
import os
from typing import List, Optional, Dict
from src.icp.icp_approval_models import ICPApprovalRecord


class ICPApprovalStore:
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_path = storage_path
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.storage_path = os.path.join(base_dir, "data", "icp_approval_queue.json")

        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def load_queue(self) -> List[ICPApprovalRecord]:
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [ICPApprovalRecord.model_validate(item) for item in data]
        except Exception:
            return []

    def save_queue(self, queue: List[ICPApprovalRecord]) -> None:
        serialized = [item.model_dump(mode="json") for item in queue]
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)

    def get_record(self, icp_id: str) -> Optional[ICPApprovalRecord]:
        queue = self.load_queue()
        for r in queue:
            if r.icp_id == icp_id:
                return r
        return None

    def upsert_record(self, record: ICPApprovalRecord) -> None:
        queue = self.load_queue()
        updated = False
        for idx, r in enumerate(queue):
            if r.icp_id == record.icp_id:
                queue[idx] = record
                updated = True
                break
        if not updated:
            queue.append(record)
        self.save_queue(queue)

    def list_records(self, status_filter: Optional[str] = None, campaign_id: Optional[str] = None) -> List[ICPApprovalRecord]:
        queue = self.load_queue()
        filtered = []
        for r in queue:
            if status_filter and r.status.value.upper() != status_filter.upper():
                continue
            if campaign_id and r.campaign_id != campaign_id:
                continue
            filtered.append(r)
        return filtered
