import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as client from '../../../api/client'
import { renderWithQuery } from '../../../test/test-utils'
import { InternetHealthTrend } from './index'

describe('InternetHealthTrend', () => {
  it('renders trend bars from history', async () => {
    vi.spyOn(client, 'getReachabilityHistory').mockResolvedValue([
      { timestamp: '2026-06-07T12:00:00Z', overall: 'ok', ipv4_ok: true, ipv6_ok: true },
      { timestamp: '2026-06-07T12:01:00Z', overall: 'degraded', ipv4_ok: true, ipv6_ok: false },
    ])

    renderWithQuery(<InternetHealthTrend />)

    await waitFor(() => {
      expect(screen.getByTestId('widget-trend')).toBeInTheDocument()
      expect(screen.getByText(/Latest: degraded/i)).toBeInTheDocument()
    })
  })
})