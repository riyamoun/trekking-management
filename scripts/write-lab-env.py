#!/usr/bin/env python3
"""Create .env from .env.example with viva lab passwords (gitignored)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = ROOT / ".env.example"
dst = ROOT / ".env"

LAB = {
    "ADMIN_PASSWORD": "TrekLab#Admin9x",
    "DEMO_STAFF_PASSWORD": "TrekLab#Staff9x",
    "DEMO_USER_PASSWORD": "TrekLab#User9x",
    "SEED_DEMO_DATA": "true",
    "SHOW_LAB_HINTS": "true",
    "PORT": "3847",
}

if not src.exists():
    raise SystemExit("Missing .env.example")

lines = []
seen = set()
for line in src.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        key = line.split("=", 1)[0].strip()
        if key in LAB:
            lines.append(f"{key}={LAB[key]}")
            seen.add(key)
            continue
    lines.append(line)
for key, val in LAB.items():
    if key not in seen:
        lines.append(f"{key}={val}")

dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {dst} with lab defaults (do not commit this file)")
