import type { ComponentType } from 'react'
import { CollectorStatus } from './CollectorStatus'
import { DeviceHealthTrend } from './DeviceHealthTrend'
import { ImportantDevicesStatusGrid } from './ImportantDevicesStatusGrid'
import { InternetHealthTrend } from './InternetHealthTrend'
import { InternetReachability } from './InternetReachability'
import { InventoryTableWidget } from './InventoryTable'
import { IssuesList } from './IssuesList'
import { SystemInfo } from './SystemInfo'
import { UpDownOverallStatus } from './UpDownOverallStatus'

export type WidgetType =
  | 'UpDownOverallStatus'
  | 'InternetReachability'
  | 'InternetHealthTrend'
  | 'ImportantDevicesStatusGrid'
  | 'IssuesList'
  | 'InventoryTable'
  | 'CollectorStatus'
  | 'SystemInfo'
  | 'DeviceHealthTrend'

export interface WidgetDefinition {
  type: WidgetType
  title: string
  description_for_llm: string
  priority: 'P0' | 'P1'
  dataSource: string
  component?: ComponentType<{ config?: Record<string, unknown> }>
}

export const widgetRegistry: WidgetDefinition[] = [
  {
    type: 'UpDownOverallStatus',
    title: 'Up/Down Overall Status',
    description_for_llm:
      'Large operational banner showing important device up/down counts and internet health summary. Config: title (string), showBreakdown (bool), refreshIntervalSec (number).',
    priority: 'P0',
    dataSource: '/api/v1/status/high-level',
    component: UpDownOverallStatus,
  },
  {
    type: 'InternetReachability',
    title: 'Internet Reachability',
    description_for_llm:
      'Shows IPv4 and IPv6 reachability status with per-target results. Config: title, showTargets (bool), refreshIntervalSec (number).',
    priority: 'P0',
    dataSource: '/api/v1/reachability/latest',
    component: InternetReachability,
  },
  {
    type: 'InternetHealthTrend',
    title: 'Internet Health Trend',
    description_for_llm:
      'Sparkline of internet reachability over time. Config: title, hours (number, default 24), refreshIntervalSec (number).',
    priority: 'P1',
    dataSource: '/api/v1/reachability/history',
    component: InternetHealthTrend,
  },
  {
    type: 'ImportantDevicesStatusGrid',
    title: 'Important Devices Grid',
    description_for_llm:
      'Compact grid of important devices with status. Config: title, maxItems (number).',
    priority: 'P1',
    dataSource: '/api/v1/devices?important=true',
    component: ImportantDevicesStatusGrid,
  },
  {
    type: 'IssuesList',
    title: 'Issues List',
    description_for_llm:
      'List of current warnings and critical issues. Config: title, importantOnly (bool).',
    priority: 'P1',
    dataSource: '/api/v1/status/issues',
    component: IssuesList,
  },
  {
    type: 'InventoryTable',
    title: 'Inventory Table',
    description_for_llm:
      'Compact searchable inventory table widget. Config: title, maxRows (number).',
    priority: 'P1',
    dataSource: '/api/v1/devices/with-status',
    component: InventoryTableWidget,
  },
  {
    type: 'CollectorStatus',
    title: 'Collector Status',
    description_for_llm:
      'Collector scheduler health: running, device counts, circuits, backoff. Config: title, refreshIntervalSec.',
    priority: 'P1',
    dataSource: '/api/v1/settings/collector/status',
    component: CollectorStatus,
  },
  {
    type: 'SystemInfo',
    title: 'System Info',
    description_for_llm:
      'App version, mock mode, collector state, device totals. Config: title, refreshIntervalSec.',
    priority: 'P1',
    dataSource: '/api/v1/system/info',
    component: SystemInfo,
  },
  {
    type: 'DeviceHealthTrend',
    title: 'Device Health Trend',
    description_for_llm:
      'Important device up/down trend from status history. Config: title, hours, refreshIntervalSec.',
    priority: 'P1',
    dataSource: '/api/v1/status/history',
    component: DeviceHealthTrend,
  },
]

export function getWidgetComponent(type: string) {
  return widgetRegistry.find((w) => w.type === type)?.component
}