import { useQuery } from '@tanstack/react-query'
import { getReachabilityHistory } from '../../../api/client'

interface Props {
  config?: {
    title?: string
    hours?: number
    refreshIntervalSec?: number
  }
}

const overallColor: Record<string, string> = {
  ok: '#3fb950',
  degraded: '#d29922',
  down: '#f85149',
  unknown: '#8aa0c8',
}

export function InternetHealthTrend({ config }: Props) {
  const title = config?.title ?? 'Internet Health Trend'
  const hours = config?.hours ?? 24
  const refreshMs = (config?.refreshIntervalSec ?? 60) * 1000

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['reachability-history', hours],
    queryFn: () => getReachabilityHistory(hours),
    refetchInterval: refreshMs,
  })

  const points = data ?? []
  const width = 320
  const height = 80
  const barWidth = points.length > 0 ? width / points.length : width

  return (
    <article className="widget widget-trend" data-testid="widget-trend">
      <header className="widget-header">
        <h3>{title}</h3>
        <span className="widget-timestamp">{hours}h window</span>
      </header>

      {isLoading && <p className="widget-muted">Loading history…</p>}
      {isError && (
        <p className="widget-error">{error instanceof Error ? error.message : 'Failed to load'}</p>
      )}

      {points.length === 0 && !isLoading && !isError && (
        <p className="widget-muted">No history data yet.</p>
      )}

      {points.length > 0 && (
        <div className="trend-body">
          <svg viewBox={`0 0 ${width} ${height}`} className="trend-chart" role="img" aria-label="Internet health trend">
            {points.map((point, index) => (
              <rect
                key={`${point.timestamp}-${index}`}
                x={index * barWidth}
                y={0}
                width={Math.max(barWidth - 1, 1)}
                height={height}
                fill={overallColor[point.overall] ?? overallColor.unknown}
                opacity={0.85}
              />
            ))}
          </svg>
          <div className="trend-legend">
            <span><i className="dot ok" /> ok</span>
            <span><i className="dot degraded" /> degraded</span>
            <span><i className="dot down" /> down</span>
          </div>
          <p className="widget-muted">
            Latest: {points[points.length - 1].overall} at{' '}
            {new Date(points[points.length - 1].timestamp).toLocaleString()}
          </p>
        </div>
      )}
    </article>
  )
}