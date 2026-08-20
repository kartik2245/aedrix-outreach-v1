"""
test_app_mode_and_demo.py
Comprehensive automated test suite for Application Mode (DEMO vs PRODUCTION),
Demo Data Seeding & Isolation, Demo Reset Safety, System Readiness, and Safety Gates.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.config.app_mode import ModeService, AppMode
from src.demo.demo_service import DemoService
from src.demo.demo_data import DEMO_CAMPAIGN_ID, DEMO_ICP_ID, DEMO_LEADS_DATA
from src.database.connection import is_database_enabled, get_db_session
from src.database.models import Campaign, Lead


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_mode():
    """Ensure mode is reset to DEMO after each test."""
    service = ModeService.get_instance()
    service.set_mode(AppMode.DEMO)
    yield
    service.set_mode(AppMode.DEMO)


# ==============================================================================
# 1. APPLICATION MODE & CENTRALIZED CONFIGURATION TESTS
# ==============================================================================

def test_mode_service_default_is_demo():
    service = ModeService.get_instance()
    service.set_mode(AppMode.DEMO)
    assert service.is_demo() is True
    assert service.is_production() is False
    assert service.get_mode() == AppMode.DEMO


def test_mode_service_switch_to_production():
    service = ModeService.get_instance()
    service.set_mode(AppMode.PRODUCTION)
    assert service.is_production() is True
    assert service.is_demo() is False
    assert service.get_mode() == AppMode.PRODUCTION


def test_get_system_mode_endpoint(client):
    response = client.get("/api/system/mode")
    assert response.status_code == 200
    data = response.json()
    assert "mode" in data
    assert data["mode"] == "DEMO"
    assert data["demo_mode"] is True
    assert data["real_emails_enabled"] is False
    assert data["real_emails_sent"] == 0
    assert "safety_summary" in data


def test_set_system_mode_to_production_requires_confirmation(client):
    # Attempting to switch to PRODUCTION without confirmation text must fail
    response = client.post("/api/system/mode", json={"mode": "PRODUCTION"})
    assert response.status_code == 400
    assert "ENABLE PRODUCTION" in response.json()["detail"]

    # With incorrect confirmation text
    response = client.post("/api/system/mode", json={"mode": "PRODUCTION", "confirmation": "yes"})
    assert response.status_code == 400

    # With valid confirmation text
    response = client.post("/api/system/mode", json={"mode": "PRODUCTION", "confirmation": "ENABLE PRODUCTION"})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "PRODUCTION"
    assert data["production_mode"] is True


def test_set_system_mode_back_to_demo(client):
    # Switch to prod first
    client.post("/api/system/mode", json={"mode": "PRODUCTION", "confirmation": "ENABLE PRODUCTION"})
    # Switch back to demo (no confirmation required)
    response = client.post("/api/system/mode", json={"mode": "DEMO"})
    assert response.status_code == 200
    assert response.json()["mode"] == "DEMO"
    assert response.json()["demo_mode"] is True


def test_get_system_readiness_endpoint(client):
    response = client.get("/api/system/readiness")
    assert response.status_code == 200
    data = response.json()
    assert "application" in data
    assert data["mode"] in ("DEMO", "PRODUCTION")
    assert "database" in data
    assert "frontend" in data
    assert "details" in data
    assert data["email"] == "DISABLED"


# ==============================================================================
# 2. DEMO DATA SEEDING & ISOLATION TESTS
# ==============================================================================

def test_demo_seeding_creates_all_demo_leads():
    service = DemoService()
    summary = service.seed_demo_dataset()
    assert summary["status"] == "SEEDED"
    assert len(DEMO_LEADS_DATA) >= 10

    # Verify qualified vs disqualified counts
    qualified = [l for l in DEMO_LEADS_DATA if l["qualification_status"] == "QUALIFIED"]
    disqualified = [l for l in DEMO_LEADS_DATA if l["qualification_status"] != "QUALIFIED"]
    assert len(qualified) >= 7
    assert len(disqualified) >= 2


def test_demo_data_endpoint_seeding(client):
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "seeded" in data["message"].lower()


def test_demo_reset_safety_and_isolation(client):
    # First seed demo dataset
    demo_service = DemoService()
    demo_service.seed_demo_dataset()

    # Reset demo dataset
    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "Production records remained 100% untouched" in data["message"]


def test_demo_full_workflow_simulation(client):
    response = client.post("/api/demo/run")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["summary"]["workflow_steps_completed"]) >= 6
    assert data["summary"]["stats"]["real_emails_sent"] == 0
    assert data["summary"]["stats"]["paid_api_credits_consumed"] == 0


def test_zero_real_emails_safety_guarantee(client):
    # In both demo and production endpoints, real_emails_sent must remain 0
    mode_resp = client.get("/api/system/mode").json()
    assert mode_resp["real_emails_sent"] == 0
    assert mode_resp["real_emails_enabled"] is False

    status_resp = client.get("/api/system/status").json()
    assert status_resp["safety_flags"]["REAL_EMAILS_SENT"] == 0
    assert status_resp["safety_flags"]["SEND_EMAILS"] is False
