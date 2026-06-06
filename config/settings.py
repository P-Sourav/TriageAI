"""
Central configuration. All secrets/tunables come from environment variables
so the same image runs locally, in Docker, and in the cloud unchanged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # ---- LLM provider -------------------------------------------------------
    # provider: "openai" | "anthropic" | "mock"  (mock => fully offline demo)
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    vision_model: str = field(default_factory=lambda: os.getenv("VISION_MODEL", "gpt-4o-mini"))
    api_key: str | None = field(default_factory=lambda: os.getenv("LLM_API_KEY"))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2")))

    # ---- Decision thresholds -----------------------------------------------
    # If the resolution agent's confidence is below this, we escalate.
    escalation_confidence_threshold: float = field(
        default_factory=lambda: float(os.getenv("ESCALATION_THRESHOLD", "0.55"))
    )
    # Priorities that are *always* escalated regardless of confidence.
    auto_escalate_priorities: tuple[str, ...] = ("Critical",)

    # ---- Storage ------------------------------------------------------------
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "data/tickets.db"))

    # ---- Email (SMTP) -------------------------------------------------------
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "localhost"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "1025")))
    smtp_user: str | None = field(default_factory=lambda: os.getenv("SMTP_USER"))
    smtp_password: str | None = field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", "support-bot@company.com"))
    smtp_use_tls: bool = field(default_factory=lambda: _bool(os.getenv("SMTP_USE_TLS"), False))
    # When True we don't actually send – we record the email in the DB (great for demos).
    email_dry_run: bool = field(default_factory=lambda: _bool(os.getenv("EMAIL_DRY_RUN"), True))

    # Routing table: category -> manager email
    manager_routing: dict = field(default_factory=lambda: {
        "Billing": os.getenv("MGR_BILLING", "billing-lead@company.com"),
        "Technical": os.getenv("MGR_TECHNICAL", "tech-lead@company.com"),
        "Account": os.getenv("MGR_ACCOUNT", "account-lead@company.com"),
        "Network": os.getenv("MGR_NETWORK", "noc-lead@company.com"),
        "Other": os.getenv("MGR_OTHER", "support-lead@company.com"),
    })


settings = Settings()
