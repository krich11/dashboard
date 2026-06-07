import { useHighLevelStatus } from '../../hooks/useDashboardData'

export function OperationalBanner() {
  const { data } = useHighLevelStatus(30_000)
  if (!data) return null

  return (
    <div className={`operational-banner banner-${data.banner}`} role="status">
      <span className="operational-banner-text">{data.banner_text}</span>
      <span className="operational-banner-meta">
        {data.important_up}/{data.important_total} up · {data.internet_health}
      </span>
    </div>
  )
}