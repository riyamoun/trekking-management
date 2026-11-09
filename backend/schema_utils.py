"""Lightweight SQLite column ensures for evolving MAD-2 schema (no manual DB edits)."""

from __future__ import annotations

from sqlalchemy import text

from backend.extensions import db


def ensure_sqlite_columns() -> None:
    """Add newly introduced columns on existing SQLite files."""
    bind = db.session.get_bind()
    if bind.dialect.name != "sqlite":
        return

    existing = {
        row[1]
        for row in db.session.execute(text("PRAGMA table_info(treks)")).fetchall()
    }
    alters = []
    if "image_url" not in existing:
        alters.append("ALTER TABLE treks ADD COLUMN image_url VARCHAR(500)")
    if "gallery_urls" not in existing:
        alters.append("ALTER TABLE treks ADD COLUMN gallery_urls TEXT")
    for stmt in alters:
        db.session.execute(text(stmt))
    if alters:
        db.session.commit()
