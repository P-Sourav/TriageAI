"""Shared pytest fixtures. All tests use the mock LLM — no API key required."""
import os
import pytest

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DB_PATH", ":memory:")
os.environ.setdefault("LOG_DB_PATH", ":memory:")

from src.llm.client import LLMClient
from src.knowledge_base.kb_store import KnowledgeBase
from src.knowledge_base.seed_data import seed
from src.models.ticket import Ticket


@pytest.fixture(scope="session")
def llm() -> LLMClient:
    return LLMClient()


@pytest.fixture
def kb(llm: LLMClient) -> KnowledgeBase:
    store = KnowledgeBase(db_path=":memory:", llm=llm)
    seed(store)
    return store


@pytest.fixture
def sample_ticket() -> Ticket:
    return Ticket(
        subject="Cannot log in",
        description="I forgot my password and the reset email never arrives.",
        user_email="user@test.com",
    )
