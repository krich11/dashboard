import type { ComponentType } from 'react'
import { InternetReachability } from './InternetReachability'
import { UpDownOverallStatus } from './UpDownOverallStatus'

export type WidgetType =
  | 'UpDownOverallStatus'
  | 'InternetReachability'
  | 'ImportantDevicesStatusGrid'
  | 'IssuesList'
  | 'InventoryTable'

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
      'Large operational banner showing important device up/down counts and internet health summary.',
    priority: 'P0',
    dataSource: '/api/v1/status/high-level',
    component: UpDownOverallStatus,
  },
  {
    type: 'InternetReachability',
    title: 'Internet Reachability',
    description_for_llm:
      'Shows IPv4 and IPv6 reachability status with per-target results and last check times.',
    priority: 'P0',
    dataSource: '/api/v1/reachability/latest',
    component: InternetReachability,
  },
  {
    type: 'ImportantDevicesStatusGrid',
    title: 'Important Devices Grid',
    description_for_llm: 'Compact grid of important devices with status and key metrics.',
    priority: 'P1',
    dataSource: '/api/v1/devices?important=true',
  },
  {
    type: 'IssuesList',
    title: 'Issues List',
    description_for_llm: 'List of current warnings and critical issues from monitored devices.',
    priority: 'P1',
    dataSource: '/api/v1/status/issues',
  },
  {
    type: 'InventoryTable',
    title: 'Inventory Table',
    description_for_llm: 'Searchable full inventory table of all monitored devices.',
    priority: 'P1',
    dataSource: '/api/v1/devices',
  },
]

export function getWidgetComponent(type: string) {
  return widgetRegistry.find((w) => w.type === type)?.component
}