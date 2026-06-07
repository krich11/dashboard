# LLM Integration Guide

Datacenter Dashboard dashboards are JSON-first so an LLM can author, modify, and import layouts without touching the UI.

## Workflow

1. **Discover widgets** — `GET /api/v1/widgets/catalog` returns each widget type with `description_for_llm`, data source, and priority.
2. **Study a working example** — `examples/dashboard-default.json` in the repository.
3. **Validate against schemas** — `backend/schemas/json/dashboard.json` and `widget-instance.json`.
4. **Import** — `POST /api/v1/dashboards/import` with body:

```json
{
  "dashboard": { "...": "DashboardExport payload" },
  "set_as_default": false
}
```

Widget instance `id` fields in exports are ignored on import; new UUIDs are assigned automatically.

## Dashboard export shape

```json
{
  "export_version": "1.0",
  "name": "NOC Overview",
  "description": "Optional description",
  "layout": { "cols": 12, "rowHeight": 30 },
  "widgets": [
    {
      "widget_type": "UpDownOverallStatus",
      "title": "Overall Status",
      "config": { "title": "Datacenter Status", "showBreakdown": true },
      "grid_x": 0,
      "grid_y": 0,
      "grid_w": 12,
      "grid_h": 4
    }
  ]
}
```

## Widget catalog (summary)

| Type | Purpose |
|------|---------|
| `UpDownOverallStatus` | Banner with important device up/down + internet summary |
| `InternetReachability` | IPv4/IPv6 target health |
| `InternetHealthTrend` | Reachability history sparkline |
| `ImportantDevicesStatusGrid` | Grid of flagged devices |
| `IssuesList` | Active warnings and critical items |
| `InventoryTable` | Compact inventory slice |
| `CollectorStatus` | Collector scheduler health and backoff stats |
| `SystemInfo` | App version, mode, and device totals |
| `DeviceHealthTrend` | Important device up/down trend from status history |

Each widget's `config` object is described in the catalog `description_for_llm` field.

## Tips for LLM authors

- Use a 12-column grid; typical row height is 30px in the composer.
- Place `UpDownOverallStatus` at the top for operator visibility.
- Pair `InternetReachability` with `InternetHealthTrend` for current + historical context.
- Set `importantOnly: true` on `IssuesList` for executive views.
- Export an existing dashboard from the UI to learn valid `grid_*` sizing.

## Related API endpoints

- `GET /api/v1/dashboards` — list dashboards
- `GET /api/v1/dashboards/{id}/export` — export one dashboard
- `POST /api/v1/dashboards/import` — create from JSON
- `GET /api/v1/status/high-level` — data for UpDownOverallStatus
- `GET /api/v1/reachability/history` — data for InternetHealthTrend