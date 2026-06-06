"""
Knowledge Agent — Retrieval step of a RAG pipeline.

It queries the Knowledge Base for the most semantically similar historical
resolutions and hands them to the Resolution Agent as grounding context.
"""
from __future__ import annotations

from src.agents.base import AgentMessage, BaseAgent
from src.knowledge_base.kb_store import KnowledgeBase


class KnowledgeAgent(BaseAgent):
    name = "Knowledge Agent"
    icon = "📚"

    def __init__(self, llm, kb: KnowledgeBase):
        super().__init__(llm)
        self.kb = kb

    def run(self, subject: str, description: str, screenshot_text: str = "",
            top_k: int = 3) -> AgentMessage:
        query = f"{subject} {description} {screenshot_text}".strip()
        hits = self.kb.search(query, top_k=top_k)

        if not hits or hits[0].score < 0.05:
            return self.say(
                "No closely matching prior resolution found in the knowledge base.",
                hits=[], context="",
            )

        bullets = "\n".join(f"- [{h.doc_id}] {h.title} (match {h.score:.0%})" for h in hits)
        context = "\n\n".join(f"[{h.doc_id}] {h.title}\n{h.content}" for h in hits)
        refs = [h.doc_id for h in hits]
        return self.say(
            f"Found {len(hits)} relevant references:\n{bullets}",
            hits=[h.__dict__ for h in hits], context=context, references=refs,
            top_score=hits[0].score,
        )
