import { useQuery } from '@tanstack/react-query'
import { getIssues } from '../../../api/client'
import { REFRESH_INTERVAL_MS } from '../../../hooks/useDashboardData'

interface Props {
  config?: { title?: string; importantOnly?: boolean }
}

export function IssuesList({ config }: Props) {
  const title = config?.title ?? 'Current Issues'
  const importantOnly = config?.importantOnly ?? false
  const { data, isLoading, isError } = useQuery({
    queryKey: ['issues', importantOnly],
    queryFn: () => getIssues(importantOnly),
    refetchInterval: REFRESH_INTERVAL_MS,
  })

  return (
    <article className="widget" data-testid="widget-issues">
      <header className="widget-header">
        <h3>{title}</h3>
      </header>
      {isLoading && <p className="widget-muted">Loading issues...</p>}
      {isError && <p className="widget-error">Failed to load issues</p>}
      {data && data.length === 0 && <p className="widget-muted">No issues — all clear.</p>}
      {data && data.length > 0 && (
        <ul className="issues-list">
          {data.map((issue) => (
            <li key={issue.device_id}>
              <strong>{issue.device_name}</strong>
              <span className={`status-pill status-${issue.overall}`}>{issue.overall}</span>
              <span>{issue.message}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}