"""
Classifier Agent — auto-categorizes a ticket using FEW-SHOT learning.

We inline a handful of labeled (input -> label) examples directly in the prompt.
The model generalizes from these exemplars without any fine-tuning. This is the
practical, production-friendly form of "few-shot learning" for LLMs.
"""
from __future__ import annotations

import json

from src.agents.base import AgentMessage, BaseAgent
from src.models.ticket import Category, Priority

# ---- The few-shot exemplars. Curate these from real, correctly-labeled tickets.
FEW_SHOT = """
Example 1
Ticket: "I was charged twice for my March subscription, please refund the extra one."
=> {"category": "Billing", "priority": "High", "rationale": "Duplicate payment dispute."}

Example 2
Ticket: "I can't log in, it says my account is locked after I changed my phone."
=> {"category": "Account", "priority": "High", "rationale": "Authentication / 2FA lockout."}

Example 3
Ticket: "The whole checkout page is down in production, customers can't pay!"
=> {"category": "Technical", "priority": "Critical", "rationale": "Production outage on a revenue path."}

Example 4
Ticket: "My VPN keeps dropping every few minutes and the dashboard loads slowly."
=> {"category": "Network", "priority": "Medium", "rationale": "Intermittent connectivity / latency."}

Example 5
Ticket: "How do I change the language of the interface to Spanish?"
=> {"category": "Other", "priority": "Low", "rationale": "General how-to question."}
""".strip()

SYSTEM = (
    "You are a senior support triage engineer. Classify the ticket into exactly one "
    f"category {[c.value for c in Category]} and one priority {[p.value for p in Priority]}. "
    "Learn from the labeled examples, then label the NEW ticket. "
    'Respond ONLY as JSON: {"category": "...", "priority": "...", "rationale": "..."}.'
)


class ClassifierAgent(BaseAgent):
    name = "Classifier Agent"
    icon = "🏷️"

    def run(self, subject: str, description: str, screenshot_text: str = "") -> AgentMessage:
        ticket_text = f"Subject: {subject}\nBody: {description}\nScreenshot: {screenshot_text}"
        prompt = f"{FEW_SHOT}\n\nNew Ticket:\n\"{ticket_text}\"\n=>"
        raw = self.llm.chat(system=SYSTEM, user=prompt, json_mode=True)
        parsed = self._safe_json(raw)

        category = self._coerce(parsed.get("category"), [c.value for c in Category], Category.OTHER.value)
        priority = self._coerce(parsed.get("priority"), [p.value for p in Priority], Priority.MEDIUM.value)
        rationale = parsed.get("rationale", "")

        return self.say(
            f"Categorized as **{category}** with **{priority}** priority. {rationale}",
            category=category, priority=priority, rationale=rationale,
        )

    @staticmethod
    def _safe_json(raw: str) -> dict:
        try:
            return json.loads(raw)
        except Exception:
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(raw[start:end + 1])
                except Exception:
                    pass
        return {}

    @staticmethod
    def _coerce(value, allowed: list[str], default: str) -> str:
        if not value:
            return default
        for a in allowed:
            if a.lower() == str(value).strip().lower():
                return a
        return default
