"""
Diagrams-as-code for AI Ticket Resolver.

Run:  python diagrams/generate_architecture.py
Produces:
  diagrams/architecture.png / .svg   — full multi-agent flow
  diagrams/prerequisites.png / .svg  — tech stack & setup overview
"""
from __future__ import annotations

import os
from graphviz import Digraph

# ---------------------------------------------------------------------------
# Palette — vibrant dark "command-center" theme
# ---------------------------------------------------------------------------
BG     = "#0d1117"   # deep charcoal canvas
INK    = "#e6edf3"   # near-white text
MUTED  = "#8b949e"   # subtle edge / border tint

# (gradient_top, gradient_bottom, glow_border)
AMBER  = ("#f2c14e", "#c98b00", "#f5cc5e")   # User — gold
TEAL   = ("#56c2c0", "#1e8f8d", "#7ddedd")   # Streamlit UI — cyan
BLUE   = ("#7aa2f7", "#3a6ef5", "#a5c0ff")   # Agents / Orchestrator — electric blue
VIOLET = ("#9d7cd8", "#6038c0", "#bb99f0")   # Data layer — purple
RED    = ("#f7768e", "#d42047", "#ff97aa")   # Escalation — coral red
GREEN  = ("#9ece6a", "#5c9e30", "#b8e87e")   # Success / resolve — lime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def node(g, name: str, label: str, palette: tuple, shape: str = "box",
         bold: bool = False, large: bool = False) -> None:
    top, bot, border = palette
    g.node(
        name, label,
        shape=shape,
        style="filled,rounded",
        fillcolor=f"{top}:{bot}",
        gradientangle="90",
        fontcolor="#0d1117",
        color=border,
        penwidth="2.8" if bold else "2.0",
        fontname="Helvetica-Bold" if bold else "Helvetica",
        fontsize="13" if large else ("11" if bold else "10"),
        margin="0.24,0.14",
        height="0.55",
    )


def cluster(g, name: str, label: str, border_color: str):
    return g.subgraph(name=f"cluster_{name}", graph_attr={
        "label": f"  {label}  ",
        "color": border_color,
        "penwidth": "2.0",
        "fontcolor": INK,
        "fontname": "Helvetica-Bold",
        "fontsize": "12",
        "style": "rounded",
        "bgcolor": "#161b22",
        "margin": "16",
    })


def primary_edge(g, src: str, dst: str, label: str = "",
                 color: str = MUTED, bold: bool = False) -> None:
    g.edge(src, dst, f" {label} " if label else "",
           color=color, fontcolor=color,
           fontname="Helvetica", fontsize="9",
           penwidth="2.2" if bold else "1.6",
           arrowsize="0.85")


def dashed_edge(g, src: str, dst: str, label: str = "",
                color: str = "#555e6b") -> None:
    g.edge(src, dst, f" {label} " if label else "",
           style="dashed", color=color, fontcolor=color,
           fontname="Helvetica", fontsize="8",
           penwidth="1.2", arrowsize="0.7")


# ---------------------------------------------------------------------------
# Main architecture diagram
# ---------------------------------------------------------------------------
def build() -> Digraph:
    g = Digraph("AITicketResolver")
    g.attr(
        rankdir="TB",
        bgcolor=BG,
        fontname="Helvetica-Bold",
        fontcolor=INK,
        labelloc="t",
        fontsize="20",
        label="AI Ticket Resolver  —  Multi-Agent Architecture",
        splines="curved",
        nodesep="0.6",
        ranksep="0.9",
        pad="0.5",
        dpi="144",
    )
    g.attr("edge", fontname="Helvetica", fontsize="9")

    # ── User + UI ────────────────────────────────────────────────────────────
    node(g, "user", "👤  User\nchat  ·  screenshot", AMBER, shape="oval", bold=True, large=True)
    node(g, "ui",   "🖥️  Streamlit UI\nlive agent transcript",  TEAL,  bold=True)

    # ── Orchestrator ─────────────────────────────────────────────────────────
    node(g, "orch", "🧭  Orchestrator\nstate machine  ·  routing policy", BLUE, bold=True, large=True)

    # ── Agent layer ───────────────────────────────────────────────────────────
    with cluster(g, "agents", "⚙  Agent Layer", BLUE[2]) as c:
        node(c, "vision", "🖼️  Vision Analyzer\nscreenshot → context",  BLUE)
        node(c, "clf",    "🏷️  Classifier Agent\nfew-shot · category · priority", BLUE)
        node(c, "know",   "📚  Knowledge Agent\nRAG retrieve · cosine search",    BLUE)
        node(c, "res",    "🛠️  Resolution Agent\nRAG generate · confidence",      BLUE)
        node(c, "esc",    "🚨  Escalation Agent\nroute · notify manager",         RED, bold=True)

    # ── LLM client ───────────────────────────────────────────────────────────
    node(g, "llm", "🧠  LLM Client\nOpenAI  ·  Anthropic  ·  Mock", VIOLET, bold=True)

    # ── Data & integrations ───────────────────────────────────────────────────
    with cluster(g, "data", "🗄  Data & Integrations", VIOLET[2]) as d:
        node(d, "kb",      "📦  Knowledge Base\nembeddings  ·  cosine index", VIOLET, shape="cylinder")
        node(d, "tickets", "🗃️  Ticket Store\nSQLite  ·  audit log",          VIOLET, shape="cylinder")
        node(d, "smtp",    "✉️  SMTP / Email\nescalation relay",               VIOLET)
        node(d, "mgr",     "👔  Support Manager\nreceives escalation",         AMBER,  shape="oval")

    # ── Primary request lifecycle ─────────────────────────────────────────────
    primary_edge(g, "user",  "ui",   "1 · message / image",      TEAL[0],   bold=True)
    primary_edge(g, "ui",    "orch", "2 · submit",               TEAL[0],   bold=True)
    primary_edge(g, "orch",  "vision","3 · if image",            BLUE[0])
    primary_edge(g, "orch",  "clf",  "4 · classify",             BLUE[0])
    primary_edge(g, "orch",  "know", "5 · retrieve",             BLUE[0])
    primary_edge(g, "orch",  "res",  "6 · resolve",              GREEN[0])
    primary_edge(g, "orch",  "esc",  "7 · low-conf / Critical",  RED[0],    bold=True)

    # ── Stream response back to UI ────────────────────────────────────────────
    g.edge("orch", "ui", " 8 · stream turns ",
           color=TEAL[0], fontcolor=TEAL[0],
           fontname="Helvetica", fontsize="9",
           penwidth="2.0", arrowsize="0.85",
           constraint="false", style="dashed")

    # ── LLM calls (dashed) ────────────────────────────────────────────────────
    dashed_edge(g, "clf",    "llm", color=VIOLET[0])
    dashed_edge(g, "res",    "llm", color=VIOLET[0])
    dashed_edge(g, "vision", "llm", color=VIOLET[0])

    # ── Data flows ────────────────────────────────────────────────────────────
    primary_edge(g, "know",  "kb",      "vector search",   VIOLET[0])
    primary_edge(g, "esc",   "smtp",    "send · ticket id", RED[0], bold=True)
    primary_edge(g, "smtp",  "mgr",                        "", RED[0])
    dashed_edge( g, "orch",  "tickets", "persist")

    return g


