.PHONY: dev backend frontend test build seed-mocks

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
NPM ?= npm
BACKEND_DIR = backend
FRONTEND_DIR = frontend
export PYTHONPATH = $(BACKEND_DIR)

dev:
	./scripts/dev.sh

backend:
	cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd $(FRONTEND_DIR) && $(NPM) run dev

test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest -q
	cd $(FRONTEND_DIR) && $(NPM) run test

build:
	cd $(FRONTEND_DIR) && $(NPM) run build

seed-mocks:
	$(PYTHON) scripts/seed_mocks.py