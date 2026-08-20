"""
demo.py
FastAPI router for Demo dataset seeding, isolated demo reset, and full simulation execution.
"""

from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

from src.demo.demo_service import DemoService

router = APIRouter(prefix="/demo", tags=["Demo Management"])


class DemoActionResponse(BaseModel):
    ok: bool
    message: str
    summary: Dict[str, Any]


@router.post("/seed", response_model=DemoActionResponse)
def seed_demo_data() -> DemoActionResponse:
    """Seeds the realistic UK B2B construction demo dataset."""
    service = DemoService()
    res = service.seed_demo_dataset()
    return DemoActionResponse(
        ok=True,
        message="Realistic UK construction demo dataset seeded successfully.",
        summary=res
    )


@router.post("/reset", response_model=DemoActionResponse)
def reset_demo_data() -> DemoActionResponse:
    """
    Safely resets ONLY demo data (environment='DEMO').
    Production campaigns and leads remain 100% untouched.
    """
    service = DemoService()
    res = service.reset_demo_dataset()
    return DemoActionResponse(
        ok=True,
        message=res["message"],
        summary=res
    )


@router.post("/run", response_model=DemoActionResponse)
def run_full_demo() -> DemoActionResponse:
    """
    Executes the complete simulated end-to-end outreach workflow
    (Campaign -> ICP -> Discovery -> Intelligence -> Drafts -> QA -> Staging)
    with zero real emails sent and zero paid credits consumed.
    """
    service = DemoService()
    res = service.run_full_demo_workflow()
    return DemoActionResponse(
        ok=True,
        message=res["message"],
        summary=res
    )
