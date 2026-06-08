# Datacenter Dashboard

Native-Linux datacenter status dashboard for ~67 devices with modular JSON-driven widgets.

**v1.7** — Deep discovery (multi-method fingerprint, ARP/MAC from infra devices, RFC1918 + delegated IPv6 defaults), LAN bind (`0.0.0.0`). Tags: `v1.0.0` … `v1.7.0`.

## Quick start (development)

```bash
# Mock fixtures (67 devices)
python3 scripts/seed_mocks.py

# Backend API
export MOCK_MODE=true
export PYTHONPATH=backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (Node 22+ via nvm)
cd frontend && npm install && npm run dev
```

Or run both (detached — script exits immediately):

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

Reset local DB to baseline mock state:

```bash
make reset-phase
```

Open http://127.0.0.1:5173 (frontend proxies API to :8000).

## Python dependencies

```bash
python3 -m pip install --user --break-system-packages -r backend/requirements.txt
```

## Testing

```bash
cd backend && TESTING=true PYTHONPATH=. python3 -m pytest -q
cd frontend && npm run test && npm run build
make ci           # full local CI (pytest + vitest + build)
make smoke-test   # requires running API on :8000
```

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Purpose |
|----------|---------|
| `MOCK_MODE` | `true` for mock connectors (default in dev) |
| `MOCK_SCENARIO` | `all_clear`, `devices_down`, `internet_degraded`, `mixed` |
| `DASHBOARD_SECRET_KEY` | Fernet key for encrypted device credentials |
| `DATABASE_URL` | SQLite path (default `data/dashboard.db`) |

Collector and reachability tuning can also be changed at runtime via **Settings** in the UI.

## Production deployment

### 1. Build frontend

```bash
cd frontend
npm ci
npm run build
```

Serve `frontend/dist` with nginx or another static file server, proxying `/api` and `/health` to the backend.

### 2. Install backend

```bash
sudo useradd --system --home /opt/dashboard dashboard || true
sudo mkdir -p /opt/dashboard/data
sudo cp -r backend frontend/dist mocks scripts /opt/dashboard/
sudo cp .env /opt/dashboard/.env
sudo chown -R dashboard:dashboard /opt/dashboard
pip install -r /opt/dashboard/backend/requirements.txt
```

Set `MOCK_MODE=false`, a strong `DASHBOARD_SECRET_KEY`, and production `DATABASE_URL` in `/opt/dashboard/.env`.

Enable polling per device by setting `connector_enabled=true` and storing encrypted credentials via the device API. Supported types: `hpe_ilorest` (Redfish/httpx), `juniper` (junos-eznc), `aruba` (REST or ping), `linux_ssh` (paramiko or ping fallback).

**Discovery** (`/discovery`): scan IPs or CIDR ranges, auto-detect connector type, test credentials, import to inventory. **Credential test**: per-device in Inventory detail or `POST /api/v1/devices/{id}/credentials/test`.

When `frontend/dist` exists, the API serves the built SPA on the same port (no separate nginx required for small deployments).

### 3. systemd

Requires root — the installer uses `sudo` internally and runs the app as the **`dashboard`** system user (never root):

```bash
cd frontend && npm ci && npm run build && cd ..
cp .env.example .env   # edit MOCK_MODE, DASHBOARD_SECRET_KEY, etc.
sudo ./scripts/setup-systemd.sh
```

Optional daily SQLite backup timer:

```bash
sudo ./scripts/setup-systemd.sh --backup-timer
```

The script deploys to `/opt/dashboard`, validates filesystem + runtime twice, and installs `/etc/systemd/system/dashboard.service`.

```bash
sudo systemctl status dashboard
sudo journalctl -u dashboard -f
sudo ./scripts/uninstall-systemd.sh   # remove units only; keeps /opt/dashboard
```

### 4. Push updates to production

On the **production server** (no config file needed):

```bash
sudo ./scripts/deploy-production.sh
```

From a **dev machine** to a remote server:

```bash
cp deploy/production.env.example deploy/production.env
# set PRODUCTION_SSH=you@production-host
./scripts/deploy-production.sh
```

Builds `frontend/dist`, rsyncs code, and restarts `dashboard.service`. **Never overwrites**
`/opt/dashboard/.env`, `data/`, `backups/`, or `.venv/`.

### 5. Prometheus + Grafana

```bash
# Add deploy/prometheus.yml to your Prometheus scrape configs
# Import examples/grafana-dashboard.json in Grafana (Dashboards → Import)
```

Webhook alerts support **JSON** or **Slack** payload formats (Settings → Webhook Alerts → Send test alert).

### 4. nginx example (snippet)

```nginx
location / {
    root /opt/dashboard/frontend/dist;
    try_files $uri /index.html;
}
location /api/ {
    proxy_pass http://127.0.0.1:8000;
}
location /health {
    proxy_pass http://127.0.0.1:8000;
}
```

## Backup

Back up the SQLite database regularly:

```bash
make backup
# or
sqlite3 /opt/dashboard/data/dashboard.db ".backup '/var/backups/dashboard-$(date +%F).db'"
```

Also archive `/opt/dashboard/.env` (contains `DASHBOARD_SECRET_KEY`) in a secrets manager. Without the key, encrypted device credentials cannot be decrypted.

Scheduled backups via systemd timer:

```bash
sudo cp deploy/dashboard-backup.{service,timer} /etc/systemd/system/
sudo systemctl enable --now dashboard-backup.timer
```

Keyboard shortcut: **Alt+N** opens NOC mode from anywhere in the app.

## API highlights

- `GET /health`
- `GET /metrics` (Prometheus)
- `GET /noc` (fullscreen NOC UI route)
- `GET /api/v1/status/high-level`
- `GET /api/v1/reachability/latest`
- `GET /api/v1/reachability/history`
- `GET/PUT /api/v1/settings/collector`
- `GET/PUT /api/v1/settings/reachability`
- `GET /api/v1/widgets/catalog`
- `GET/POST/PUT/DELETE /api/v1/dashboards`
- `POST /api/v1/dashboards/import`

Mock scenarios: `?scenario=all_clear|devices_down|internet_degraded|mixed`

## Project docs

- [`PROJECT_SPEC_FINAL.md`](PROJECT_SPEC_FINAL.md)
- [`AGENT_ROLES_FINAL.md`](AGENT_ROLES_FINAL.md)
- [`docs/CONTRACTS.md`](docs/CONTRACTS.md)
- [`docs/LLM_INTEGRATION.md`](docs/LLM_INTEGRATION.md)

## Layout

```
backend/     FastAPI + SQLAlchemy
frontend/    React + TypeScript + Vite
mocks/       Generated fixture data
scripts/     dev.sh, seed_mocks.py
deploy/      systemd unit
docs/        Contracts and LLM integration
examples/    Sample dashboard JSON
```