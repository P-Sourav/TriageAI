"""
Escalation Agent — fires when automated resolution isn't trusted.

Responsibilities:
  * Pick the right manager from the routing table (by category).
  * Compose and send a handoff email containing the Ticket ID + full context.
  * Persist the ticket so the manager (and audits) can reference it later.
"""
from __future__ import annotations

from config.settings import settings
from src.agents.base import AgentMessage, BaseAgent
from src.models.ticket import Ticket, TicketStatus
from src.notifications.emailer import send_email


class EscalationAgent(BaseAgent):
    name = "Escalation Agent"
    icon = "🚨"

    def run(self, ticket: Ticket, reason: str) -> AgentMessage:
        manager = settings.manager_routing.get(
            ticket.category, settings.manager_routing["Other"]
        )
        ticket.assigned_manager = manager
        ticket.status = TicketStatus.ESCALATED.value

        subject = f"[ESCALATION] {ticket.ticket_id} – {ticket.category}/{ticket.priority} – {ticket.subject}"
        body = (
            f"Ticket ID : {ticket.ticket_id}\n"
            f"Category  : {ticket.category}\n"
            f"Priority  : {ticket.priority}\n"
            f"From      : {ticket.user_email}\n"
            f"Confidence: {ticket.confidence:.0%}\n"
            f"Reason    : {reason}\n"
            f"KB refs   : {', '.join(ticket.kb_references) or 'none'}\n"
            f"{'-' * 60}\n"
            f"Subject:\n{ticket.subject}\n\n"
            f"Description:\n{ticket.description}\n\n"
            f"Screenshot context:\n{ticket.screenshot_text or 'none'}\n\n"
            f"Draft (auto) resolution for review:\n{ticket.resolution}\n"
        )
        result = send_email(to=manager, subject=subject, body=body)

        mode = "recorded (dry-run)" if result.get("dry_run") else "sent"
        return self.say(
            f"Escalated **{ticket.ticket_id}** to **{manager}**. Email {mode}. Reason: {reason}",
            manager=manager, email=result, ticket_id=ticket.ticket_id,
        )
