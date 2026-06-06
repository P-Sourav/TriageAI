"""Domain models shared across agents."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Category(str, Enum):
    BILLING = "Billing"
    TECHNICAL = "Technical"
    ACCOUNT = "Account"
    NETWORK = "Network"
    OTHER = "Other"


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TicketStatus(str, Enum):
    OPEN = "Open"
    AUTO_RESOLVED = "Auto-Resolved"
    ESCALATED = "Escalated"


def _ticket_id() -> str:
    """Human-friendly, sortable, unique id, e.g. TCK-20260606-3F9A2C."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"TCK-{stamp}-{uuid.uuid4().hex[:6].upper()}"


@dataclass
class Ticket:
    subject: str
    description: str
    ticket_id: str = field(default_factory=_ticket_id)
    user_email: str = "anonymous@user.com"
    category: str = Category.OTHER.value
    priority: str = Priority.MEDIUM.value
    status: str = TicketStatus.OPEN.value
    confidence: float = 0.0
    resolution: str = ""
    screenshot_text: str = ""          # OCR / vision-extracted context
    classifier_rationale: str = ""
    kb_references: list[str] = field(default_factory=list)
    assigned_manager: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
