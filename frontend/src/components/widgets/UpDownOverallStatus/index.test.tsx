import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as client from '../../../api/client'
import { renderWithQuery } from '../../../test/test-utils'
import { UpDownOverallStatus } from './index'

describe('UpDownOverallStatus', () => {
  it('renders high-level banner text', async () => {
    vi.spyOn(client, 'getHighLevelStatus').mockResolvedValue({
      banner: 'all_clear',
      banner_text: 'All Systems Operational',
      important_total: 17,
      important_up: 17,
      important_down: 0,
      internet_health: 'ok',
      internet_summary: 'IPv4 OK, IPv6 OK',
      worst_overall: 'ok',
      timestamp: new Date().toISOString(),
    })

    renderWithQuery(<UpDownOverallStatus />)

    await waitFor(() => {
      expect(screen.getByTestId('widget-updown')).toBeInTheDocument()
      expect(screen.getByText('All Systems Operational')).toBeInTheDocument()
      expect(screen.getByText('17/17')).toBeInTheDocument()
    })
  })
})