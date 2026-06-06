"""
Resolution Agent — Generation step of the RAG pipeline.

Given the retrieved context, it drafts a step-by-step resolution AND a
self-assessed confidence score. The confidence + priority drive the
orchestrator's escalate-vs-auto-resolve decision.
"""
from __future__ import annotations

import json

SYSTEM = (
    "You are a senior support resolution engineer. Using ONLY the provided knowledge "
    "context plus the ticket, write a concise, numbered, step-by-step resolution the "
    "user can follow. Then judge your own confidence (0.0-1.0) that these steps fully "
    "resolve the issue without a human. Be honest: if context is thin, score low.\n"
    'Respond ONLY as JSON: '
    '{"resolution": "...", "confidence": 0.0, "needs_human": false}.'
)

from src.agents.base import AgentMessage, BaseAgent


class ResolutionAgent(BaseAgent):
    name = "Resolution Agent"
    icon = "🛠️"

    def run(self, subject: str, description: str, category: str,
            context: str, screenshot_text: str = "") -> AgentMessage:
        user = (
            f"Category: {category}\n"
            f"Ticket subject: {subject}\n"
            f"Ticket body: {description}\n"
            f"Screenshot context: {screenshot_text or 'none'}\n\n"
            f"Knowledge context:\n{context or 'none available'}\n"
        )
        raw = self.llm.chat(system=SYSTEM, user=user, json_mode=True)
        parsed = self._safe_json(raw)

        resolution = parsed.get("resolution") or "Unable to draft an automated resolution."
        confidence = float(parsed.get("confidence", 0.0) or 0.0)
        needs_human = bool(parsed.get("needs_human", confidence < 0.5))

        return self.say(
            f"Drafted a resolution (self-confidence **{confidence:.0%}**).",
            resolution=resolution, confidence=confidence, needs_human=needs_human,
        )

    @staticmethod
    def _safe_json(raw: str) -> dict:
        try:
            return json.loads(raw)
        except Exception:
            s, e = raw.find("{"), raw.rfind("}")
            if s != -1 and e != -1:
                try:
                    return json.loads(raw[s:e + 1])
                except Exception:
                    pass
        return {}
