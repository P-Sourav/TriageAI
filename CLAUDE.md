# AI Ticket Resolver — Claude Code Guide

## Project Overview
Multi-agent AI support-ticket resolver. Streamlit UI → Orchestrator → Agent chain
(Vision → Classifier → Knowledge → Resolution → Escalation) → SQLite + SMTP.

## Commands

```bash
# Run the app (mock provider, no API key needed)
streamlit run app/streamlit_app.py

# Run tests
pytest tests/ -v

# Seed knowledge base
python scripts/seed_kb.py

# Regenerate architecture diagram (needs graphviz system package)
python diagrams/generate_architecture.py
```

## Key Files

| File | Role |
|------|------|
| `config/settings.py` | Single source of truth for all config; reads from `.env` |
| `src/llm/client.py` | Swap LLM provider here (openai / anthropic / mock) |
| `src/orchestrator/orchestrator.py` | Agent sequencing + escalation policy |
| `src/agents/` | One file per agent; all inherit `BaseAgent` |
| `src/knowledge_base/seed_data.py` | Add/edit KB articles here |
| `.env` | Local secrets — never commit this file |

## Architecture Decisions

- **Mock provider first**: The `mock` LLM uses keyword heuristics so the full
  pipeline runs with zero credentials. Switch provider in `.env`, not in code.
- **Confidence-based routing**: Escalation threshold lives in `settings.py`
  (`ESCALATION_THRESHOLD`, default 0.55). Adjust without touching agent code.
- **SQLite for everything**: Both ticket history and the vector KB use SQLite.
  Swap to pgvector/Pinecone by replacing `KnowledgeBase._search` — the `add`/`search`
  interface stays identical.
- **Dry-run email**: `EMAIL_DRY_RUN=true` (default) records escalations in DB
  instead of sending. Flip to `false` + set SMTP vars for real delivery.

## Adding a New Agent

1. Create `src/agents/my_agent.py`, subclass `BaseAgent`, implement `run()`
2. Return `self.say("message", **structured_data)` — the orchestrator streams this to the UI
3. Wire it in `src/orchestrator/orchestrator.py` at the appropriate state

## Environment

- Python ≥ 3.10
- All dependencies in `requirements.txt`
- Copy `.env.example` → `.env` before first run
