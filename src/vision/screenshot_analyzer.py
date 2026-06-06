"""
Screenshot Analyzer — turns an uploaded image into text context an LLM agent
can reason over (error dialogs, stack traces, UI state, etc.).
"""
from __future__ import annotations

import base64

from src.llm.client import LLMClient

VISION_PROMPT = (
    "You are a support engineer. Describe what this screenshot shows in 2-4 sentences: "
    "any error messages, codes, stack traces, affected screen/feature, and visible state. "
    "Quote exact error text if present."
)


class ScreenshotAnalyzer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze(self, image_bytes: bytes, media_type: str = "image/png") -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return self.llm.vision(VISION_PROMPT, b64, media_type=media_type)
