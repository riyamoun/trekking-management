#!/usr/bin/env bash
# Wrapper so:  bash scripts/start-local.sh
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/start-local.py
