import { useQuery } from '@tanstack/react-query'
import { getHealth, getHighLevelStatus, getReachabilityLatest } from '../api/client'
import { widgetRegistry } from '../components/widgets/registry'

export function OverviewPage() {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth })
  const highLevel = useQuery({ queryKey: ['high-level'], queryFn: getHighLevelStatus })
  const reachability = useQuery({ queryKey: ['reachability'], queryFn: getReachabilityLatest })

  return (
    <section className="page">
      <div className="page-header">
        <h2>Overview</h2>
        <p>Phase 0 shell — priority widgets land in Phase 2.</p>
      </div>

      <div className="status-grid">
        <article className="card">
          <h3>System Health</h3>
          {highLevel.isLoading && <p>Loading...</p>}
          {highLevel.data && (
            <>
              <p className={`banner banner-${highLevel.data.banner}`}>{highLevel.data.banner_text}</p>
              <p>
                Important: {highLevel.data.important_up}/{highLevel.data.important_total} up
              </p>
              <p>{highLevel.data.internet_summary}</p>
            </>
          )}
        </article>

        <article className="card">
          <h3>Internet Reachability</h3>
          {reachability.isLoading && <p>Loading...</p>}
          {reachability.data && (
            <>
              <p>IPv4: {reachability.data.ipv4_ok ? 'OK' : 'Down'}</p>
              <p>IPv6: {reachability.data.ipv6_ok ? 'OK' : 'Degraded'}</p>
              <p>Overall: {reachability.data.overall}</p>
            </>
          )}
        </article>

        <article className="card">
          <h3>Runtime</h3>
          {health.data && (
            <>
              <p>API: {health.data.status}</p>
              <p>Mock mode: {String(health.data.mock_mode)}</p>
              <p>Scenario: {health.data.mock_scenario}</p>
            </>
          )}
        </article>
      </div>

      <article className="card">
        <h3>Widget Registry</h3>
        <ul className="registry-list">
          {widgetRegistry.map((widget) => (
            <li key={widget.type}>
              <strong>{widget.title}</strong> ({widget.priority}) — {widget.dataSource}
            </li>
          ))}
        </ul>
      </article>
    </section>
  )
}