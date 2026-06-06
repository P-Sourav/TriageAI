"""
Auto-generate the system architecture diagram (diagrams-as-code).

Run:  python diagrams/generate_architecture.py
Produces: diagrams/architecture.png and diagrams/architecture.svg

Using Graphviz means the diagram lives in version control and regenerates
deterministically in CI — no manual drawing tools, no drift from the code.
"""
from __future__ import annotations

import os
from graphviz import Digraph

# ---- Palette (dark "support command-center" theme) --------------------------
BG = "#0f1419"
INK = "#e6edf3"
EDGE = "#8b98a5"
USER = "#f2c14e"      # amber
UI = "#56c2c0"        # teal
AGENT = "#7aa2f7"     # blue
DATA = "#9d7cd8"      # violet
ALERT = "#f7768e"     # red


def node(g, name, label, fill, shape="box"):
    g.node(name, label, shape=shape, style="filled,rounded",
           fillcolor=fill, fontcolor="#0b0e14", color=fill,
           fontname="Helvetica", fontsize="11", margin="0.18,0.10")


def build() -> Digraph:
    g = Digraph("AITicketResolver", format="png")
    g.attr(rankdir="TB", bgcolor=BG, fontname="Helvetica",
           fontcolor=INK, labelloc="t", fontsize="18",
           label="AI Ticket Resolver — Multi-Agent Architecture")
    g.attr("edge", color=EDGE, fontcolor=INK, fontname="Helvetica", fontsize="9")

    # A. Client / UI
    node(g, "user", "👤 User\n(chat + screenshot)", USER, shape="oval")
    node(g, "ui", "🖥️ Streamlit UI\nlive agent transcript", UI)

    # B. Orchestrator
    node(g, "orch", "🧭 Orchestrator\n(state machine + policy)", AGENT)

    # C. Agents cluster
    with g.subgraph(name="cluster_agents") as c:
        c.attr(label="Agent Layer", color=EDGE, fontcolor=INK, style="rounded")
        node(c, "vision", "🖼️ Vision Analyzer", AGENT)
        node(c, "clf", "🏷️ Classifier Agent\n(few-shot)", AGENT)
        node(c, "know", "📚 Knowledge Agent\n(RAG retrieve)", AGENT)
        node(c, "res", "🛠️ Resolution Agent\n(RAG generate + confidence)", AGENT)
        node(c, "esc", "🚨 Escalation Agent", ALERT)

    # D. Shared services
    node(g, "llm", "🧠 LLM Client\n(OpenAI / Anthropic / mock)", DATA, shape="box")

    # E. Data + integrations
    with g.subgraph(name="cluster_data") as d:
        d.attr(label="Data & Integrations", color=EDGE, fontcolor=INK, style="rounded")
        node(d, "kb", "🗄️ Knowledge Base\n(embeddings + cosine)", DATA, shape="cylinder")
        node(d, "tickets", "🗃️ Ticket Store\n(SQLite)", DATA, shape="cylinder")
        node(d, "smtp", "✉️ SMTP / Email", DATA)
        node(d, "mgr", "👔 Ticket Manager", USER, shape="oval")

    # ---- Edges (the request lifecycle) -------------------------------------
    g.edge("user", "ui", "1. message / image")
    g.edge("ui", "orch", "2. submit")
    g.edge("orch", "vision", "3. if image")
    g.edge("orch", "clf", "4. classify")
    g.edge("orch", "know", "5. retrieve")
    g.edge("orch", "res", "6. resolve")
    g.edge("orch", "esc", "7. if low conf / Critical", color=ALERT, fontcolor=ALERT)

    g.edge("clf", "llm", style="dashed")
    g.edge("res", "llm", style="dashed")
    g.edge("vision", "llm", style="dashed")
    g.edge("know", "kb", "vector search")
    g.edge("esc", "smtp", "send w/ ticket id", color=ALERT)
    g.edge("smtp", "mgr", color=ALERT)
    g.edge("orch", "tickets", "persist", style="dashed")
    g.edge("orch", "ui", "8. stream turns", constraint="false", color=UI, fontcolor=UI)

    return g


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    g = build()
    g.render(os.path.join(here, "architecture"), format="png", cleanup=True)
    g.render(os.path.join(here, "architecture"), format="svg", cleanup=True)
    print("Wrote diagrams/architecture.png and diagrams/architecture.svg")


if __name__ == "__main__":
    main()
