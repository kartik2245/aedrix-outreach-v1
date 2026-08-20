"""
health_check.py
CLI health check & diagnostics tool for Aedrix Cold Outreach System.
Validates Python virtualenv, Supabase PostgreSQL connectivity, application mode, and integration states.
"""

import os
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.app_mode import ModeService
from src.database.connection import check_db_health, is_database_enabled
from src.integrations.smartlead_client import SmartleadClient, load_env_file_if_present


def run_health_check() -> bool:
    load_env_file_if_present()
    mode_service = ModeService.get_instance()
    cfg = mode_service.get_mode_config()
    db_health = check_db_health()

    print("===================================================================")
    print(" AEDRIX AI COLD OUTREACH SYSTEM — SYSTEM HEALTH DIAGNOSTIC")
    print("===================================================================")
    print(f"  Application Mode:      {cfg.mode}")
    print(f"  Python Version:        {sys.version.split()[0]}")
    print(f"  Database Engine:       {cfg.database}")
    print(f"  Database Status:       {'CONNECTED (HEALTHY)' if db_health.get('connected') else 'DISCONNECTED / OFFLINE'}")
    if db_health.get("latency_ms") is not None:
        print(f"  Database Latency:      {db_health['latency_ms']:.2f} ms")
    print(f"  Claude Status:         {cfg.claude_mode}")
    print(f"  Deepline Status:       {cfg.deepline_mode}")
    print(f"  Smartlead Status:      {cfg.smartlead_mode}")
    print(f"  Real Email Sending:    {'ENABLED' if cfg.real_emails_enabled else 'DISABLED (SAFE)'}")
    print(f"  Real Emails Sent:      {cfg.real_emails_sent}")
    print(f"  Safety Summary:        {cfg.safety_summary}")
    print("===================================================================")

    if cfg.production_mode and not db_health.get("connected"):
        print(" [WARNING] Production mode is active but database connection failed.")
        return False

    print(" [OK] System health check passed.")
    return True


if __name__ == "__main__":
    success = run_health_check()
    sys.exit(0 if success else 1)
