"""Seed the KB with historical, already-resolved tickets / articles."""
from __future__ import annotations

from src.knowledge_base.kb_store import KnowledgeBase

SEED_DOCS = [
    ("KB-001", "Reset a forgotten password",
     "Users who are locked out should use Settings > Security > Reset Password. "
     "A reset link is emailed and valid for 30 minutes. If 2FA is enabled, the "
     "backup codes screen unlocks recovery.", "Account"),
    ("KB-002", "Duplicate invoice charge",
     "Duplicate charges are usually a payment-gateway retry. Verify in the Billing "
     "dashboard under Transactions; if two identical charges exist within 5 minutes, "
     "issue a refund for the later one and notify the customer.", "Billing"),
    ("KB-003", "VPN connection drops / slow network",
     "Intermittent VPN drops are typically MTU mismatch. Set MTU to 1400, switch the "
     "client to TCP mode, and confirm the regional gateway is not in maintenance.", "Network"),
    ("KB-004", "Application returns HTTP 500 on checkout",
     "A 500 at /api/v1/checkout commonly stems from a null cart session. Clear the "
     "user's cart cache, redeploy the checkout service, and confirm the inventory "
     "service is reachable.", "Technical"),
    ("KB-005", "Clearing application cache",
     "Stale UI usually clears with a hard refresh and a server-side cache purge "
     "(Admin > Maintenance > Purge Cache). Ask the user to retry afterwards.", "Technical"),
]


def seed(kb: KnowledgeBase, force: bool = False) -> int:
    if kb.count() > 0 and not force:
        return kb.count()
    for doc_id, title, content, cat in SEED_DOCS:
        kb.add(doc_id, title, content, cat)
    return kb.count()
