"""Tests for the Ticket domain model."""
import re
from src.models.ticket import Ticket, Category, Priority, TicketStatus, _ticket_id


def test_ticket_id_format():
    tid = _ticket_id()
    assert re.match(r"TCK-\d{8}-[A-F0-9]{6}", tid), f"Unexpected format: {tid}"


def test_ticket_ids_are_unique():
    ids = {_ticket_id() for _ in range(100)}
    assert len(ids) == 100


def test_default_values():
    t = Ticket(subject="Test", description="Desc")
    assert t.status == TicketStatus.OPEN
    assert t.priority == Priority.MEDIUM
    assert t.category == Category.OTHER
    assert t.confidence == 0.0
    assert t.kb_references == []


def test_to_dict_is_serializable():
    t = Ticket(subject="Test", description="Desc")
    d = t.to_dict()
    assert d["subject"] == "Test"
    assert "ticket_id" in d
    assert isinstance(d["kb_references"], list)
