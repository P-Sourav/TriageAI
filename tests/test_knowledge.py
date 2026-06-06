"""Tests for the KnowledgeBase vector store."""
from src.knowledge_base.kb_store import KnowledgeBase, KBHit


def test_seed_populates_kb(kb: KnowledgeBase):
    assert kb.count() >= 5


def test_search_returns_hits(kb: KnowledgeBase):
    hits = kb.search("forgot password reset", top_k=3)
    assert len(hits) > 0
    assert all(isinstance(h, KBHit) for h in hits)


def test_top_hit_is_most_relevant(kb: KnowledgeBase):
    hits = kb.search("duplicate invoice charge refund", top_k=3)
    assert hits[0].score >= hits[-1].score  # sorted descending


def test_add_and_search_custom_doc(kb: KnowledgeBase):
    kb.add("KB-TEST", "Widget installation guide",
           "Download the widget from portal, unzip, run install.sh.", "Technical")
    assert kb.count() >= 6


def test_cosine_identical_vectors():
    score = KnowledgeBase._cosine([1.0, 0.0], [1.0, 0.0])
    assert abs(score - 1.0) < 1e-9


def test_cosine_orthogonal_vectors():
    score = KnowledgeBase._cosine([1.0, 0.0], [0.0, 1.0])
    assert abs(score) < 1e-9


def test_cosine_empty_vectors():
    assert KnowledgeBase._cosine([], []) == 0.0
