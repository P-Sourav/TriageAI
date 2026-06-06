"""
Agent event store — writes to two places in parallel:

  data/agent_logs.db    SQLite (powers the Streamlit Agent Logs tab)
  data/agent_logs.json  Human-readable JSON array (open in VS Code / any editor)

Every LLM prompt, LLM response, and agent output is captured with:
  time        — UTC timestamp
  ticket_id   — TCK-… identifier
  agent       — which agent produced this event
  event_type  — ticket_received | llm_prompt | llm_response | agent_output
  direction   — SEND (going out) | RECEIVE (coming back)
  duration_ms — latency for LLM calls
  provider    — mock | openai | anthropic
  data        — full structured payload (parsed, not a raw string)
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
        self._json_path: str | None = None

        if db_path != ":memory:":
            dir_part = os.path.dirname(db_path)
            if dir_part:
                os.makedirs(dir_part, exist_ok=True)
            self._json_path = os.path.splitext(db_path)[0] + ".json"
            # Initialise JSON file as empty array if it doesn't exist yet
            if not os.path.exists(self._json_path):
                with open(self._json_path, "w", encoding="utf-8") as f:
                    json.dump([], f)

        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()

    # ── Write ─────────────────────────────────────────────────────────────────
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
        now        = datetime.now(timezone.utc).isoformat()
        ticket_id  = current_ticket_id.get("")
        payload_str = json.dumps(payload, ensure_ascii=False, default=str)

        # 1) SQLite (powers Streamlit viewer)
        self._conn.execute(
            """INSERT INTO agent_events
               (event_time, ticket_id, agent_name, event_type, direction,
                payload, duration_ms, provider, model, status)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (now, ticket_id, agent_name, event_type, direction,
             payload_str, duration_ms, provider, model, status),
        )
        self._conn.commit()

        # 2) JSON file (open directly in VS Code / any editor)
        self._append_json({
            "time":       now[:19].replace("T", " ") + " UTC",
            "ticket_id":  ticket_id,
            "agent":      agent_name,
            "event_type": event_type,
            "direction":  direction,
            "duration_ms": duration_ms,
            "provider":   provider,
            "model":      model,
            "data":       payload,          # parsed dict, not a raw string
        })

    def _append_json(self, event: dict) -> None:
        if not self._json_path:
            return
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                existing: list = json.load(f)
        except Exception:
            existing = []
        existing.append(event)
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

    # ── Read (Streamlit viewer) ───────────────────────────────────────────────
    def query(
        self,
        ticket_id: str | None = None,
        agent_name: str | None = None,
        event_type: str | None = None,
        limit: int = 300,
    ) -> list[dict]:
        clauses, params = [], []
        if ticket_id:
            clauses.append("ticket_id = ?");  params.append(ticket_id)
        if agent_name:
            clauses.append("agent_name = ?"); params.append(agent_name)
        if event_type:
            clauses.append("event_type = ?"); params.append(event_type)
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

    @property
    def json_path(self) -> str | None:
        return self._json_path


# ── Singleton ──────────────────────────────────────────────────────────────────
_store: EventStore | None = None


def get_event_store() -> EventStore:
    global _store
    if _store is None:
        from config.settings import settings
        _store = EventStore(settings.log_db_path)
    return _store
