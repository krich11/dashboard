# Data Contracts

Authoritative API shapes for Datacenter Dashboard. Changes require Lead Architect approval.

## DeviceStatus

```json
{
  "device_id": "uuid",
  "overall": "ok|warning|critical|unknown|down",
  "message": "string",
  "metrics": {},
  "details": {},
  "timestamp": "ISO-8601"
}
```

## ExternalReachabilityResult

```json
{
  "ipv4_ok": true,
  "ipv6_ok": false,
  "ipv4_targets": [],
  "ipv6_targets": [],
  "overall": "ok|degraded|down",
  "timestamp": "ISO-8601"
}
```

## HighLevelSummary

```json
{
  "banner": "all_clear|devices_down|internet_degraded|mixed",
  "banner_text": "string",
  "important_total": 0,
  "important_up": 0,
  "important_down": 0,
  "internet_health": "ok|degraded|down",
  "internet_summary": "string",
  "worst_overall": "ok",
  "timestamp": "ISO-8601"
}
```

## ReachabilityHistoryPoint

```json
{
  "timestamp": "ISO-8601",
  "overall": "ok|degraded|down",
  "ipv4_ok": true,
  "ipv6_ok": false
}
```

## API endpoints

- `GET /api/v1/status/high-level` — computed from DB
- `GET /api/v1/status/issues`
- `GET /api/v1/reachability/latest`
- `GET /api/v1/reachability/history?hours=24&limit=100`
- `GET/PUT /api/v1/settings/reachability`
- `GET/PUT /api/v1/settings/collector`
- `GET /api/v1/settings/encryption`
- `POST /api/v1/settings/encryption/test`
- `GET /api/v1/widgets/catalog`
- `GET/POST/PUT/DELETE /api/v1/dashboards`
- `GET /api/v1/dashboards/{id}/export`
- `POST /api/v1/dashboards/import`
- `GET/POST/PUT/DELETE /api/v1/devices`
- `GET /api/v1/devices/export` — CSV download (import-compatible format)
- `POST /api/v1/devices/import` (CSV)
- `POST /api/v1/devices/bulk` — bulk connector/important updates
- `POST /api/v1/devices/bulk-delete` — bulk device removal
- `POST /api/v1/devices/{id}/poll` — on-demand connector poll
- `GET /api/v1/settings/collector/status` — scheduler health snapshot
- `GET/PUT /api/v1/settings/alerts` — webhook alert configuration
- `GET /metrics` — Prometheus text exposition

Mock scenarios (`all_clear`, `devices_down`, `internet_degraded`, `mixed`) drive `MockConnector` via `MOCK_SCENARIO` env var.

Dashboard JSON schemas: `backend/schemas/json/dashboard.json`, `widget-instance.json`. See `docs/LLM_INTEGRATION.md`.