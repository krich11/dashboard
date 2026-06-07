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