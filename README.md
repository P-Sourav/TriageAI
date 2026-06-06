# AI Ticket Resolver — Multi-Agent Support System

A production-shaped, multi-agent AI support assistant. A user submits a problem
(text and/or a screenshot); a chain of specialized agents classifies it,
retrieves relevant past resolutions, drafts a fix with a self-assessed
confidence score, and either **auto-resolves** or **escalates** to the right
manager by email — all streamed live in a Streamlit UI.

---

## Architecture

```
                        ┌──────────────────────────────────────────────┐
                        │              Streamlit UI                    │
                        │        (live agent transcript)               │
                        └──────────────────┬───────────────────────────┘
                                           │ submit
                                           ▼
                        ┌──────────────────────────────────────────────┐
                        │              Orchestrator                    │
                        │         (state machine + policy)             │
                        └──┬────────┬──────────┬────────────┬──────────┘
                           │        │          │            │
                    if img │ 4.clf  │ 5.retrvl │ 6.resolve  │ 7. low-conf/Critical
                           ▼        ▼          ▼            ▼
              ┌────────────────────────────────────────────────────────┐
              │                     Agent Layer                        │
              │  Vision   Classifier   Knowledge   Resolution  Escalation│
              │  Analyzer  (few-shot)  (RAG retrv) (RAG gen)   Agent   │
              └───────┬──────────┬──────────┬──────────┬──────────┬────┘
                      │          │          │          │          │
                      └──────────┴──────────┘          │     SMTP/Email
                             LLM Client            KB (cosine)      │
                        (OpenAI/Anthropic/mock)    SQLite        Manager
                                                  Ticket Store
```

See `diagrams/architecture.png` for the full rendered diagram.  
Regenerate it with: `python diagrams/generate_architecture.py`

---

## Tech Stack

