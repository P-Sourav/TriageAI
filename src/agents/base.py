"""Base agent abstractions + the message type used for the live transcript."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.llm.client import LLMClient


@dataclass
class AgentMessage:
    """One turn in the visible multi-agent conversation."""
    agent: str
    icon: str
    content: str
    data: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseAgent:
    name: str = "Agent"
    icon: str = "🤖"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def say(self, content: str, **data: Any) -> AgentMessage:
        msg = AgentMessage(agent=self.name, icon=self.icon, content=content, data=data)
        try:
            from src.logging.event_store import get_event_store
            get_event_store().log(
                agent_name=self.name,
                event_type="agent_output",
                direction="RECEIVE",
                payload={"content": content, **data},
                provider=self.llm.provider,
            )
        except Exception:
            pass
        return msg
