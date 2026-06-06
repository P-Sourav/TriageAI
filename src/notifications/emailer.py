"""
Email notifier. Real SMTP in production; `EMAIL_DRY_RUN=true` records the message
instead of sending (perfect for demos / CI). Returns a structured result either way.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from config.settings import settings


def send_email(to: str, subject: str, body: str) -> dict:
    if settings.email_dry_run:
        return {"sent": False, "dry_run": True, "to": to,
                "subject": subject, "body": body}

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
        if settings.smtp_use_tls:
            s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password or "")
        s.send_message(msg)

    return {"sent": True, "dry_run": False, "to": to, "subject": subject, "body": body}
