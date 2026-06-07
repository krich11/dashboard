import type { Device, ExternalReachability, HighLevelSummary } from '../types/api'

const API_BASE = ''

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
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

export function getHealth() {
  return fetchJson<{ status: string; mock_mode: boolean; mock_scenario: string }>('/health')
}