| Layer | Tool | Version | Notes |
|---|---|---|---|
| UI | [Streamlit](https://streamlit.io) | ≥ 1.40 | Live streaming agent transcript |
| LLM — OpenAI | `openai` SDK | ≥ 1.0 | GPT-4o-mini (chat + vision + embeddings) |
| LLM — Anthropic | `anthropic` SDK | ≥ 0.25 | Claude 3.5 Haiku (chat + vision) |
| LLM — Offline | Mock provider | built-in | Keyword heuristics, no API key needed |
| Vector Search | NumPy cosine similarity | ≥ 1.24 | Semantic KB lookup |
| Database | SQLite 3 | stdlib | Ticket history + knowledge base |
| Vision | Multimodal LLM API | — | Base64 image → extracted error context |
| Email / SMTP | `smtplib` | stdlib | Escalation notifications (dry-run by default) |
| Diagram | [Graphviz](https://graphviz.org) | ≥ 0.20 (Python) | Architecture diagram as code |
| Config | `python-dotenv` | ≥ 1.0 | `.env` → `config/settings.py` |

---

## Prerequisites

### Required

| Requirement | Version | Check |
|---|---|---|
| Python | ≥ 3.10 | `python --version` |
| pip | ≥ 23 | `pip --version` |

### Optional — for real LLM calls

| Option | Details |
|---|---|
| OpenAI API key | Set `LLM_PROVIDER=openai` + `LLM_API_KEY=sk-...` |
| Anthropic API key | Set `LLM_PROVIDER=anthropic` + `LLM_API_KEY=sk-ant-...` |

### Optional — for diagram regeneration

| Requirement | Install |
|---|---|
| Graphviz (system) | `winget install graphviz` / `brew install graphviz` / `sudo apt install graphviz` |
| graphviz (Python) | included in `requirements.txt` |

### Optional — for real email escalation

| Requirement | Details |
|---|---|
| SMTP server | Any SMTP relay (Gmail, SendGrid, or local `aiosmtpd`) |
| Env vars | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_FROM`, `EMAIL_DRY_RUN=false` |

---

## Quick Start (offline — no API key needed)

```bash
# 1. Clone and enter the project
git clone https://github.com/P-Sourav/TriageAI.git
cd TriageAI

# 2. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment config (mock provider is the default)
cp .env.example .env

# 5. Run the app
streamlit run app/streamlit_app.py
```

Open `http://localhost:8501` — the mock provider works with zero credentials.

---

## Use a Real LLM

Edit `.env`:

```env
LLM_PROVIDER=openai           # or: anthropic
LLM_MODEL=gpt-4o-mini         # any chat + vision capable model
LLM_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
```

For Anthropic:

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-haiku-20241022
LLM_API_KEY=sk-ant-...
```

---

## Real Escalation Emails

Set `EMAIL_DRY_RUN=false` in `.env` and fill the SMTP vars:

```env
EMAIL_DRY_RUN=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your-app-password
EMAIL_FROM=support-bot@yourcompany.com
```

For local SMTP testing (no real server needed):

```bash
pip install aiosmtpd
python -m aiosmtpd -n -l localhost:1025
# Then set SMTP_HOST=localhost SMTP_PORT=1025 EMAIL_DRY_RUN=false
```

---

## Project Structure

```
ai-ticket-resolver/
│
├── .env.example                  # All env vars with defaults and docs
├── .gitignore
├── README.md
├── requirements.txt
├── Makefile                      # Convenience commands
│
├── .streamlit/
│   └── config.toml               # Dark theme + server settings
│
├── app/
│   └── streamlit_app.py          # Streamlit UI entry point
│
├── config/
│   ├── __init__.py
│   └── settings.py               # Env-driven configuration & manager routing
│
├── data/                         # SQLite DB files (git-ignored, dir tracked)
│   └── .gitkeep
│
├── diagrams/
│   ├── architecture.png          # Rendered diagram (committed)
│   ├── architecture.svg
│   └── generate_architecture.py  # Diagram as code — run to regenerate
│
├── scripts/
│   └── seed_kb.py                # Populate knowledge base with sample articles
│
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py               # BaseAgent + AgentMessage types
│   │   ├── classifier_agent.py   # Few-shot ticket categorization
│   │   ├── escalation_agent.py   # Routes + emails manager
│   │   ├── knowledge_agent.py    # RAG semantic retrieval
│   │   └── resolution_agent.py   # RAG generation + confidence scoring
│   ├── knowledge_base/
│   │   ├── __init__.py
│   │   ├── kb_store.py           # Vector KB (SQLite + cosine similarity)
│   │   ├── seed_data.py          # Sample KB articles
│   │   └── ticket_store.py       # Ticket CRUD + persistence
│   ├── llm/
│   │   ├── __init__.py
│   │   └── client.py             # LLM adapter: OpenAI / Anthropic / mock
│   ├── models/
│   │   ├── __init__.py
│   │   └── ticket.py             # Ticket dataclass + ID generation
│   ├── notifications/
│   │   ├── __init__.py
│   │   └── emailer.py            # SMTP escalation emails (dry-run safe)
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── orchestrator.py       # State machine wiring all agents + policy
│   └── vision/
│       ├── __init__.py
│       └── screenshot_analyzer.py # Screenshot → base64 → LLM vision → text
│
└── tests/
    ├── __init__.py
    ├── conftest.py               # Shared pytest fixtures
    ├── test_classifier.py
    ├── test_knowledge.py
    └── test_ticket_model.py
```

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` / `openai` / `anthropic` |
| `LLM_MODEL` | `gpt-4o-mini` | Chat model ID |
| `LLM_API_KEY` | _(empty)_ | API key for chosen provider |
| `VISION_MODEL` | `gpt-4o-mini` | Model used for screenshot analysis |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embeddings model (OpenAI only) |
| `ESCALATION_THRESHOLD` | `0.55` | Confidence cutoff (0.0–1.0); below → escalate |
| `MAX_KB_RESULTS` | `3` | Top-k KB docs retrieved per query |
| `DB_PATH` | `data/tickets.db` | SQLite file path |
| `EMAIL_DRY_RUN` | `true` | `false` to send real emails |
| `SMTP_HOST` | `localhost` | SMTP server hostname |
| `SMTP_PORT` | `1025` | SMTP server port |
| `SMTP_USER` | _(empty)_ | SMTP login username |
| `SMTP_PASS` | _(empty)_ | SMTP login password |
| `EMAIL_FROM` | `bot@example.com` | Sender address |
| `MGR_BILLING` | `billing-mgr@example.com` | Escalation target for Billing tickets |
| `MGR_TECHNICAL` | `tech-lead@example.com` | Escalation target for Technical tickets |
| `MGR_ACCOUNT` | `accounts@example.com` | Escalation target for Account tickets |
| `MGR_NETWORK` | `network-ops@example.com` | Escalation target for Network tickets |
| `MGR_OTHER` | `support-mgr@example.com` | Escalation target for uncategorized tickets |

---

## Escalation Logic

A ticket escalates when **any** of these conditions hold:

1. Priority is `Critical` → always escalate, regardless of confidence
2. Resolution Agent sets `needs_human = true` (model decided it cannot handle it)
3. Resolution confidence `< ESCALATION_THRESHOLD` (default 55%)

Otherwise the ticket auto-resolves and the drafted resolution is shown to the user.
Every ticket is persisted under a `TCK-YYYYMMDD-XXXXXX` ID for later lookup
(sidebar) and audit.

---

## Running Tests

```bash
# Install dev dependencies (pytest is included in requirements.txt)
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --tb=short
```

Tests use the `mock` provider — no API key required.

---

## Makefile Commands

```bash
make install    # create venv + install dependencies
make run        # launch Streamlit app
make seed       # populate knowledge base with sample articles
make test       # run pytest suite
make diagram    # regenerate architecture diagram (requires graphviz)
make clean      # remove __pycache__, .pyc, and SQLite DB
```
