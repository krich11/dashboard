import { useDevicesWithStatus } from '../../../hooks/useDashboardData'

interface Props {
  config?: { title?: string; maxRows?: number }
}

export function InventoryTableWidget({ config }: Props) {
  const title = config?.title ?? 'Inventory'
  const maxRows = config?.maxRows ?? 10
  const { data, isLoading, isError } = useDevicesWithStatus()

  return (
    <article className="widget" data-testid="widget-inventory-table">
      <header className="widget-header">
        <h3>{title}</h3>
      </header>
      {isLoading && <p className="widget-muted">Loading inventory...</p>}
      {isError && <p className="widget-error">Failed to load inventory</p>}
      {data && (
        <table className="inventory-table compact">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.slice(0, maxRows).map((device) => (
              <tr key={device.id}>
                <td>{device.name}</td>
                <td>{device.device_type}</td>
                <td>
                  <span className={`status-pill status-${device.status?.overall ?? 'unknown'}`}>
                    {device.status?.overall ?? 'unknown'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </article>
  )
}