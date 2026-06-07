
# Datacenter Status Dashboard Specification (Refined v1.1)
**Version**: 1.1 (Tailored to 67 devices + Up/Down + IPv4/IPv6 Reachability priorities)  
**Target Builder**: Grok Build (grok-build-0.1) – **Start in Plan Mode**  
**Date**: 2026-06-07  
**Context**: ~67 devices (7 HPE ESXi hosts via iLO Redfish, 10 Juniper, 20 Aruba, 30 Linux). High-level curated rollup focused on **Up/Down overall status** of important devices + **IPv4 + IPv6 internet reachability**. Modular widgets + JSON dashboard configs for future LLM-driven customization. Native Linux deploy only (no Docker). `requirements.txt` packaging.

## 1. Executive Summary & v1 Success Criteria
- **High-level status (priority)**: Big, clear **Up/Down Overall widget** showing aggregate health of user-flagged “important” devices + **Internet Reachability (IPv4 + IPv6)** as a first-class signal. Overall banner: “All Clear”, “N Devices Down”, “Internet Degraded”, etc.
- **Full visibility**: Searchable/filterable inventory of all ~67 nodes with lighter detail (status + key metrics + last update). Click for detail.
- **Modular widgets (flexible for LLM future)**: Small, well-defined registry of high-value widgets. Each is a self-contained React component + JSON config schema. Drag-drop, resizable, multi-instance, savable per dashboard. Easy to extend later by LLM outputting valid JSON or new widget defs.
- **Key v1 widgets to build first** (high-value):
  1. **UpDownOverallStatus** – Prominent visual (big status, counts or %, breakdown by type or status, last refresh). Uses important devices + internet reachability.
  2. **InternetReachability** – Shows IPv4 + IPv6 status (OK/Degraded/Down), last check times, target results, configurable targets.
  3. **ImportantDevicesStatusGrid** – Cards or compact rows for important subset only.
  4. **IssuesList** – Current non-OK items from important or filtered devices.
  5. **InventoryTable** – Full or filtered searchable table (less granular view).
- **Dashboards**: Multiple named ones. Layout + widget configs saved as JSON. Export/import for LLM future (“describe what I want” → JSON → import).
- **Data collection**: Smart background collector using vendor-native libraries. Normalized status. External reachability checker runs independently.
- **Non-goals (v1)**: Long-term metrics trends (simple optional history table only), alerting, write actions, auto topology, discovery, multi-user RBAC.

**Success for unattended Grok Build**: Phased plan with mocks, explicit “implement UpDownOverall + InternetReachability early”, `requirements.txt`, systemd deploy example, and clear checkpoint after each phase.

## 2. Assumptions (Confirmed by your answers)
- **Scale**: 7 HPE ESXi hosts (use iLO Redfish for hardware health, power state, thermal, fans, PSU – excellent “up” proxy for the server itself; basic connectivity/SSH for hypervisor layer if needed), 10 Juniper, 20 Aruba, 30 Linux. Total ~67. Single collector process easily handles this with 60–120 s default interval + concurrency limit 8–10.
- **AquaInferno**: No current details or integration required.
- **Frontend**: Flexible + modular for future LLM customization → React 18 + TypeScript + component/widget registry is the right choice (easy dynamic registration or future JSON-described widgets).
- **Packaging**: `requirements.txt` + venv for backend (classic open-source Python approach). npm for frontend.
- **HPE ESXi hosts**: Redfish is primary and high-value (hardware + chassis status). “Up” can combine successful Redfish poll + optional ping/SSH reachability.
- **Internet reachability (IPv4 + IPv6)**: Dedicated lightweight monitor (not tied to inventory devices). Configurable targets. Feeds high-level rollup and its own widget.
- **Auth/Deploy**: Single-user or small trusted team. Native Linux (Ubuntu 24.04 / Rocky 9+). You can add TLS/reverse proxy later.

