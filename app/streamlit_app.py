"""
AI Ticket Resolver — Streamlit UI.

Run:  streamlit run app/streamlit_app.py

Renders a live, streaming multi-agent conversation as each agent in the
orchestrator yields its turn.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

# Make `config` and `src` importable when run via `streamlit run`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import settings                       # noqa: E402
from src.knowledge_base.kb_store import KnowledgeBase       # noqa: E402
from src.knowledge_base.seed_data import seed               # noqa: E402
from src.llm.client import LLMClient                        # noqa: E402
from src.orchestrator.orchestrator import Orchestrator      # noqa: E402

# --- Per-agent accent colors for the conversation bubbles -------------------
AGENT_COLORS = {
    "Vision Analyzer": "#7aa2f7",
    "Classifier Agent": "#bb9af7",
    "Knowledge Agent": "#7dcfff",
    "Resolution Agent": "#9ece6a",
    "Escalation Agent": "#f7768e",
    "System": "#565f89",
}

st.set_page_config(page_title="AI Ticket Resolver", page_icon="🎫", layout="wide")

# --- Custom theme: dark support command-center ------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Sora:wght@400;600;700&display=swap');
.stApp { background: radial-gradient(1200px 600px at 80% -10%, #16203a 0%, #0b0e14 55%); }
h1, h2, h3, .stMarkdown h1 { font-family: 'Sora', sans-serif !important; letter-spacing:-0.02em; }
body, p, .stMarkdown { font-family: 'Sora', sans-serif; }
.brand { font-family:'Space Mono', monospace; font-weight:700; font-size:2.0rem;
         color:#e6edf3; letter-spacing:-0.04em; }
.brand .accent { color:#56c2c0; }
.tagline { color:#8b98a5; font-family:'Space Mono', monospace; font-size:0.85rem; margin-top:-6px;}
.bubble { border-left:3px solid var(--c); background:rgba(255,255,255,0.03);
          border-radius:10px; padding:12px 16px; margin:10px 0; }
.bubble .who { font-family:'Space Mono', monospace; font-weight:700; color:var(--c);
               font-size:0.8rem; text-transform:uppercase; letter-spacing:0.05em; }
.bubble .body { color:#cdd6e3; margin-top:4px; white-space:pre-wrap; }
.pill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.72rem;
        font-family:'Space Mono', monospace; margin-right:6px; }
.stButton>button { background:#56c2c0; color:#06231f; font-weight:700; border:none;
                   border-radius:8px; font-family:'Space Mono', monospace; }
.stButton>button:hover { background:#6fdedc; color:#06231f; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand">TICKET<span class="accent">·</span>RESOLVER</div>'
            '<div class="tagline">multi-agent AI support // classify → retrieve → resolve → escalate</div>',
            unsafe_allow_html=True)
st.write("")


# --- Cached singletons -------------------------------------------------------
@st.cache_resource
def get_orchestrator() -> Orchestrator:
    orch = Orchestrator()
    seed(orch.kb)  # ensure KB is populated on first run
    return orch


orch = get_orchestrator()

# --- Sidebar: config + lookups ----------------------------------------------
with st.sidebar:
    st.subheader("⚙️ Runtime")
    st.caption(f"LLM provider: **{settings.llm_provider}**  ·  model: `{settings.llm_model}`")
    st.caption(f"Escalation threshold: **{settings.escalation_confidence_threshold:.0%}**")
    st.caption(f"KB documents loaded: **{orch.kb.count()}**")
    st.caption(f"Email mode: **{'DRY-RUN' if settings.email_dry_run else 'LIVE SMTP'}**")
    st.divider()
    st.subheader("🔎 Look up a ticket")
    tid = st.text_input("Ticket ID", placeholder="TCK-20260606-XXXXXX")
    if st.button("Fetch", use_container_width=True) and tid:
        rec = orch.store.get(tid.strip())
        st.json(rec) if rec else st.warning("No ticket with that ID.")
    st.divider()
    st.subheader("🗃️ Recent tickets")
    for t in orch.store.all()[:8]:
        st.caption(f"`{t['ticket_id']}` · {t['category']}/{t['priority']} · {t['status']}")

# --- Input panel -------------------------------------------------------------
col_l, col_r = st.columns([3, 2])
with col_l:
    subject = st.text_input("Subject", placeholder="e.g. Checkout page returns an error")
    description = st.text_area("Describe the issue", height=140,
                               placeholder="Type your message to the support bot…")
    user_email = st.text_input("Your email", value="customer@user.com")
with col_r:
    shot = st.file_uploader("Attach a screenshot (optional)",
                            type=["png", "jpg", "jpeg", "webp"])
    if shot:
        st.image(shot, caption="Attached screenshot", use_container_width=True)

go = st.button("🚀 Resolve ticket", use_container_width=True)

st.markdown("### 💬 Live agent conversation")
stream_area = st.container()


def render_bubble(area, agent: str, icon: str, body: str, data: dict):
    color = AGENT_COLORS.get(agent, "#56c2c0")
    pills = ""
    if "category" in data:
        pills += f'<span class="pill" style="background:#bb9af733;color:#bb9af7">{data["category"]}</span>'
    if "priority" in data:
        pills += f'<span class="pill" style="background:#f7768e33;color:#f7768e">{data["priority"]}</span>'
    if "confidence" in data:
        pills += f'<span class="pill" style="background:#9ece6a33;color:#9ece6a">conf {data["confidence"]:.0%}</span>'
    area.markdown(
        f'<div class="bubble" style="--c:{color}">'
        f'<div class="who">{icon} {agent}</div>'
        f'<div class="body">{body}</div>{pills}</div>',
        unsafe_allow_html=True,
    )


if go:
    if not (subject or description):
        st.error("Please enter a subject or description.")
    else:
        img_bytes = shot.read() if shot else None
        media = shot.type if shot else "image/png"
        with stream_area:
            for msg in orch.handle(subject=subject or description[:60],
                                   description=description or subject,
                                   user_email=user_email,
                                   screenshot_bytes=img_bytes,
                                   screenshot_media_type=media):
                render_bubble(stream_area, msg.agent, msg.icon, msg.content, msg.data)
                time.sleep(0.45)  # pacing for the "live" feel
        st.success("Conversation complete. Use the sidebar to look the ticket up anytime.")
