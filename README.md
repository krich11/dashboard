# Datacenter Dashboard

Native-Linux datacenter status dashboard for ~67 devices with modular JSON-driven widgets.

## Quick start (Phase 0)

```bash
# Mock fixtures (67 devices)
python3 scripts/seed_mocks.py

# Backend API (requires Python deps — see below)
export MOCK_MODE=true
export PYTHONPATH=backend
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (requires Node 22+ via nvm)
cd frontend && npm install && npm run dev
```

Or run both:

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

## Python dependencies

```bash
python3 -m pip install --user --break-system-packages -r backend/requirements.txt
```

## API (mock mode)

- `GET /health`
- `GET /api/v1/status/high-level`
- `GET /api/v1/reachability/latest`
- `GET /api/v1/devices`

Mock scenarios: `?scenario=all_clear|devices_down|internet_degraded|mixed`

## Project docs

- [`PROJECT_SPEC_FINAL.md`](PROJECT_SPEC_FINAL.md)
- [`AGENT_ROLES_FINAL.md`](AGENT_ROLES_FINAL.md)
- [`docs/CONTRACTS.md`](docs/CONTRACTS.md)

## Layout

```
backend/     FastAPI + SQLAlchemy
frontend/    React + TypeScript + Vite
mocks/       Generated fixture data
scripts/     dev.sh, seed_mocks.py
deploy/      systemd unit (Phase 4)
```