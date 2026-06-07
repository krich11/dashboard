import { useQuery } from '@tanstack/react-query'
import {
  getDefaultDashboard,
  getDevicesWithStatus,
  getHighLevelStatus,
  getReachabilityLatest,
} from '../api/client'

export const REFRESH_INTERVAL_MS = 30_000

export function useHighLevelStatus(refetchInterval = REFRESH_INTERVAL_MS) {
  return useQuery({
    queryKey: ['high-level'],
    queryFn: getHighLevelStatus,
    refetchInterval,
  })
}

export function useReachability(refetchInterval = REFRESH_INTERVAL_MS) {
  return useQuery({
    queryKey: ['reachability'],
    queryFn: getReachabilityLatest,
    refetchInterval,
  })
}

export function useDevicesWithStatus(filters?: {
  important?: boolean
  device_type?: string
  status?: string
  search?: string
}) {
  return useQuery({
    queryKey: ['devices-with-status', filters],
    queryFn: () => getDevicesWithStatus(filters),
    refetchInterval: REFRESH_INTERVAL_MS,
  })
}

export function useDefaultDashboard() {
  return useQuery({
    queryKey: ['dashboard-default'],
    queryFn: getDefaultDashboard,
  })
}