# 🎫 AI Ticket Resolver — Multi-Agent Support System

A production-shaped, multi-agent AI support assistant. A user submits a problem
(text **and/or** a screenshot); a chain of specialized agents classifies it,
retrieves relevant past resolutions, drafts a fix with a self-assessed
confidence score, and either **auto-resolves** or **escalates** to the right
manager by email — all streamed live in a Streamlit UI.

```
Vision → Classifier (few-shot) → Knowledge (RAG retrieve) → Resolution (RAG generate)
                                          │
                       confident & not Critical?  ── yes ─→ Auto-resolve + reply
                                          └────────── no ──→ Escalation Agent → email manager + persist
```

## Quick start (zero credentials, offline)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # LLM_PROVIDER defaults to "mock"
sudo apt-get install -y graphviz # system Graphviz, for the diagram
python diagrams/generate_architecture.py     # regenerate the diagram
streamlit run app/streamlit_app.py
```

The `mock` provider makes the entire app work with **no API key** so you can
demo the flow immediately.

## Use a real model

Edit `.env`:

```env
LLM_PROVIDER=openai        # or: anthropic
LLM_MODEL=gpt-4o-mini      # any chat+vision capable model
LLM_API_KEY=sk-...
```

`pip install openai` (or `anthropic`) for the provider you choose.

## Real escalation emails

Set `EMAIL_DRY_RUN=false` and fill the `SMTP_*` vars in `.env`. For local
testing, run a fake SMTP inbox: `python -m aiosmtpd -n -l localhost:1025`.

## Layout

| Path | Responsibility |
|------|----------------|
| `config/settings.py` | Env-driven configuration & routing table |
| `src/llm/client.py` | Pluggable LLM adapter (OpenAI / Anthropic / mock) |
| `src/agents/` | Classifier, Knowledge, Resolution, Escalation agents |
| `src/vision/` | Screenshot → text context |
| `src/knowledge_base/` | Vector KB + ticket persistence (SQLite) |
| `src/orchestrator/` | State machine that wires agents + policy |
| `app/streamlit_app.py` | Live conversation UI |
| `diagrams/` | Auto-generated architecture diagram (as code) |

## How the agents decide to escalate

A ticket escalates when **any** of these hold:
1. priority is `Critical`, **or**
2. the Resolution Agent flags `needs_human`, **or**
3. resolution confidence `< ESCALATION_THRESHOLD` (default 55%).

Otherwise it auto-resolves and replies to the user. Every ticket is persisted
under a `TCK-YYYYMMDD-XXXXXX` id for later lookup (sidebar) and audit.
