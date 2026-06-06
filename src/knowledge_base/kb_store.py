"""
Knowledge Base store.

Holds resolved historical tickets + KB articles, and does semantic retrieval
via cosine similarity over embeddings. Kept storage-agnostic and tiny:
in-memory index backed by SQLite so the demo needs no external vector DB.
In production you'd swap `_search` for pgvector / Pinecone / Weaviate — the
interface (`add`, `search`) stays identical.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass

from src.llm.client import LLMClient


@dataclass
class KBHit:
    doc_id: str
    title: str
    content: str
    score: float


class KnowledgeBase:
    def __init__(self, db_path: str, llm: LLMClient):
        self.db_path = db_path
        self.llm = llm
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS kb_docs (
                doc_id   TEXT PRIMARY KEY,
                title    TEXT,
                content  TEXT,
                category TEXT,
                embedding TEXT
            )""")
        self._conn.commit()

    def add(self, doc_id: str, title: str, content: str, category: str = "Other") -> None:
        emb = self.llm.embed(f"{title}. {content}")
        self._conn.execute(
            "INSERT OR REPLACE INTO kb_docs VALUES (?,?,?,?,?)",
            (doc_id, title, content, category, ",".join(map(str, emb))),
        )
        self._conn.commit()

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM kb_docs").fetchone()[0]

    def search(self, query: str, top_k: int = 3) -> list[KBHit]:
        q = self.llm.embed(query)
        rows = self._conn.execute(
            "SELECT doc_id, title, content, embedding FROM kb_docs"
        ).fetchall()
        hits: list[KBHit] = []
        for doc_id, title, content, emb_str in rows:
            emb = [float(x) for x in emb_str.split(",")] if emb_str else []
            hits.append(KBHit(doc_id, title, content, self._cosine(q, emb)))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0
