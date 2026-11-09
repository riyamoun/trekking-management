#!/usr/bin/env python3
"""Start TrekManage locally for viva / instructor review.

Usage (from project root):
  python3 scripts/start-local.py

Opens http://127.0.0.1:3847 in your default browser.
Requires: Python 3.10+. Redis is optional for UI; install it for cache/Celery.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.getenv("PORT", "3847"))
URL = f"http://127.0.0.1:{PORT}/"
VENV_DIR = ROOT / ".venv"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _ensure_venv() -> Path:
    py = _venv_python()
    if py.exists():
        return py
    print("→ Creating virtualenv (.venv)…")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)], cwd=ROOT)
    py = _venv_python()
    print("→ Installing requirements…")
    subprocess.check_call([str(py), "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=ROOT)
    return py


# Lab-only defaults for first local boot (matches README viva table).
# Written only into the gitignored .env — never into committed source.
_LAB_DEFAULTS = {
    "ADMIN_PASSWORD": "TrekLab#Admin9x",
    "DEMO_STAFF_PASSWORD": "TrekLab#Staff9x",
    "DEMO_USER_PASSWORD": "TrekLab#User9x",
    "SEED_DEMO_DATA": "true",
    "SHOW_LAB_HINTS": "true",
}


def _ensure_env() -> None:
    if ENV_FILE.exists():
        return
    if not ENV_EXAMPLE.exists():
        raise SystemExit("Missing .env.example — cannot bootstrap .env")
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, val = line.partition("=")
            key = key.strip()
            if key in _LAB_DEFAULTS and not val.strip():
                line = f"{key}={_LAB_DEFAULTS[key]}"
        lines.append(line)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("→ Created .env with lab passwords (see README viva table)")


def _redis_up() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 6379), timeout=0.6):
            return True
    except OSError:
        return False


def _maybe_start_redis() -> None:
    if _redis_up():
        print("→ Redis already running on :6379")
        return
    redis_server = shutil.which("redis-server")
    if not redis_server:
        print(
            "⚠  Redis not installed (redis-server not found) — continuing without it.\n"
            "   Public site + dashboards still work. Install later for cache/Celery:\n"
            "     Ubuntu/WSL: sudo apt-get install -y redis-server && sudo service redis-server start\n"
            "     macOS:      brew install redis && brew services start redis\n"
            "   You do NOT need Redis to open http://127.0.0.1:3847 for a UI demo."
        )
        return
    print("→ Starting redis-server --daemonize yes")
    subprocess.check_call([redis_server, "--daemonize", "yes"])
    time.sleep(0.4)
    if _redis_up():
        print("→ Redis ready")
    else:
        print("⚠  Redis did not come up — continuing anyway")


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def main() -> int:
    os.chdir(ROOT)
    print("TrekManage — local lab / instructor preview")
    print(f"Project: {ROOT}")
    _ensure_env()
    py = _ensure_venv()
    _maybe_start_redis()

    if not _port_free(PORT):
        print(f"→ Port {PORT} already in use — opening existing server")
        webbrowser.open(URL)
        print(f"Open: {URL}")
        return 0

    env = os.environ.copy()
    env.setdefault("FLASK_DEBUG", "0")
    env.setdefault("PORT", str(PORT))

    print(f"→ Starting Flask on {URL}")
    proc = subprocess.Popen(
        [str(py), "run.py"],
        cwd=ROOT,
        env=env,
    )

    # Wait until health answers, then open browser
    deadline = time.time() + 25
    ready = False
    while time.time() < deadline:
        if proc.poll() is not None:
            print("Flask exited early — check terminal output / logs")
            return proc.returncode or 1
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                ready = True
                break
        except OSError:
            time.sleep(0.35)

    if ready:
        webbrowser.open(URL)
        print()
        print("=" * 56)
        print(f"  Open in your browser:  {URL}")
        print("  Stop server:           Ctrl+C in this terminal")
        print("=" * 56)
        print()
        print("Optional Celery (other terminals, same venv):")
        print("  celery -A celery_app.celery_config.celery worker --loglevel=INFO")
        print("  celery -A celery_app.celery_config.celery beat --loglevel=INFO")
    else:
        print("Server did not become ready in time — check errors above.")

    try:
        return proc.wait()
    except KeyboardInterrupt:
        print("\n→ Stopping…")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
