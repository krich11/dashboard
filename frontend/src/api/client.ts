import type {
  BulkDeviceUpdate,
  AlertSettings,
  AlertTestResult,
  CollectorSettings,
  CollectorRunResult,
  CollectorStatus,
  Dashboard,
  DeviceCreate,
  DashboardExport,
  Device,
  DeviceStatus,
  DeviceStatusHistoryPoint,
  DeviceUpdate,
  DeviceWithStatus,
  OperationalHistoryPoint,
  EncryptionStatus,
  EncryptionTestResult,
  ExternalReachability,
  HighLevelSummary,
  IssueItem,
  ReachabilityHistoryPoint,
  ReachabilitySettings,
  WidgetInstance,
} from '../types/api'

export interface MockScenarioSettings {
  scenario: string
  available: string[]
}

const API_BASE = ''

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${path}`)
  }
  return response.json() as Promise<T>
}

export function getHighLevelStatus() {
  return fetchJson<HighLevelSummary>('/api/v1/status/high-level')
}

export function getReachabilityLatest() {
  return fetchJson<ExternalReachability>('/api/v1/reachability/latest')
}

export function getDevices(important?: boolean) {
  const query = important === undefined ? '' : `?important=${important}`
  return fetchJson<Device[]>(`/api/v1/devices${query}`)
}

export function getDevicesWithStatus(params?: {
  important?: boolean
  device_type?: string
  status?: string
  search?: string
}) {
  const searchParams = new URLSearchParams()
  if (params?.important !== undefined) searchParams.set('important', String(params.important))
  if (params?.device_type) searchParams.set('device_type', params.device_type)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.search) searchParams.set('search', params.search)
  const query = searchParams.toString()
  return fetchJson<DeviceWithStatus[]>(`/api/v1/devices/with-status${query ? `?${query}` : ''}`)
}

export function createDevice(payload: DeviceCreate) {
  return fetchJson<Device>('/api/v1/devices', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function bulkUpdateDevices(payload: BulkDeviceUpdate) {
  return fetchJson<{ updated: number }>('/api/v1/devices/bulk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function bulkDeleteDevices(deviceIds: string[]) {
  return fetchJson<{ deleted: number }>('/api/v1/devices/bulk-delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_ids: deviceIds }),
  })
}

export function bulkPollDevices(deviceIds: string[]) {
  return fetchJson<{ polled: number; results: DeviceStatus[] }>('/api/v1/devices/bulk-poll', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_ids: deviceIds }),
  })
}

export function deleteDevice(deviceId: string) {
  return fetch(`${API_BASE}/api/v1/devices/${deviceId}`, { method: 'DELETE' }).then((response) => {
    if (!response.ok) {
      throw new Error(`API error ${response.status}: /api/v1/devices/${deviceId}`)
    }
  })
}

export async function downloadDevicesExport() {
  const response = await fetch('/api/v1/devices/export')
  if (!response.ok) {
    throw new Error(`API error ${response.status}: /api/v1/devices/export`)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'devices-export.csv'
  link.click()
  URL.revokeObjectURL(url)
}

export function updateDevice(deviceId: string, payload: DeviceUpdate) {
  return fetchJson<Device>(`/api/v1/devices/${deviceId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function pollDevice(deviceId: string) {
  return fetchJson<DeviceStatus>(`/api/v1/devices/${deviceId}/poll`, {
    method: 'POST',
  })
}

export async function importDevicesCsv(file: File) {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch('/api/v1/devices/import', { method: 'POST', body: form })
  if (!response.ok) {
    throw new Error(`API error ${response.status}: /api/v1/devices/import`)
  }
  return response.json() as Promise<{ imported: number }>
}

export function getDefaultDashboard() {
  return fetchJson<Dashboard>('/api/v1/dashboards/default')
}

export function listDashboards() {
  return fetchJson<Dashboard[]>('/api/v1/dashboards')
}

export function getDashboard(id: string) {
  return fetchJson<Dashboard>(`/api/v1/dashboards/${id}`)
}

export function createDashboard(payload: {
  name: string
  description?: string
  layout?: Record<string, unknown>
  is_default?: boolean
  widgets?: Omit<WidgetInstance, 'id' | 'dashboard_id'>[]
}) {
  return fetchJson<Dashboard>('/api/v1/dashboards', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function updateDashboard(
  id: string,
  payload: {
    name?: string
    description?: string
    layout?: Record<string, unknown>
    is_default?: boolean
    widgets?: WidgetInstance[]
  },
) {
  return fetchJson<Dashboard>(`/api/v1/dashboards/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function deleteDashboard(id: string) {
  return fetch(`${API_BASE}/api/v1/dashboards/${id}`, { method: 'DELETE' })
}

export function exportDashboard(id: string) {
  return fetchJson<DashboardExport>(`/api/v1/dashboards/${id}/export`)
}

export function importDashboard(dashboard: DashboardExport, setAsDefault = false) {
  return fetchJson<Dashboard>('/api/v1/dashboards/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dashboard, set_as_default: setAsDefault }),
  })
}

export function getIssues(importantOnly = false) {
  const q = importantOnly ? '?important=true' : ''
  return fetchJson<IssueItem[]>(`/api/v1/status/issues${q}`)
}

export function getHealth() {
  return fetchJson<{ status: string; mock_mode: boolean; mock_scenario: string }>('/health')
}

export interface SystemInfo {
  app: string
  version: string
  mock_mode: boolean
  mock_scenario: string | null
  collector_running: boolean
  total_devices: number
  docs_url: string
  openapi_url: string
}

export function getSystemInfo() {
  return fetchJson<SystemInfo>('/api/v1/system/info')
}

export function getOperationalHistory(hours = 24) {
  return fetchJson<OperationalHistoryPoint[]>(
    `/api/v1/status/history?hours=${hours}&limit=200`,
  )
}

export function getDeviceStatusHistory(deviceId: string, hours = 24) {
  return fetchJson<DeviceStatusHistoryPoint[]>(
    `/api/v1/devices/${deviceId}/status/history?hours=${hours}&limit=200`,
  )
}

export function getReachabilitySettings() {
  return fetchJson<ReachabilitySettings>('/api/v1/settings/reachability')
}

export function updateReachabilitySettings(payload: ReachabilitySettings) {
  return fetchJson<ReachabilitySettings>('/api/v1/settings/reachability', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function getCollectorSettings() {
  return fetchJson<CollectorSettings>('/api/v1/settings/collector')
}

export function getCollectorStatus() {
  return fetchJson<CollectorStatus>('/api/v1/settings/collector/status')
}

export function runCollectorOnce() {
  return fetchJson<CollectorRunResult>('/api/v1/settings/collector/run', { method: 'POST' })
}

export function getAlertSettings() {
  return fetchJson<AlertSettings>('/api/v1/settings/alerts')
}

export function updateAlertSettings(payload: AlertSettings) {
  return fetchJson<AlertSettings>('/api/v1/settings/alerts', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function testAlertWebhook() {
  return fetchJson<AlertTestResult>('/api/v1/settings/alerts/test', { method: 'POST' })
}

export function getMockScenario() {
  return fetchJson<MockScenarioSettings>('/api/v1/settings/mock-scenario')
}

export function updateMockScenario(scenario: string) {
  return fetchJson<MockScenarioSettings>('/api/v1/settings/mock-scenario', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario }),
  })
}

export function updateCollectorSettings(payload: CollectorSettings) {
  return fetchJson<CollectorSettings>('/api/v1/settings/collector', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function getEncryptionStatus() {
  return fetchJson<EncryptionStatus>('/api/v1/settings/encryption')
}

export function testEncryption(testValue: string) {
  return fetchJson<EncryptionTestResult>('/api/v1/settings/encryption/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ test_value: testValue }),
  })
}

export function getReachabilityHistory(hours = 24) {
  return fetchJson<ReachabilityHistoryPoint[]>(
    `/api/v1/reachability/history?hours=${hours}&limit=100`,
  )
}