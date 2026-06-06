"""
Pluggable LLM client.

Design goals:
  * One interface (`chat`, `vision`, `embed`) the agents depend on.
  * Swap providers via env (`LLM_PROVIDER`) without touching agent code.
  * A `mock` provider that needs no API key, so the whole app is demoable offline.

This is the classic Strategy / Adapter pattern: agents code against the
abstraction, the concrete provider is injected at runtime.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from config.settings import settings


class LLMClient:
    def __init__(self, provider: str | None = None):
        self.provider = (provider or settings.llm_provider).lower()
        self._client = None
        if self.provider in {"openai", "anthropic"}:
            self._init_real_client()

    # -- provider bootstrap ---------------------------------------------------
    def _init_real_client(self) -> None:
        if not settings.api_key:
            raise RuntimeError(
                f"LLM_PROVIDER={self.provider} but LLM_API_KEY is empty. "
                "Set it in .env or use LLM_PROVIDER=mock."
            )
        if self.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.api_key)
        elif self.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(api_key=settings.api_key)

    # -- text chat ------------------------------------------------------------
    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        if self.provider == "mock":
            return self._mock_chat(system, user, json_mode)
        if self.provider == "openai":
            resp = self._client.chat.completions.create(
                model=settings.llm_model,
                temperature=settings.temperature,
                response_format={"type": "json_object"} if json_mode else {"type": "text"},
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
            )
            return resp.choices[0].message.content
        if self.provider == "anthropic":
            msg = self._client.messages.create(
                model=settings.llm_model,
                max_tokens=1024,
                temperature=settings.temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return msg.content[0].text
        raise ValueError(f"Unknown provider {self.provider}")

    # -- multimodal (screenshot) ---------------------------------------------
    def vision(self, prompt: str, image_b64: str, media_type: str = "image/png") -> str:
        if self.provider == "mock":
            return self._mock_vision(prompt)
        if self.provider == "openai":
            resp = self._client.chat.completions.create(
                model=settings.vision_model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url",
                     "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                ]}],
            )
            return resp.choices[0].message.content
        if self.provider == "anthropic":
            msg = self._client.messages.create(
                model=settings.vision_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "source": {"type": "base64",
                                                 "media_type": media_type,
                                                 "data": image_b64}},
                ]}],
            )
            return msg.content[0].text
        raise ValueError(f"Unknown provider {self.provider}")

    # -- embeddings (used by the Knowledge Agent's retriever) -----------------
    def embed(self, text: str) -> list[float]:
        if self.provider == "openai":
            v = self._client.embeddings.create(
                model="text-embedding-3-small", input=text
            )
            return v.data[0].embedding
        # mock / anthropic-without-embeddings fall back to a cheap deterministic
        # hashing embedding so cosine similarity still behaves sensibly.
        return self._hash_embed(text)

    # ========================= MOCK IMPLEMENTATIONS ==========================
    @staticmethod
    def _hash_embed(text: str, dim: int = 256) -> list[float]:
        vec = [0.0] * dim
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % dim] += 1.0
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    def _mock_chat(self, system: str, user: str, json_mode: bool) -> str:
        """Heuristic stand-in so the demo works with zero credentials."""
        text = user.lower()
        if "classify" in system.lower() or "category" in system.lower():
            # Only inspect the NEW ticket, not the few-shot exemplars in the prompt.
            if "new ticket:" in text:
                text = text.split("new ticket:", 1)[1]
            category, priority = "Other", "Medium"
            if any(k in text for k in ("invoice", "charge", "refund", "payment", "billing")):
                category, priority = "Billing", "High"
            elif any(k in text for k in ("login", "password", "account", "locked", "2fa")):
                category, priority = "Account", "High"
            elif any(k in text for k in ("slow", "timeout", "connection", "vpn", "wifi", "network")):
                category, priority = "Network", "Medium"
            elif any(k in text for k in ("error", "crash", "bug", "500", "exception", "fail")):
                category, priority = "Technical", "High"
            if any(k in text for k in ("down", "outage", "production", "data loss", "urgent")):
                priority = "Critical"
            return json.dumps({
                "category": category, "priority": priority,
                "rationale": f"Matched keywords characteristic of a {category} issue.",
            })
        if "confidence" in system.lower() or "resolution" in system.lower():
            known = any(k in text for k in ("password", "invoice", "vpn", "cache", "login"))
            return json.dumps({
                "resolution": (
                    "1) Reproduce the issue.\n2) Apply the documented fix from the "
                    "knowledge base.\n3) Verify with the user.\n4) Close once confirmed."
                ),
                "confidence": 0.82 if known else 0.40,
                "needs_human": not known,
            })
        return "I understand your issue and I'm looking into it right now."

    @staticmethod
    def _mock_vision(prompt: str) -> str:
        return ("[mock vision] The screenshot appears to show an application error "
                "dialog with a stack trace mentioning a NullPointerException and an "
                "HTTP 500 response from /api/v1/checkout.")
