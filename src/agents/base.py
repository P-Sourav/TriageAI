"""Base agent abstractions + the message type used for the live transcript."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.llm.client import LLMClient


@dataclass
class AgentMessage:
    """One turn in the visible multi-agent conversation."""
    agent: str                       # e.g. "Classifier Agent"
    icon: str                        # emoji shown in the UI bubble
    content: str                     # human-readable text
    data: dict[str, Any] = field(default_factory=dict)  # structured payload
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseAgent:
    name: str = "Agent"
    icon: str = "🤖"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def say(self, content: str, **data: Any) -> AgentMessage:
        return AgentMessage(agent=self.name, icon=self.icon, content=content, data=data)
