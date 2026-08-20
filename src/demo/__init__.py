"""
demo package for Aedrix Cold Outreach System.
"""

from src.demo.demo_data import (
    DEMO_CAMPAIGN_ID,
    DEMO_CAMPAIGN_NAME,
    DEMO_CAMPAIGN_OBJECTIVE,
    DEMO_ICP_ID,
    DEMO_ICP_CONFIG,
    DEMO_LEADS_DATA,
)
from src.demo.demo_service import DemoService

__all__ = [
    "DEMO_CAMPAIGN_ID",
    "DEMO_CAMPAIGN_NAME",
    "DEMO_CAMPAIGN_OBJECTIVE",
    "DEMO_ICP_ID",
    "DEMO_ICP_CONFIG",
    "DEMO_LEADS_DATA",
    "DemoService",
]
