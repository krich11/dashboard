import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as client from '../../../api/client'
import { renderWithQuery } from '../../../test/test-utils'
import { InternetReachability } from './index'

describe('InternetReachability', () => {
  it('renders ipv4 and ipv6 status', async () => {
    vi.spyOn(client, 'getReachabilityLatest').mockResolvedValue({
      ipv4_ok: true,
      ipv6_ok: false,
      ipv4_targets: [{ target: '1.1.1.1', ok: true, latency_ms: 10, error: null }],
      ipv6_targets: [{ target: '2606:4700:4700::1111', ok: false, latency_ms: null, error: 'timeout' }],
      overall: 'degraded',
      timestamp: new Date().toISOString(),
    })

    renderWithQuery(<InternetReachability />)

    await waitFor(() => {
      expect(screen.getByTestId('widget-internet')).toBeInTheDocument()
      expect(screen.getByText('Overall: degraded')).toBeInTheDocument()
      expect(screen.getByText('1.1.1.1 — OK (10ms)')).toBeInTheDocument()
    })
  })
})