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

## API endpoints (Phase 1)

- `GET /api/v1/status/high-level` — computed from DB
- `GET /api/v1/status/issues`
- `GET /api/v1/reachability/latest`
- `GET/PUT /api/v1/settings/reachability`
- `GET/POST/PUT/DELETE /api/v1/devices`
- `POST /api/v1/devices/import` (CSV)

Mock scenarios (`all_clear`, `devices_down`, `internet_degraded`, `mixed`) drive `MockConnector` via `MOCK_SCENARIO` env var.