"""Runtime secrets, password policy, and deploy-safe helpers.

Secrets are never hardcoded. Prefer environment variables; otherwise generate
cryptographically strong values and persist them under instance/ (gitignored).
"""

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTANCE_DIR = ROOT / "instance"
RUNTIME_SECRETS_PATH = INSTANCE_DIR / "runtime_secrets.json"
BOOTSTRAP_ADMIN_PATH = INSTANCE_DIR / "BOOTSTRAP_ADMIN.txt"


def _ensure_instance() -> None:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def _load_runtime_file() -> dict:
    _ensure_instance()
    if not RUNTIME_SECRETS_PATH.exists():
        return {}
    try:
        return json.loads(RUNTIME_SECRETS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_runtime_file(data: dict) -> None:
    _ensure_instance()
    RUNTIME_SECRETS_PATH.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    try:
        RUNTIME_SECRETS_PATH.chmod(0o600)
    except OSError:
        pass


def resolve_secret(env_name: str, *, length: int = 48) -> str:
    """Return env secret or a persisted randomly generated value (never a fixed default)."""
    import os

    from_env = (os.getenv(env_name) or "").strip()
    if from_env:
        return from_env

    store = _load_runtime_file()
    existing = store.get(env_name)
    if isinstance(existing, str) and len(existing) >= 32:
        return existing

    generated = secrets.token_urlsafe(length)
    store[env_name] = generated
    _save_runtime_file(store)
    return generated


def generate_password(length: int = 16) -> str:
    """Generate a strong password with mixed character classes."""
    alphabet = (
        "ABCDEFGHJKLMNPQRSTUVWXYZ"
        "abcdefghijkmnopqrstuvwxyz"
        "23456789"
        "!@#$%^&*"
    )
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if password_policy_error(pwd) is None:
            return pwd


def password_policy_error(password: str, *, min_length: int = 10) -> str | None:
    """Return an error message if password fails the project policy, else None."""
    if not password or len(password) < min_length:
        return f"Password must be at least {min_length} characters"
    if not re.search(r"[A-Z]", password):
        return "Password must include an uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must include a lowercase letter"
    if not re.search(r"\d", password):
        return "Password must include a digit"
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must include a special character"
    return None


def write_bootstrap_admin(email: str, password: str) -> Path:
    """Persist one-time local bootstrap credentials (instance/, never committed)."""
    _ensure_instance()
    BOOTSTRAP_ADMIN_PATH.write_text(
        (
            "# TrekManage admin bootstrap — local only, do not commit\n"
            f"email={email}\n"
            f"password={password}\n"
        ),
        encoding="utf-8",
    )
    try:
        BOOTSTRAP_ADMIN_PATH.chmod(0o600)
    except OSError:
        pass
    return BOOTSTRAP_ADMIN_PATH
