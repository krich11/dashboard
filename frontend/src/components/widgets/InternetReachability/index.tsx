import { Globe, Wifi, WifiOff } from 'lucide-react'
import { useReachability } from '../../../hooks/useDashboardData'
import {
  defaultInternetReachabilityConfig,
  type InternetReachabilityConfig,
} from './config.schema'

interface Props {
  config?: Partial<InternetReachabilityConfig>
}

function FamilyStatus({ label, ok }: { label: string; ok: boolean }) {
  const Icon = ok ? Wifi : WifiOff
  return (
    <div className={`family-status ${ok ? 'ok' : 'bad'}`}>
      <Icon size={20} aria-hidden />
      <div>
        <span className="stat-label">{label}</span>
        <strong>{ok ? 'OK' : 'Down'}</strong>
      </div>
    </div>
  )
}

export function InternetReachability({ config }: Props) {
  const merged = { ...defaultInternetReachabilityConfig, ...config }
  const { data, isLoading, isError, error } = useReachability(merged.refreshIntervalSec * 1000)

  return (
    <article className="widget widget-internet" data-testid="widget-internet">
      <header className="widget-header">
        <h3>{merged.title}</h3>
        <Globe size={18} aria-hidden />
      </header>

      {isLoading && <p className="widget-muted">Checking reachability...</p>}
      {isError && <p className="widget-error">{error instanceof Error ? error.message : 'Failed to load'}</p>}

      {data && (
        <div className="internet-body">
          <div className="internet-summary-row">
            <FamilyStatus label="IPv4" ok={data.ipv4_ok} />
            <FamilyStatus label="IPv6" ok={data.ipv6_ok} />
            <div className={`overall-pill overall-${data.overall}`}>Overall: {data.overall}</div>
          </div>
          <p className="widget-timestamp">Last check {new Date(data.timestamp).toLocaleString()}</p>

          {merged.showTargets && (
            <div className="target-grid">
              <div>
                <h4>IPv4 Targets</h4>
                <ul>
                  {data.ipv4_targets.map((t) => (
                    <li key={t.target} className={t.ok ? 'target-ok' : 'target-bad'}>
                      {t.target} — {t.ok ? `OK (${t.latency_ms ?? '?'}ms)` : t.error ?? 'failed'}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>IPv6 Targets</h4>
                <ul>
                  {data.ipv6_targets.map((t) => (
                    <li key={t.target} className={t.ok ? 'target-ok' : 'target-bad'}>
                      {t.target} — {t.ok ? `OK (${t.latency_ms ?? '?'}ms)` : t.error ?? 'failed'}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  )
}