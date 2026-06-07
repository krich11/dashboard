import type {
  Dashboard,
  Device,
  DeviceWithStatus,
  ExternalReachability,
  HighLevelSummary,
} from '../types/api'

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

export function updateDevice(deviceId: string, payload: Partial<Device>) {
  return fetchJson<Device>(`/api/v1/devices/${deviceId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function getDefaultDashboard() {
  return fetchJson<Dashboard>('/api/v1/dashboards/default')
}

export function getHealth() {
  return fetchJson<{ status: string; mock_mode: boolean; mock_scenario: string }>('/health')
}