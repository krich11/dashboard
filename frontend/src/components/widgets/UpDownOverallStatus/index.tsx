import { Activity, AlertTriangle, CheckCircle2, Globe2 } from 'lucide-react'
import { useHighLevelStatus } from '../../../hooks/useDashboardData'
import { defaultUpDownConfig, type UpDownConfig } from './config.schema'

interface Props {
  config?: Partial<UpDownConfig>
}

const bannerIcon = {
  all_clear: CheckCircle2,
  devices_down: AlertTriangle,
  internet_degraded: Globe2,
  mixed: AlertTriangle,
} as const

export function UpDownOverallStatus({ config }: Props) {
  const merged = { ...defaultUpDownConfig, ...config }
  const { data, isLoading, isError, error } = useHighLevelStatus(merged.refreshIntervalSec * 1000)
  const Icon = data ? bannerIcon[data.banner] : Activity

  return (
    <article className="widget widget-updown" data-testid="widget-updown">
      <header className="widget-header">
        <h3>{merged.title}</h3>
        {data && <span className="widget-timestamp">Updated {new Date(data.timestamp).toLocaleTimeString()}</span>}
      </header>

      {isLoading && <p className="widget-muted">Loading status...</p>}
      {isError && <p className="widget-error">{error instanceof Error ? error.message : 'Failed to load'}</p>}

      {data && (
        <div className="updown-body">
          <div className={`updown-banner banner-${data.banner}`}>
            <Icon size={28} aria-hidden />
            <span>{data.banner_text}</span>
          </div>

          {merged.showBreakdown && (
            <div className="updown-stats">
              <div>
                <span className="stat-label">Important Up</span>
                <strong>
                  {data.important_up}/{data.important_total}
                </strong>
              </div>
              <div>
                <span className="stat-label">Important Down</span>
                <strong className={data.important_down > 0 ? 'text-danger' : ''}>{data.important_down}</strong>
              </div>
              <div>
                <span className="stat-label">Internet</span>
                <strong className={`health-${data.internet_health}`}>{data.internet_health}</strong>
              </div>
            </div>
          )}

          <p className="internet-summary">{data.internet_summary}</p>
        </div>
      )}
    </article>
  )
}