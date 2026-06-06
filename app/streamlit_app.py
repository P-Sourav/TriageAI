"""
AI Ticket Resolver — Streamlit UI.

Run:  streamlit run app/streamlit_app.py

Two tabs:
  🎫 Resolve Ticket — submit a ticket and watch the live agent conversation
  📊 Agent Logs     — inspect every LLM prompt/response and agent output
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import settings                        # noqa: E402
from src.knowledge_base.seed_data import seed               # noqa: E402
from src.orchestrator.orchestrator import Orchestrator      # noqa: E402
from src.logging.event_store import get_event_store         # noqa: E402

AGENT_COLORS = {
    "Vision Analyzer":  "#7aa2f7",
    "Classifier Agent": "#bb9af7",
    "Knowledge Agent":  "#7dcfff",
    "Resolution Agent": "#9ece6a",
    "Escalation Agent": "#f7768e",
    "System":           "#565f89",
}

DIRECTION_COLOR = {"SEND": "#56c2c0", "RECEIVE": "#9ece6a"}
EVENT_COLOR = {
    "llm_prompt":      "#7aa2f7",
    "llm_response":    "#9ece6a",
    "agent_output":    "#bb9af7",
    "ticket_received": "#f2c14e",
}

st.set_page_config(page_title="AI Ticket Resolver", page_icon="🎫", layout="wide")

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
.log-row { border-left:3px solid var(--lc); background:rgba(255,255,255,0.02);
           border-radius:8px; padding:8px 14px; margin:6px 0; }
.log-meta { font-family:'Space Mono', monospace; font-size:0.75rem; color:#8b98a5; }
.log-badge { display:inline-block; padding:1px 8px; border-radius:999px; font-size:0.70rem;
             font-family:'Space Mono', monospace; margin-right:5px; font-weight:700; }
.stButton>button { background:#56c2c0; color:#06231f; font-weight:700; border:none;
                   border-radius:8px; font-family:'Space Mono', monospace; }
.stButton>button:hover { background:#6fdedc; color:#06231f; }
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="brand">TICKET<span class="accent">·</span>RESOLVER</div>'
    '<div class="tagline">multi-agent AI support // classify → retrieve → resolve → escalate</div>',
    unsafe_allow_html=True,
)
st.write("")


@st.cache_resource
def get_orchestrator() -> Orchestrator:
    orch = Orchestrator()
    seed(orch.kb)
    return orch


orch = get_orchestrator()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ Runtime")
    st.caption(f"LLM provider: **{settings.llm_provider}**  ·  model: `{settings.llm_model}`")
    st.caption(f"Escalation threshold: **{settings.escalation_confidence_threshold:.0%}**")
    st.caption(f"KB documents: **{orch.kb.count()}**")
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


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_resolve, tab_logs = st.tabs(["🎫  Resolve Ticket", "📊  Agent Logs"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Resolve Ticket
# ─────────────────────────────────────────────────────────────────────────────
with tab_resolve:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        subject     = st.text_input("Subject", placeholder="e.g. Checkout page returns an error")
        description = st.text_area("Describe the issue", height=140,
                                   placeholder="Type your message to the support bot…")
        user_email  = st.text_input("Your email", value="customer@user.com")
    with col_r:
        shot = st.file_uploader("Attach a screenshot (optional)",
                                type=["png", "jpg", "jpeg", "webp"])
        if shot:
            st.image(shot, caption="Attached screenshot", use_container_width=True)

    go = st.button("🚀 Resolve ticket", use_container_width=True)
    st.markdown("### 💬 Live agent conversation")
    stream_area = st.container()

    if go:
        if not (subject or description):
            st.error("Please enter a subject or description.")
        else:
            img_bytes = shot.read() if shot else None
            media     = shot.type if shot else "image/png"
            with stream_area:
                for msg in orch.handle(
                    subject=subject or description[:60],
                    description=description or subject,
                    user_email=user_email,
                    screenshot_bytes=img_bytes,
                    screenshot_media_type=media,
                ):
                    render_bubble(stream_area, msg.agent, msg.icon, msg.content, msg.data)
                    time.sleep(0.45)
            st.success("Done. Switch to **📊 Agent Logs** to inspect every prompt and response.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Agent Logs
# ─────────────────────────────────────────────────────────────────────────────
with tab_logs:
    store = get_event_store()

    # ── Filters ──────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])
    with fc1:
        ticket_ids   = ["All"] + store.all_ticket_ids()
        f_ticket     = st.selectbox("Ticket", ticket_ids, key="log_ticket")
    with fc2:
        agent_names  = ["All"] + store.all_agent_names()
        f_agent      = st.selectbox("Agent", agent_names, key="log_agent")
    with fc3:
        event_types  = ["All"] + store.all_event_types()
        f_type       = st.selectbox("Event type", event_types, key="log_type")
    with fc4:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    events = store.query(
        ticket_id  = None if f_ticket == "All" else f_ticket,
        agent_name = None if f_agent  == "All" else f_agent,
        event_type = None if f_type   == "All" else f_type,
        limit=300,
    )

    total = store.count()
    st.caption(f"Showing **{len(events)}** of **{total}** total events · most recent first")
    st.divider()

    if not events:
        st.info("No events logged yet. Submit a ticket on the **🎫 Resolve Ticket** tab first.")
    else:
        for ev in events:
            dir_color  = DIRECTION_COLOR.get(ev["direction"], "#8b98a5")
            type_color = EVENT_COLOR.get(ev["event_type"], "#8b98a5")
            ts_short   = ev["event_time"][11:19] + " UTC"
            dur        = f"  ·  `{ev['duration_ms']} ms`" if ev["duration_ms"] else ""
            ticket_lbl = f"  ·  `{ev['ticket_id']}`" if ev["ticket_id"] else ""

            label = (
                f'<span class="log-badge" style="background:{dir_color}22;color:{dir_color}">'
                f'{ev["direction"]}</span>'
                f'<span class="log-badge" style="background:{type_color}22;color:{type_color}">'
                f'{ev["event_type"]}</span>'
                f'<span style="color:#e6edf3;font-weight:600"> {ev["agent_name"]}</span>'
                f'<span class="log-meta">{ticket_lbl}  ·  {ts_short}{dur}</span>'
            )

            st.markdown(
                f'<div class="log-row" style="--lc:{type_color}">{label}</div>',
                unsafe_allow_html=True,
            )
            with st.expander("View payload"):
                if ev["provider"]:
                    st.caption(
                        f"provider: `{ev['provider']}`  ·  model: `{ev['model']}`  "
                        f"·  status: `{ev['status']}`"
                    )
                try:
                    parsed = json.loads(ev["payload"])
                    st.json(parsed)
                except Exception:
                    st.code(ev["payload"], language="text")
