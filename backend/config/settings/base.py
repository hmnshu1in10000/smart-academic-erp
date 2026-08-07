"""
config/settings/base.py
=======================
Infrastructure-only settings. This module NEVER contains school-specific
business rules, colors, or tenant data — those live in config/tenants/.

Rule (ARCHITECTURE §1.3.3): modules read tenant config from ITenantConfigProvider,
never from this settings file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (two levels up from backend/)
_root_env = Path(__file__).resolve().parents[3] / ".env"
_backend_env = Path(__file__).resolve().parents[2] / ".env"

for _env_path in [_backend_env, _root_env]:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

# ── Core Identity ──────────────────────────────────────────────────────────────
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
SECRET_KEY: str = os.getenv(
    "SECRET_KEY",
    "dev-insecure-change-me-in-production-000000000000000000000000000000"
)
DEBUG: bool = ENVIRONMENT == "development"

# ── Database ───────────────────────────────────────────────────────────────────
# SQLite default for local dev. Override with DATABASE_URL=postgresql+asyncpg://...
_backend_dir = Path(__file__).resolve().parents[2]
_sqlite_path = str(_backend_dir / "db.sqlite3").replace("\\", "/")
_default_sqlite = f"sqlite:///{_sqlite_path}"
DATABASE_URL: str = os.getenv("DATABASE_URL", _default_sqlite)

# Sync URL for Alembic migrations (Alembic doesn't support async drivers)
DATABASE_SYNC_URL: str = DATABASE_URL.replace(
    "sqlite+aiosqlite:///", "sqlite:///"
).replace(
    "postgresql+asyncpg://", "postgresql://"
)

# Read-only analytics connection (defaults to same DB in Phase 1; Phase 2 uses replica)
READ_ONLY_ANALYTICS_DB_URL: str = os.getenv(
    "READ_ONLY_ANALYTICS_DB_URL", DATABASE_URL
)

# ── API Configuration ──────────────────────────────────────────────────────────
API_V1_PREFIX: str = "/api/v1"
PROJECT_NAME: str = "Smart Academic ERP"
PROJECT_VERSION: str = "0.1.0"

# ── CORS (dev allows all origins) ─────────────────────────────────────────────
ALLOWED_ORIGINS: list[str] = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8080,http://localhost:8081,http://localhost:8082,http://localhost:19006,http://127.0.0.1:8081,http://127.0.0.1:3000"
).split(",")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR: str = os.getenv("LOG_DIR", str(_backend_dir.parent / ".logs"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_ALGORITHM: str = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)
JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(
    os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30")
)

# ── External APIs (Phase 1 all dummy) ─────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
