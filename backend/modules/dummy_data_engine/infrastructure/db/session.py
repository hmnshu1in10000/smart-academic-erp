"""
modules/dummy_data_engine/infrastructure/db/session.py
========================================================
SQLAlchemy engine and session factory.
Source of truth: ARCHITECTURE.md Appendix §1

Uses the DATABASE_URL from settings — SQLite by default, overridable to PostgreSQL.
"""
from __future__ import annotations

import logging
import sys
import os
from contextlib import contextmanager
from typing import Generator

# Ensure the backend directory is on sys.path when this module is imported
# (handles both 'python manage.py' and direct imports)
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from config.settings.base import DATABASE_SYNC_URL

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_SYNC_URL,
    echo=False,              # Set True to log all SQL statements
    pool_pre_ping=True,
    connect_args=(
        {"check_same_thread": False}
        if DATABASE_SYNC_URL.startswith("sqlite")
        else {}
    ),
)

# Enable WAL mode + FK enforcement for SQLite
if DATABASE_SYNC_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _connection_record):  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

# ── Session Factory ────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,    # Avoids lazy-load after commit in seeding loops
)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager that provides a DB session and handles rollback on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all_tables() -> None:
    """Create all ORM-defined tables. Safe to call multiple times (idempotent)."""
    from modules.dummy_data_engine.infrastructure.db.models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (or already exist): %s",
                list(Base.metadata.tables.keys()))


def drop_all_tables() -> None:
    """Drop all ORM-defined tables. Used by seed_db --drop-existing."""
    from modules.dummy_data_engine.infrastructure.db.models import Base
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped.")
