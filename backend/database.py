"""
backend/database.py — Thin SQLite layer.

Schema
------
incidents
  id          TEXT PRIMARY KEY
  payload     TEXT  (JSON-encoded PipelineResult)
  created_at  TEXT  (ISO-8601 timestamp)

No ORM — plain sqlite3 is sufficient and keeps the dependency surface minimal.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Generator, List, Optional

from backend.models import PipelineResult

_DB_PATH = Path(os.environ.get("BACKEND_DB_PATH", ".backend_db/incidents.db"))


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_DB_PATH))
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    """Create the incidents table if it does not exist."""
    with _conn() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id         TEXT PRIMARY KEY,
                payload    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_incident(result: PipelineResult) -> None:
    """Insert or replace a pipeline result."""
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO incidents (id, payload, created_at) VALUES (?, ?, ?)",
            (
                result.incident.id,
                result.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def load_incident(incident_id: str) -> Optional[PipelineResult]:
    """Return a PipelineResult or None if not found."""
    with _conn() as con:
        row = con.execute(
            "SELECT payload FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()
    if row is None:
        return None
    return PipelineResult.model_validate_json(row["payload"])


def list_incidents() -> List[Dict]:
    """Return a lightweight list of {id, title, severity, created_at}."""
    with _conn() as con:
        rows = con.execute(
            "SELECT id, payload, created_at FROM incidents ORDER BY created_at DESC"
        ).fetchall()
    results = []
    for row in rows:
        data = json.loads(row["payload"])
        results.append(
            {
                "id": row["id"],
                "title": data["incident"]["title"],
                "severity": data["incident"]["severity"],
                "service": data["incident"]["service"],
                "created_at": row["created_at"],
            }
        )
    return results


def delete_incident(incident_id: str) -> bool:
    """Delete an incident. Returns True if a row was deleted."""
    with _conn() as con:
        cur = con.execute("DELETE FROM incidents WHERE id = ?", (incident_id,))
    return cur.rowcount > 0
