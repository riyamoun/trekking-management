#!/usr/bin/env bash
# Foolproof local start from repo root:  bash go.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "Repo: $ROOT"
ls -la "$ROOT/run.py" "$ROOT/requirements.txt"

PY=""
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
elif [[ -x "$ROOT/.venv/bin/python3" ]]; then
  PY="$ROOT/.venv/bin/python3"
fi

if [[ -z "$PY" ]]; then
  echo "No .venv yet — creating one…"
  if ! python3 -m venv "$ROOT/.venv"; then
    echo "Install venv support, then re-run:"
    echo "  sudo apt-get update && sudo apt-get install -y python3.12-venv python3-venv"
    echo "  rm -rf .venv && bash go.sh"
    exit 1
  fi
  PY="$ROOT/.venv/bin/python"
fi

echo "Python: $PY"
"$PY" -c "import flask" 2>/dev/null || "$PY" -m pip install -r "$ROOT/requirements.txt"

export PORT="${PORT:-3847}"
echo "Starting http://127.0.0.1:${PORT}/  (Ctrl+C to stop)"
exec "$PY" "$ROOT/run.py"
