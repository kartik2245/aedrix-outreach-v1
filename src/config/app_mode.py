"""
app_mode.py
Centralized Application Mode & Environment Configuration for Aedrix Cold Outreach System.

Enforces strict architectural separation between:
1. DEMO MODE: Safe deterministic simulation with zero credit expenditure and zero real email sending.
2. PRODUCTION MODE: Strict validation, live PostgreSQL operations, and guarded external integrations.

Guarantees:
- Mode is determined centrally from environment (APP_MODE) or runtime toggle.
- Sensitive credentials (API keys, database URLs) are NEVER exposed.
- Live email sending is strictly disabled by default in both modes.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel

from src.integrations.smartlead_client import SmartleadClient, load_env_file_if_present
from src.database.connection import check_db_health, is_database_enabled


class AppMode(str, Enum):
    DEMO = "DEMO"
    PRODUCTION = "PRODUCTION"


class ModeConfigResponse(BaseModel):
    mode: str
    demo_mode: bool
    production_mode: bool
    database: str
    database_connected: bool
    database_latency_ms: Optional[float] = None
    claude_mode: str
    deepline_mode: str
    smartlead_mode: str
    real_emails_enabled: bool
    smartlead_live: bool
    deepline_live: bool
    real_emails_sent: int = 0
    safety_summary: str


class ReadinessResponse(BaseModel):
    application: str
    mode: str
    database: str
    frontend: str
    claude: str
    deepline: str
    smartlead: str
    email: str
    details: Dict[str, Any]


class ModeService:
    _instance: Optional["ModeService"] = None
    _runtime_mode_override: Optional[AppMode] = None

    @classmethod
    def get_instance(cls) -> "ModeService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_mode(self) -> AppMode:
        """Returns the active application mode (runtime override or environment)."""
        if self._runtime_mode_override is not None:
            return self._runtime_mode_override
        load_env_file_if_present()
        raw_mode = os.getenv("APP_MODE", "DEMO").strip().upper()
        if raw_mode in ("PRODUCTION", "PROD"):
            return AppMode.PRODUCTION
        return AppMode.DEMO

    def set_mode(self, mode: AppMode) -> None:
        """Sets the runtime application mode."""
        self._runtime_mode_override = mode

    def is_demo(self) -> bool:
        return self.get_mode() == AppMode.DEMO

    def is_production(self) -> bool:
        return self.get_mode() == AppMode.PRODUCTION

    def get_mode_config(self) -> ModeConfigResponse:
        """Returns full mode configuration status with safety indicators."""
        load_env_file_if_present()
        mode = self.get_mode()
        is_demo_mode = (mode == AppMode.DEMO)

        # Database health check
        db_health = check_db_health()
        db_connected = db_health.get("connected", False)
        db_latency = db_health.get("latency_ms")

        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        smartlead_key = os.getenv("SMARTLEAD_API_KEY", "").strip()
        deepline_key = os.getenv("DEEPLINE_API_KEY", "").strip()

        env_dry_run = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
        env_send_emails = os.getenv("SEND_EMAILS", "false").lower() in ("true", "1", "yes")
        env_smartlead_live = os.getenv("SMARTLEAD_LIVE", "false").lower() in ("true", "1", "yes")
        env_deepline_live = os.getenv("DEEPLINE_LIVE", "false").lower() in ("true", "1", "yes")
        env_prod_confirm = os.getenv("PRODUCTION_SEND_CONFIRMATION", "false").lower() in ("true", "1", "yes")

        if is_demo_mode:
            claude_mode = "SIMULATED / DRY_RUN"
            deepline_mode = "SIMULATED / DRY_RUN"
            smartlead_mode = "SIMULATED / STAGING"
            real_emails_enabled = False
            smartlead_live = False
            deepline_live = False
            safety_summary = "DEMO SIMULATION: 0 real emails, 0 paid API credits consumed."
        else:
            claude_mode = "LIVE_API" if (anthropic_key and not env_dry_run) else "OFFLINE_FALLBACK"
            deepline_mode = "LIVE_API" if (deepline_key and env_deepline_live) else "DRY_RUN_DISCOVERY"
            smartlead_mode = "LIVE_API" if (smartlead_key and env_smartlead_live) else "STAGING_ONLY"
            real_emails_enabled = (env_send_emails and env_prod_confirm)
            smartlead_live = env_smartlead_live
            deepline_live = env_deepline_live
            safety_summary = "PRODUCTION MODE: Live database active, human approval gates strictly enforced."

        return ModeConfigResponse(
            mode=mode.value,
            demo_mode=is_demo_mode,
            production_mode=(mode == AppMode.PRODUCTION),
            database="SUPABASE_POSTGRESQL" if is_database_enabled() else "OFFLINE_JSON_STORE",
            database_connected=db_connected,
            database_latency_ms=db_latency,
            claude_mode=claude_mode,
            deepline_mode=deepline_mode,
            smartlead_mode=smartlead_mode,
            real_emails_enabled=real_emails_enabled,
            smartlead_live=smartlead_live,
            deepline_live=deepline_live,
            real_emails_sent=0,
            safety_summary=safety_summary,
        )

    def get_readiness_status(self) -> ReadinessResponse:
        """Returns startup diagnostics with masked credentials."""
        cfg = self.get_mode_config()

        # Check frontend dist availability
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dist_dir = os.path.join(base_dir, "frontend", "dist")
        frontend_status = "READY" if os.path.exists(dist_dir) else "DEV_SERVER_REQUIRED"

        # Determine overall readiness
        app_status = "READY"
        if not cfg.database_connected and cfg.production_mode:
            app_status = "DEGRADED"

        email_status = "ENABLED" if cfg.real_emails_enabled else "DISABLED"

        return ReadinessResponse(
            application=app_status,
            mode=cfg.mode,
            database="CONNECTED" if cfg.database_connected else "DISCONNECTED",
            frontend=frontend_status,
            claude=cfg.claude_mode,
            deepline=cfg.deepline_mode,
            smartlead=cfg.smartlead_mode,
            email=email_status,
            details={
                "demo_mode": cfg.demo_mode,
                "database_enabled": is_database_enabled(),
                "database_latency_ms": cfg.database_latency_ms,
                "real_emails_sent": 0,
                "safety_summary": cfg.safety_summary,
            }
        )
