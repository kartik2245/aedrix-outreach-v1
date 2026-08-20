"""
connection.py
PostgreSQL / Supabase connection manager and session factory using SQLAlchemy 2.x and psycopg 3.

Safety Guarantees:
- Never prints or exposes DATABASE_URL, passwords, or credentials.
- Safe connection pooling with pool_pre_ping=True.
- Graceful health checks and latency measurement.
- DATABASE_ENABLED flag controls whether PostgreSQL is the primary store or offline JSON fallback is used.
"""

import os
from dotenv import load_dotenv

load_dotenv()
import time
from typing import Generator, Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import sessionmaker, Session
from src.integrations.claude_client import load_env_file_if_present

# Global Engine and SessionFactory caches
_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


def is_database_enabled() -> bool:
    """Returns True if DATABASE_ENABLED is set to true and a DATABASE_URL is configured."""
    load_env_file_if_present()
    db_enabled = os.getenv("DATABASE_ENABLED", "true").lower() in ("true", "1", "yes")
    db_url = os.getenv("DATABASE_URL", "").strip()
    return db_enabled and bool(db_url)


def get_database_url() -> str:
    """Safely retrieves DATABASE_URL from the environment."""
    load_env_file_if_present()
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return ""
    # Ensure psycopg 3 driver is specified if postgresql:// is provided
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_engine() -> Optional[Engine]:
    """Returns the cached SQLAlchemy Engine instance or creates one."""
    global _engine
    if _engine is not None:
        return _engine

    db_url = get_database_url()
    if not db_url:
        return None

    try:
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,
            connect_args={"connect_timeout": 10},
        )
        return _engine
    except Exception:
        return None


def get_session_factory() -> Optional[sessionmaker]:
    """Returns the cached sessionmaker factory."""
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory

    engine = get_engine()
    if engine is None:
        return None

    _SessionFactory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    return _SessionFactory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager providing a transactional database session with auto-rollback on error."""
    factory = get_session_factory()
    if not factory:
        raise RuntimeError("Database session factory is not available. Check DATABASE_URL and DATABASE_ENABLED.")

    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding an active database session."""
    with get_db_session() as session:
        yield session


def check_db_health() -> Dict[str, Any]:
    """
    Executes a lightweight SELECT 1 query and returns connection status, latency, and database type.
    Never exposes credentials or connection strings.
    """
    if not is_database_enabled():
        return {
            "database": "supabase_postgresql",
            "connected": False,
            "latency_ms": None,
            "database_enabled": False,
            "status": "DISABLED",
        }

    engine = get_engine()
    if not engine:
        return {
            "database": "supabase_postgresql",
            "connected": False,
            "latency_ms": None,
            "database_enabled": True,
            "status": "ENGINE_UNAVAILABLE",
        }

    t0 = time.perf_counter()
    try:
        with engine.connect() as conn:
            val = conn.execute(text("SELECT 1")).scalar()
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            if val == 1:
                return {
                    "database": "supabase_postgresql",
                    "connected": True,
                    "latency_ms": latency_ms,
                    "database_enabled": True,
                    "status": "HEALTHY",
                }
            return {
                "database": "supabase_postgresql",
                "connected": False,
                "latency_ms": latency_ms,
                "database_enabled": True,
                "status": "UNEXPECTED_RESPONSE",
            }
    except Exception as e:
        return {
            "database": "supabase_postgresql",
            "connected": False,
            "latency_ms": None,
            "database_enabled": True,
            "status": f"ERROR_{type(e).__name__}",
        }
