.PHONY: dev backend frontend test build seed-mocks smoke-test install backup ci reset-phase install-systemd

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
NPM ?= npm
BACKEND_DIR = backend
FRONTEND_DIR = frontend
export PYTHONPATH = $(BACKEND_DIR)

install:
	chmod +x scripts/install.sh scripts/smoke_test.sh scripts/dev.sh
	./scripts/install.sh

dev:
	./scripts/dev.sh

backend:
	cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app.main:app --reload --host $${BIND_HOST:-0.0.0.0} --port 8000

frontend:
	cd $(FRONTEND_DIR) && $(NPM) run dev

test:
	cd $(BACKEND_DIR) && TESTING=true $(PYTHON) -m pytest -q
	cd $(FRONTEND_DIR) && $(NPM) run test

ci:
	chmod +x scripts/ci.sh
	./scripts/ci.sh

build:
	cd $(FRONTEND_DIR) && $(NPM) run build

seed-mocks:
	$(PYTHON) scripts/seed_mocks.py

smoke-test:
	chmod +x scripts/smoke_test.sh
	./scripts/smoke_test.sh

backup:
	chmod +x scripts/backup.sh
	./scripts/backup.sh

reset-phase:
	chmod +x scripts/reset_phase.sh
	./scripts/reset_phase.sh

install-systemd:
	chmod +x scripts/setup-systemd.sh
	@echo "Run: sudo ./scripts/setup-systemd.sh --install-dir $$(pwd) --user $$(whoami)"