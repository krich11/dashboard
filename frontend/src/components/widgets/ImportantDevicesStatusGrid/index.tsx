import { useDevicesWithStatus } from '../../../hooks/useDashboardData'

interface Props {
  config?: { title?: string; maxItems?: number }
}

export function ImportantDevicesStatusGrid({ config }: Props) {
  const title = config?.title ?? 'Important Devices'
  const maxItems = config?.maxItems ?? 12
  const { data, isLoading, isError } = useDevicesWithStatus({ important: true })

  return (
    <article className="widget" data-testid="widget-important-grid">
      <header className="widget-header">
        <h3>{title}</h3>
      </header>
      {isLoading && <p className="widget-muted">Loading...</p>}
      {isError && <p className="widget-error">Failed to load devices</p>}
      {data && (
        <div className="device-card-grid">
          {data.slice(0, maxItems).map((device) => (
            <div key={device.id} className="device-card">
              <strong>{device.name}</strong>
              <span className={`status-pill status-${device.status?.overall ?? 'unknown'}`}>
                {device.status?.overall ?? 'unknown'}
              </span>
              <span className="widget-muted">{device.device_type}</span>
            </div>
          ))}
        </div>
      )}
    </article>
  )
}