# ---------------------------------------------------------------------------
# Prerequisites / tech-stack diagram
# ---------------------------------------------------------------------------
def prereqs() -> Digraph:
    p = Digraph("Prerequisites")
    p.attr(
        rankdir="TB",
        bgcolor=BG,
        fontname="Helvetica-Bold",
        fontcolor=INK,
        labelloc="t",
        fontsize="18",
        label="AI Ticket Resolver  —  Tech Stack & Setup",
        splines="ortho",
        nodesep="0.7",
        ranksep="0.8",
        pad="0.5",
        dpi="144",
    )
    p.attr("edge", fontname="Helvetica", fontsize="9", color=MUTED, fontcolor=MUTED)

    # ── Foundation row ────────────────────────────────────────────────────────
    with cluster(p, "runtime", "🐍  Runtime", BLUE[2]) as r:
        node(r, "py",  "🐍  Python\ncore language",    BLUE, bold=True, large=True)
        node(r, "pip", "📦  pip\npackage manager",     BLUE)

    # ── Core framework row ────────────────────────────────────────────────────
    with cluster(p, "framework", "🧱  Core Framework", TEAL[2]) as f:
        node(f, "st",     "🖥️  Streamlit\nUI + streaming",   TEAL)
        node(f, "np",     "🔢  NumPy\ncosine similarity",    TEAL)
        node(f, "sqlite", "🗄  SQLite\ntickets + KB",        TEAL)
        node(f, "dotenv", "🔐  python-dotenv\nconfig / secrets", TEAL)

    # ── LLM providers row ─────────────────────────────────────────────────────
    with cluster(p, "providers", "🧠  LLM Provider  (choose one)", VIOLET[2]) as l:
        node(l, "mock",      "🤖  Mock Provider\nbuilt-in · no key needed", GREEN,  bold=True)
        node(l, "openai",    "⚡  OpenAI\nchat · vision · embeddings",      VIOLET)
        node(l, "anthropic", "🌸  Anthropic\nchat · vision",                VIOLET)

    # ── Integrations row ──────────────────────────────────────────────────────
    with cluster(p, "integrations", "🔌  Integrations", AMBER[2]) as i:
        node(i, "smtp_i", "✉️  SMTP Server\nescalation emails",        AMBER)
        node(i, "gv_i",   "📐  Graphviz\ndiagram generation",          AMBER)

    # ── Dependency edges ──────────────────────────────────────────────────────
    for target in ["st", "np", "sqlite", "dotenv"]:
        p.edge("py", target, penwidth="1.5", arrowsize="0.75", color=TEAL[0], fontcolor=TEAL[0])

    for target in ["mock", "openai", "anthropic"]:
        p.edge("st", target, penwidth="1.4", arrowsize="0.75",
               color=VIOLET[0], fontcolor=VIOLET[0], style="dashed")

    p.edge("st",    "smtp_i", penwidth="1.2", arrowsize="0.7", color=AMBER[0], style="dashed")
    p.edge("gv_i",  "py",     penwidth="1.0", arrowsize="0.65", color=MUTED, style="dashed",
           constraint="false")

    return p


# ---------------------------------------------------------------------------
def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))

    g = build()
    g.render(os.path.join(here, "architecture"), format="png", cleanup=True)
    g.render(os.path.join(here, "architecture"), format="svg", cleanup=True)
    print("Wrote  diagrams/architecture.png  and  diagrams/architecture.svg")

    pr = prereqs()
    pr.render(os.path.join(here, "prerequisites"), format="png", cleanup=True)
    pr.render(os.path.join(here, "prerequisites"), format="svg", cleanup=True)
    print("Wrote  diagrams/prerequisites.png  and  diagrams/prerequisites.svg")


if __name__ == "__main__":
    main()