## 3. Architecture (Updated for Priorities)
```
[Frontend React SPA]
  - UpDownOverallStatus widget (priority)
  - InternetReachability widget (priority)
  - Other modular widgets + drag-drop composer
  - Inventory browser + detail modals
        ↓ REST (+ optional SSE)
[FastAPI + Pydantic]
  - High-level aggregation (important devices up/down + internet reachability)
  - Device & status CRUD
  - Dashboard/widget JSON import/export (LLM-ready)
        ↓
[SQLite]
  - devices + latest_status + dashboards + widget_instances + external_reachability_results (optional simple history)
        ↑
[Collector Service (APScheduler)]
  - Device connectors (HPE ilorest, Juniper PyEZ, Aruba REST, Linux SSH)
  - ExternalReachabilityMonitor (independent, asyncio + httpx/icmplib or subprocess ping)
        ↑
[Devices + Public Internet Targets]
```

**Normalized Status**: `overall`, `message`, `metrics` (cpu/mem/temp/power where available, connectivity), `details`, `timestamp`.

**High-level rollup logic (simple & reliable)**: 
- Important devices = those with `important_flag=True`.
- Up/Down aggregate: count successful recent polls + overall != critical/unknown.
- Internet: combine v4 + v6 results (user-configurable “both required” or “either OK”).
- Overall banner driven by worst of (important devices health, internet health).

## 4. Tech Stack (Confirmed)
**Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 + SQLite, APScheduler, `python-ilorest-library`, `junos-eznc`, `pyaoscx` or `requests`, `paramiko`, `cryptography` (Fernet), `httpx` (for reachability), `icmplib` or subprocess for ping. Packaged with `requirements.txt`.

**Frontend**: React 18 + TypeScript + Vite + Tailwind + shadcn/ui + lucide-react + `react-grid-layout` (drag/resize) + `recharts` (simple trends stub) + `zod` + React Query/SWR. Widget system = registry of TSX components + config schemas (perfect for future LLM).

**Native deploy only**: `uvicorn` + systemd unit for backend. `npm run build` → static files served by FastAPI `StaticFiles` (single port) or simple nginx/caddy. No Docker.

## 5. High-Value Widgets (Build These First – Especially #1 & #2)
1. **UpDownOverallStatus** (highest priority)  
   - Big visual status (color + icon + text: “All Systems Operational”, “3 Important Devices Down”, etc.).  
   - Counts or % of important devices up.  
   - Breakdown (by type or status).  
   - Includes internet reachability summary line.  
   - Config: title, which important set or tags, refresh interval.  
   - Feeds directly from high-level aggregation API.

2. **InternetReachability** (high priority)  
   - Clear IPv4 status + IPv6 status (OK / Degraded / Down).  
   - Last successful check times.  
   - Per-target results (if multiple).  
   - Overall “Internet Health” indicator.  
   - Config: list of IPv4 targets (IPs or hostnames), IPv6 targets, check method (ping or HTTP GET to reliable public endpoint), interval, “require both families” flag.  
   - Runs via dedicated `ExternalReachabilityMonitor` (independent of device inventory – always-on, lightweight).

3. **ImportantDevicesStatusGrid** – Compact cards or rows for the important subset only (name, status, key metrics, last update). Click opens detail.

4. **IssuesList** – Current warnings/criticals/errors from important or filtered devices. Actionable list.

5. **InventoryTable** – Full ~67 node view (search, filter by status/type/tag/important, sortable). Less granular columns. “Add to Important” toggle.

All widgets: self-contained, accept `config` prop (JSON validated), pull data via shared hooks/queries, support edit-mode configuration forms.

**Dashboard Composer**: Edit mode toggle → visual grid (react-grid-layout) → palette (add any registered widget) → drag/resize/snap → click widget → config modal (dynamic from schema) → save full layout + configs as JSON.

## 6. ExternalReachabilityMonitor (New – High Value, Low Complexity)
- Independent background task (not per-device).  
- Configurable in Settings: IPv4 targets, IPv6 targets, interval (default 60s), timeout, method (ping preferred for true reachability or HTTP fallback).  
- Stores latest results (v4_ok, v6_ok, details per target, timestamp).  
- Exposed via dedicated API endpoints and used by UpDownOverallStatus + InternetReachability widget.  
- Simple & reliable implementation: `asyncio` + `httpx` (HTTP) or `icmplib` / subprocess `ping` (cross-platform).  
- No dependency on inventory devices.

