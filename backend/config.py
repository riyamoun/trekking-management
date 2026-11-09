"""Application configuration."""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)

    # SQLite created under instance/ programmatically (absolute path)
    _db_env = os.getenv("DATABASE_URL", "").strip()
    if _db_env.startswith("sqlite:///") and not _db_env.startswith("sqlite:////"):
        # Resolve relative sqlite paths against project root
        rel = _db_env.replace("sqlite:///", "", 1)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(ROOT / rel).resolve()}"
    elif _db_env:
        SQLALCHEMY_DATABASE_URI = _db_env
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(ROOT / 'instance' / 'trek.db').resolve()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
    )

    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@trekmanage.local")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@trekmanage.local")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

    ADMIN_EMAIL_SEED = os.getenv("ADMIN_EMAIL_SEED", "admin@trekmanage.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "System Admin")

    EXPORTS_DIR = str(ROOT / "exports")
    REPORTS_DIR = str(ROOT / "reports")
