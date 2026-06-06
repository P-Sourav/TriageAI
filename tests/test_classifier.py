"""Tests for ClassifierAgent using the mock LLM provider."""
from src.agents.classifier_agent import ClassifierAgent
from src.agents.base import AgentMessage
from src.models.ticket import Category, Priority
from src.llm.client import LLMClient


def test_classifier_returns_agent_message(llm: LLMClient):
    agent = ClassifierAgent(llm)
    msg = agent.run(subject="App is down", description="500 error on checkout page")
    assert isinstance(msg, AgentMessage)


def test_classifier_category_is_valid(llm: LLMClient):
    agent = ClassifierAgent(llm)
    msg = agent.run(subject="Billing issue", description="I was charged twice")
    assert msg.data.get("category") in [c.value for c in Category]


def test_classifier_priority_is_valid(llm: LLMClient):
    agent = ClassifierAgent(llm)
    msg = agent.run(subject="Help needed", description="Cannot log in to my account")
    assert msg.data.get("priority") in [p.value for p in Priority]


def test_classifier_has_rationale(llm: LLMClient):
    agent = ClassifierAgent(llm)
    msg = agent.run(subject="VPN drops", description="VPN keeps disconnecting every few minutes")
    assert "rationale" in msg.data


def test_coerce_handles_bad_value():
    result = ClassifierAgent._coerce("unknown", ["Billing", "Technical"], "Other")
    assert result == "Other"


def test_coerce_case_insensitive():
    result = ClassifierAgent._coerce("billing", ["Billing", "Technical"], "Other")
    assert result == "Billing"


def test_safe_json_recovers_from_markdown():
    raw = 'Some text\n{"category": "Technical", "priority": "High", "rationale": "ok"}'
    parsed = ClassifierAgent._safe_json(raw)
    assert parsed["category"] == "Technical"
