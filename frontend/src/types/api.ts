export type BannerType = 'all_clear' | 'devices_down' | 'internet_degraded' | 'mixed'
export type HealthType = 'ok' | 'degraded' | 'down' | 'warning' | 'critical' | 'unknown'

export interface HighLevelSummary {
  banner: BannerType
  banner_text: string
  important_total: number
  important_up: number
  important_down: number
  internet_health: HealthType
  internet_summary: string
  worst_overall: HealthType
  timestamp: string
}

export interface ReachabilityTargetResult {
  target: string
  ok: boolean
  latency_ms: number | null
  error: string | null
}

export interface ExternalReachability {
  ipv4_ok: boolean
  ipv6_ok: boolean
  ipv4_targets: ReachabilityTargetResult[]
  ipv6_targets: ReachabilityTargetResult[]
  overall: string
  timestamp: string
}

export interface DeviceStatus {
  device_id: string
  overall: string
  message: string
  metrics: Record<string, unknown>
  details: Record<string, unknown>
  timestamp: string
}

export interface Device {
  id: string
  name: string
  hostname: string
  device_type: string
  tags: string[]
  important_flag: boolean
  management_ip: string | null
  connector_enabled: boolean
}

export interface DeviceWithStatus extends Device {
  status: DeviceStatus | null
}

export interface WidgetInstance {
  id: string
  dashboard_id: string
  widget_type: string
  title: string
  config: Record<string, unknown>
  grid_x: number
  grid_y: number
  grid_w: number
  grid_h: number
}

export interface IssueItem {
  device_id: string
  device_name: string
  device_type: string
  overall: string
  message: string
  important_flag: boolean
  timestamp: string
}

export interface DashboardExport {
  export_version: string
  name: string
  description: string | null
  layout: Record<string, unknown>
  widgets: Omit<WidgetInstance, 'dashboard_id'>[]
}

export interface Dashboard {
  id: string
  name: string
  description: string | null
  layout: Record<string, unknown>
  is_default: boolean
  created_at: string
  updated_at: string
  widgets: WidgetInstance[]
}