import { useQuery } from '@tanstack/react-query'
import { getCollectorStatus } from '../../../api/client'

interface Props {
  config?: {
    title?: string
    refreshIntervalSec?: number
  }
}

export function CollectorStatus({ config }: Props) {
  const title = config?.title ?? 'Collector Status'
  const refreshMs = (config?.refreshIntervalSec ?? 15) * 1000

  const { data, isLoading, isError } = useQuery({
    queryKey: ['collector-status'],
    queryFn: getCollectorStatus,
    refetchInterval: refreshMs,
  })

  return (
    <article className="widget widget-collector" data-testid="widget-collector-status">
      <header className="widget-header">
        <h3>{title}</h3>
        <span className={`status-pill status-${data?.running ? 'ok' : 'down'}`}>
          {data?.running ? 'running' : 'stopped'}
        </span>
      </header>

      {isLoading && <p className="widget-muted">Loading collector status…</p>}
      {isError && <p className="widget-error">Failed to load collector status.</p>}

      {data && (
        <dl className="collector-stats">
          <div>
            <dt>Devices</dt>
            <dd>{data.total_devices}</dd>
          </div>
          <div>
            <dt>Pollable</dt>
            <dd>{data.connector_enabled_devices}</dd>
          </div>
          <div>
            <dt>Circuits open</dt>
            <dd>{data.circuits_open}</dd>
          </div>
          <div>
            <dt>In backoff</dt>
            <dd>{data.devices_in_backoff}</dd>
          </div>
          <div>
            <dt>Mode</dt>
            <dd>{data.mock_mode ? 'mock' : 'production'}</dd>
          </div>
        </dl>
      )}
    </article>
  )
}