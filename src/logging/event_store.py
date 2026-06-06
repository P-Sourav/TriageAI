"""
SQLite-backed agent event store.

Every LLM prompt/response and agent output is written here with full payloads,
timing, provider info, and the associated ticket ID.

Schema: agent_events
  id          — auto PK
  event_time  — ISO-8601 UTC timestamp
  ticket_id   — TCK-… identifier (empty for system-level events)
  agent_name  — "LLM Client", "Classifier Agent", "Orchestrator", …
  event_type  — llm_prompt | llm_response | agent_output | ticket_received
  direction   — SEND (outgoing prompt) | RECEIVE (incoming response / output)
  payload     — full JSON blob
  duration_ms — latency (only meaningful for llm_response)
  provider    — mock | openai | anthropic
  model       — model ID string
  status      — ok | error
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from src.logging.context import current_ticket_id


_DDL = """
CREATE TABLE IF NOT EXISTS agent_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time  TEXT    NOT NULL,
    ticket_id   TEXT    DEFAULT '',
    agent_name  TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    direction   TEXT    NOT NULL,
    payload     TEXT    NOT NULL,
    duration_ms INTEGER DEFAULT 0,
    provider    TEXT    DEFAULT '',
    model       TEXT    DEFAULT '',
    status      TEXT    DEFAULT 'ok'
);
CREATE INDEX IF NOT EXISTS idx_ticket  ON agent_events (ticket_id);
CREATE INDEX IF NOT EXISTS idx_agent   ON agent_events (agent_name);
CREATE INDEX IF NOT EXISTS idx_time    ON agent_events (event_time);
"""


class EventStore:
    def __init__(self, db_path: str):
        if db_path != ":memory:":
            dir_part = os.path.dirname(db_path)
            if dir_part:
                os.makedirs(dir_part, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()

    # ------------------------------------------------------------------
    def log(
        self,
        agent_name: str,
        event_type: str,
        direction: str,
        payload: dict[str, Any],
        duration_ms: int = 0,
        provider: str = "",
        model: str = "",
        status: str = "ok",
    ) -> None:
        self._conn.execute(
            """INSERT INTO agent_events
               (event_time, ticket_id, agent_name, event_type, direction,
                payload, duration_ms, provider, model, status)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                current_ticket_id.get(""),
                agent_name,
                event_type,
                direction,
                json.dumps(payload, ensure_ascii=False, default=str),
                duration_ms,
                provider,
                model,
                status,
            ),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    def query(
        self,
        ticket_id: str | None = None,
        agent_name: str | None = None,
        event_type: str | None = None,
        limit: int = 300,
    ) -> list[dict]:
        clauses, params = [], []
        if ticket_id:
            clauses.append("ticket_id = ?")
            params.append(ticket_id)
        if agent_name:
            clauses.append("agent_name = ?")
            params.append(agent_name)
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        rows = self._conn.execute(
            f"SELECT * FROM agent_events {where} ORDER BY id DESC LIMIT ?", params
        ).fetchall()
        return [dict(r) for r in rows]

    def all_ticket_ids(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT ticket_id FROM agent_events "
            "WHERE ticket_id != '' ORDER BY ticket_id DESC"
        ).fetchall()
        return [r[0] for r in rows]

    def all_agent_names(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT agent_name FROM agent_events ORDER BY agent_name"
        ).fetchall()
        return [r[0] for r in rows]

    def all_event_types(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT event_type FROM agent_events ORDER BY event_type"
        ).fetchall()
        return [r[0] for r in rows]

    def count(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM agent_events"
        ).fetchone()[0]


# ── Singleton ──────────────────────────────────────────────────────────────
_store: EventStore | None = None


def get_event_store() -> EventStore:
    global _store
    if _store is None:
        from config.settings import settings
        _store = EventStore(settings.log_db_path)
    return _store
