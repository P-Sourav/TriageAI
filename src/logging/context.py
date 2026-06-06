"""Lightweight context variable so ticket_id propagates to all loggers automatically."""
from contextvars import ContextVar

current_ticket_id: ContextVar[str] = ContextVar("current_ticket_id", default="")
