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
    from modules.dummy_data_engine.infrastructure.db.models import Base, User
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (or already exist): %s",
                list(Base.metadata.tables.keys()))

    with SessionLocal() as session:
        try:
            cnt = session.query(User).count()
            if cnt == 0:
                demo_staff = [
                    User(
                        id="admin_erp_user",
                        tenant_id="greenwood-high-001",
                        email="admin@demo.school",
                        full_name="ERP Admin",
                        role_key="ADMIN",
                        phone="+91-98765-43210",
                    ),
                    User(
                        id="principal_anita_sharma",
                        tenant_id="greenwood-high-001",
                        email="principal@demo.school",
                        full_name="Dr. Anita Sharma",
                        role_key="PRINCIPAL",
                        phone="+91-98765-43211",
                    ),
                    User(
                        id="teacher_rajesh_kumar",
                        tenant_id="greenwood-high-001",
                        email="teacher01@demo.school",
                        full_name="Mr. Rajesh Kumar",
                        role_key="TEACHER",
                        phone="+91-98765-43212",
                        assigned_sections="10-A",
                    ),
                    User(
                        id="teacher_priya_singh",
                        tenant_id="greenwood-high-001",
                        email="teacher02@demo.school",
                        full_name="Ms. Priya Singh",
                        role_key="TEACHER",
                        phone="+91-98765-43213",
                        assigned_sections="10-B",
                    ),
                    User(
                        id="teacher_amit_verma",
                        tenant_id="greenwood-high-001",
                        email="amit.verma@greenwoodhigh.edu.in",
                        full_name="Mr. Amit Verma",
                        role_key="TEACHER",
                        phone="+91-98765-43214",
                    ),
                    User(
                        id="teacher_sunita_sharma",
                        tenant_id="greenwood-high-001",
                        email="sunita.sharma@greenwoodhigh.edu.in",
                        full_name="Ms. Sunita Sharma",
                        role_key="TEACHER",
                        phone="+91-98765-43215",
                    ),
                    User(
                        id="teacher_vikram_malhotra",
                        tenant_id="greenwood-high-001",
                        email="vikram.malhotra@greenwoodhigh.edu.in",
                        full_name="Mr. Vikram Malhotra",
                        role_key="TEACHER",
                        phone="+91-98765-43216",
                    ),
                    User(
                        id="teacher_kavita_joshi",
                        tenant_id="greenwood-high-001",
                        email="kavita.joshi@greenwoodhigh.edu.in",
                        full_name="Ms. Kavita Joshi",
                        role_key="TEACHER",
                        phone="+91-98765-43217",
                    ),
                ]
                session.add_all(demo_staff)
                session.commit()
                logger.info("Seeded %d staff users", len(demo_staff))
        except Exception as e:
            session.rollback()
            logger.warning("Could not auto-seed users: %s", e)


def drop_all_tables() -> None:
    """Drop all ORM-defined tables. Used by seed_db --drop-existing."""
    from modules.dummy_data_engine.infrastructure.db.models import Base
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped.")
