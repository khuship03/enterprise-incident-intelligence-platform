from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_db_path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    return connection


def initialize_db() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                service TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                summary TEXT,
                category TEXT,
                severity TEXT,
                confidence REAL,
                key_symptoms TEXT NOT NULL DEFAULT '[]',
                recommendations TEXT NOT NULL DEFAULT '[]',
                retrieved_runbooks TEXT NOT NULL DEFAULT '[]',
                assigned_group TEXT,
                needs_human_review INTEGER NOT NULL DEFAULT 0,
                analysis_provider TEXT,
                triage_notes TEXT,
                error_message TEXT,
                reviewed_by TEXT,
                review_notes TEXT,
                reviewed_at TEXT,
                processing_attempts INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at)")


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def decode_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def row_to_incident(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for field in ("key_symptoms", "recommendations", "retrieved_runbooks"):
        result[field] = decode_json(result.get(field), [])
    result["needs_human_review"] = bool(result.get("needs_human_review", 0))
    result["confidence"] = float(result["confidence"]) if result.get("confidence") is not None else None
    return result


def get_incident(incident_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    return row_to_incident(row)


def list_incidents(limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    with connect() as connection:
        if status:
            rows = connection.execute(
                "SELECT * FROM incidents WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [row_to_incident(row) for row in rows if row is not None]


def create_incident_record(
    *, incident_id: str, title: str, description: str, service: str, source: str
) -> dict[str, Any]:
    now = utc_now()
    with connect() as connection:
        connection.execute(
            """INSERT INTO incidents
               (id, title, description, service, source, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'received', ?, ?)""",
            (incident_id, title, description, service, source, now, now),
        )
    created = get_incident(incident_id)
    if created is None:
        raise RuntimeError("Incident was inserted but could not be read back.")
    return created
