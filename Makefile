.PHONY: install run seed test diagram clean

VENV    = .venv
PYTHON  = $(VENV)/bin/python
PIP     = $(VENV)/bin/pip
# Windows fallback
ifeq ($(OS),Windows_NT)
  PYTHON = $(VENV)/Scripts/python
  PIP    = $(VENV)/Scripts/pip
endif

install:
	python -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	cp -n .env.example .env || true

run:
	$(PYTHON) -m streamlit run app/streamlit_app.py

seed:
	$(PYTHON) scripts/seed_kb.py

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

diagram:
	$(PYTHON) diagrams/generate_architecture.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f data/tickets.db