## 7. Phased Implementation Plan for Grok Build
**Step 1 (you do this)**: Paste this entire spec into Grok Build TUI.  
**Command**: “Review this full specification. Output a detailed execution plan with exact folder structure, key file outlines, and checkpoints after each phase. Pay special attention to implementing UpDownOverallStatus and InternetReachability widgets early.”

Then follow the phases below. Commit after each phase. Pause for my review or say “continue”.

**Phase 0: Project Setup**  
- Git repo, `requirements.txt` (backend), `package.json` (frontend).  
- Exact folder structure (backend/app/ with collectors/, models/, routers/, services/; frontend/src/components/widgets/ with registry).  
- FastAPI skeleton + SQLite models (Device, LatestStatus, Dashboard, WidgetInstance, ExternalReachabilityResult).  
- Frontend Vite + Tailwind + shadcn + widget registry skeleton.  
- Mock mode + fake data generator (critical for early progress without real devices).  
- Full README with setup/run/deploy commands (venv, pip install -r requirements.txt, uvicorn, npm run build, systemd example).

**Phase 1: Backend Core + Connectors + Collector + High-Level + Reachability (Core Value)**  
- Device CRUD + `important_flag` + tags + CSV import.  
- Connectors: HPE (python-ilorest-library – hardware health, power, thermal – note ESXi hosts), Juniper (junos-eznc), Aruba, Linux (paramiko basic up + load/mem/disk).  
- Status normalization + simple up/down rules.  
- APScheduler collector with concurrency limit, per-device intervals, backoff, error isolation.  
- **ExternalReachabilityMonitor** implemented early (config-driven targets, results storage).  
- High-level aggregation API (important devices up/down + internet health).  
- Basic auth/encryption for creds (Fernet + env master key).  
- Mocks + unit tests.

**Phase 2: Frontend Inventory + High-Level View + First Two Priority Widgets**  
- Inventory page (table + filters + detail modal).  
- High-level overview page/view featuring **UpDownOverallStatus** widget prominently + **InternetReachability** widget.  
- Implement the two priority widgets fully (big visual status, config forms, data binding).  
- Basic dashboard CRUD + simple layout persistence.  
- Global refresh controls.

**Phase 3: Full Modular Widget System + Drag/Drop + Remaining Widgets + JSON Import/Export**  
- Complete widget registry + drag-drop composer (react-grid-layout).  
- Add ImportantDevicesStatusGrid, IssuesList, InventoryTable as widgets.  
- Edit mode, dynamic config modals from schemas, multi-dashboard support.  
- Full JSON export/import for dashboards (LLM-ready).  
- Polish (loading states, error handling, responsive desktop focus).

**Phase 4: Polish, Deploy, LLM Hooks, Documentation**  
- Settings UI (collector config, reachability targets, encryption key setup wizard).  
- Optional simple history table + one basic trend in a widget.  
- LLM foundation: documented JSON schemas, `/dashboards/import` endpoint, widget `description_for_llm` fields.  
- Production README + systemd unit example + backup guidance.  
- In-app help or docs.

## 8. Security & Operational Notes (Same Hardened Approach)
- Creds encrypted at rest (Fernet). Master key via env var or protected file.  
- Least-privilege device users recommended.  
- Collector runs on trusted host with mgmt network access.  
- Timeouts, concurrency limits, error isolation prevent overload on your ~67 devices.  
- External reachability uses public targets you control (no scanning).

## 9. How to Use with Grok Build (Exact Instructions)
1. Copy this entire markdown into Grok Build.
2. Start with the Plan Mode command above.
3. Review the plan it outputs.
4. Then: “Now execute Phase 0 completely. After that, pause.”
5. After my review/“continue”, proceed phase by phase.
6. Grok Build strengths leveraged: long-horizon planning, parallel subagents if useful, native code output, Git handling, testing.




