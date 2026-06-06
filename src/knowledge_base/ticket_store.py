"""Persists tickets so any ticket_id can be referenced later (audits, managers)."""
from __future__ import annotations

import json
import sqlite3

from src.models.ticket import Ticket


class TicketStore:
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                payload   TEXT,
                created_at TEXT
            )""")
        self._conn.commit()

    def save(self, ticket: Ticket) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO tickets VALUES (?,?,?)",
            (ticket.ticket_id, json.dumps(ticket.to_dict()), ticket.created_at),
        )
        self._conn.commit()

    def get(self, ticket_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT payload FROM tickets WHERE ticket_id=?", (ticket_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def all(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT payload FROM tickets ORDER BY created_at DESC"
        ).fetchall()
        return [json.loads(r[0]) for r in rows]
