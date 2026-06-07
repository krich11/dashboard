import { useQuery } from '@tanstack/react-query'
import { getOperationalHistory } from '../../../api/client'

interface Props {
  config?: {
    title?: string
    hours?: number
    refreshIntervalSec?: number
  }
}

const overallColor: Record<string, string> = {
  ok: '#3fb950',
  warning: '#d29922',
  degraded: '#d29922',
  critical: '#f85149',
  down: '#f85149',
  unknown: '#8aa0c8',
}

export function DeviceHealthTrend({ config }: Props) {
  const title = config?.title ?? 'Device Health Trend'
  const hours = config?.hours ?? 24
  const refreshMs = (config?.refreshIntervalSec ?? 60) * 1000

  const { data, isLoading, isError } = useQuery({
    queryKey: ['operational-history', hours],
    queryFn: () => getOperationalHistory(hours),
    refetchInterval: refreshMs,
  })

  const points = data ?? []
  const width = 320
  const height = 80
  const barWidth = points.length > 0 ? width / points.length : width

  return (
    <article className="widget widget-trend" data-testid="widget-device-health-trend">
      <header className="widget-header">
        <h3>{title}</h3>
        <span className="widget-timestamp">{hours}h · important devices</span>
      </header>

      {isLoading && <p className="widget-muted">Loading device history…</p>}
      {isError && <p className="widget-error">Failed to load device history.</p>}

      {points.length === 0 && !isLoading && !isError && (
        <p className="widget-muted">No device history yet. Polls will populate this chart.</p>
      )}

      {points.length > 0 && (
        <div className="trend-body">
          <svg viewBox={`0 0 ${width} ${height}`} className="trend-chart" role="img" aria-label="Device health trend">
            {points.map((point, index) => (
              <rect
                key={`${point.timestamp}-${index}`}
                x={index * barWidth}
                y={0}
                width={Math.max(barWidth - 1, 1)}
                height={height}
                fill={overallColor[point.worst_overall] ?? overallColor.unknown}
                opacity={0.85}
              />
            ))}
          </svg>
          <p className="widget-muted">
            Latest: {points[points.length - 1].important_up}/{points[points.length - 1].important_total} up
            {' · '}
            worst {points[points.length - 1].worst_overall}
          </p>
        </div>
      )}
    </article>
  )
}