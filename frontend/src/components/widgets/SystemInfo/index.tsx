import { useQuery } from '@tanstack/react-query'
import { getSystemInfo } from '../../../api/client'

interface Props {
  config?: {
    title?: string
    refreshIntervalSec?: number
  }
}

export function SystemInfo({ config }: Props) {
  const title = config?.title ?? 'System Info'
  const refreshMs = (config?.refreshIntervalSec ?? 30) * 1000

  const { data, isLoading, isError } = useQuery({
    queryKey: ['system-info'],
    queryFn: getSystemInfo,
    refetchInterval: refreshMs,
  })

  return (
    <article className="widget widget-system-info" data-testid="widget-system-info">
      <header className="widget-header">
        <h3>{title}</h3>
        {data && <span className="widget-timestamp">v{data.version}</span>}
      </header>

      {isLoading && <p className="widget-muted">Loading system info…</p>}
      {isError && <p className="widget-error">Failed to load system info.</p>}

      {data && (
        <dl className="collector-stats">
          <div>
            <dt>Application</dt>
            <dd>{data.app}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>{data.version}</dd>
          </div>
          <div>
            <dt>Mode</dt>
            <dd>{data.mock_mode ? `mock · ${data.mock_scenario ?? 'default'}` : 'production'}</dd>
          </div>
          <div>
            <dt>Collector</dt>
            <dd>{data.collector_running ? 'running' : 'stopped'}</dd>
          </div>
          <div>
            <dt>Devices</dt>
            <dd>{data.total_devices}</dd>
          </div>
          <div>
            <dt>History tiers</dt>
            <dd>
              raw {data.history_raw_days}d → hourly {data.history_hourly_days}d → daily ∞
            </dd>
          </div>
        </dl>
      )}
    </article>
  )
}