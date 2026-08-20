"""
approval package for Aedrix Cold Outreach System.
Human Approval & Safety Gate Layer.
"""

from src.approval.approval_models import ApprovalStatus, ApprovalRecord

__all__ = [
    "ApprovalStatus",
    "ApprovalRecord",
]