"""
Seed the knowledge base with sample support articles.

Run:  python scripts/seed_kb.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.knowledge_base.kb_store import KnowledgeBase
from src.knowledge_base.seed_data import SEED_DOCS, seed
from src.llm.client import LLMClient
from config.settings import settings


def main() -> None:
    os.makedirs("data", exist_ok=True)
    print(f"Seeding KB (provider: {settings.llm_provider})")
    llm = LLMClient()
    kb = KnowledgeBase(db_path=settings.db_path, llm=llm)
    count = seed(kb, force=True)
    print(f"Done. KB contains {count} articles:")
    for doc_id, title, _, category in SEED_DOCS:
        print(f"  [{category:10}] {doc_id} — {title}")


if __name__ == "__main__":
    main()
