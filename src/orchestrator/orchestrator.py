"""
Orchestrator — the multi-agent control plane.

It runs the agents in sequence, applies the routing policy, persists the ticket,
and *yields* each AgentMessage as it happens so the UI can render a live,
streaming conversation. This is a deterministic state machine wrapping
non-deterministic LLM steps — the pattern that keeps agentic systems debuggable.

Flow:
  (optional) Vision  ->  Classifier  ->  Knowledge  ->  Resolution
                                              |
                         confidence >= T  and  priority not Critical
                          /                                   \
                  Auto-Resolve                            Escalate (email + persist)
"""
from __future__ import annotations

from typing import Iterator

from config.settings import settings
from src.agents.base import AgentMessage
from src.logging.context import current_ticket_id
from src.agents.classifier_agent import ClassifierAgent
from src.agents.escalation_agent import EscalationAgent
from src.agents.knowledge_agent import KnowledgeAgent
from src.agents.resolution_agent import ResolutionAgent
from src.knowledge_base.kb_store import KnowledgeBase
from src.knowledge_base.ticket_store import TicketStore
from src.llm.client import LLMClient
from src.models.ticket import Ticket, TicketStatus
from src.vision.screenshot_analyzer import ScreenshotAnalyzer


class Orchestrator:
    def __init__(self):
        self.llm = LLMClient()
        self.kb = KnowledgeBase(settings.db_path, self.llm)
        self.store = TicketStore(settings.db_path)
        self.vision = ScreenshotAnalyzer(self.llm)
        self.classifier = ClassifierAgent(self.llm)
        self.knowledge = KnowledgeAgent(self.llm, self.kb)
        self.resolver = ResolutionAgent(self.llm)
        self.escalator = EscalationAgent(self.llm)

    def handle(self, subject: str, description: str, user_email: str = "anonymous@user.com",
               screenshot_bytes: bytes | None = None,
               screenshot_media_type: str = "image/png") -> Iterator[AgentMessage]:
        ticket = Ticket(subject=subject, description=description, user_email=user_email)
        current_ticket_id.set(ticket.ticket_id)

        try:
            from src.logging.event_store import get_event_store
            get_event_store().log(
                agent_name="Orchestrator",
                event_type="ticket_received",
                direction="SEND",
                payload={
                    "subject": subject,
                    "description": description,
                    "user_email": user_email,
                    "has_screenshot": bool(screenshot_bytes),
                },
            )
        except Exception:
            pass

        # 0) Vision (optional)
        if screenshot_bytes:
            yield AgentMessage("Vision Analyzer", "🖼️", "Reading the uploaded screenshot…")
            ticket.screenshot_text = self.vision.analyze(screenshot_bytes, screenshot_media_type)
            yield AgentMessage("Vision Analyzer", "🖼️",
                               f"Extracted context: {ticket.screenshot_text}",
                               data={"screenshot_text": ticket.screenshot_text})

        # 1) Classify (few-shot)
        m = self.classifier.run(subject, description, ticket.screenshot_text)
        ticket.category = m.data["category"]
        ticket.priority = m.data["priority"]
        ticket.classifier_rationale = m.data["rationale"]
        yield m

        # 2) Retrieve knowledge
        k = self.knowledge.run(subject, description, ticket.screenshot_text)
        ticket.kb_references = k.data.get("references", [])
        yield k

        # 3) Draft resolution + confidence
        r = self.resolver.run(subject, description, ticket.category,
                              k.data.get("context", ""), ticket.screenshot_text)
        ticket.resolution = r.data["resolution"]
        ticket.confidence = r.data["confidence"]
        yield r

        # 4) Decision policy
        must_escalate = (
            ticket.priority in settings.auto_escalate_priorities
            or r.data["needs_human"]
            or ticket.confidence < settings.escalation_confidence_threshold
        )

        if must_escalate:
            reason = (
                f"priority={ticket.priority}"
                if ticket.priority in settings.auto_escalate_priorities
                else f"confidence {ticket.confidence:.0%} < "
                     f"{settings.escalation_confidence_threshold:.0%} threshold"
            )
            e = self.escalator.run(ticket, reason)
            yield e
        else:
            ticket.status = TicketStatus.AUTO_RESOLVED.value
            yield AgentMessage(
                "Resolution Agent", "✅",
                "Confidence is sufficient — auto-resolving and replying to the user:\n\n"
                f"{ticket.resolution}",
                data={"resolution": ticket.resolution, "auto_resolved": True},
            )

        # 5) Persist for future reference
        self.store.save(ticket)
        yield AgentMessage(
            "System", "💾",
            f"Ticket **{ticket.ticket_id}** saved — status **{ticket.status}**.",
            data={"ticket": ticket.to_dict()},
        )
