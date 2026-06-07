import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo, useRef, useState } from 'react'
import { importDevicesCsv, updateDevice } from '../api/client'
import { DeviceDetailModal } from '../components/inventory/DeviceDetailModal'
import { useDevicesWithStatus } from '../hooks/useDashboardData'
import type { DeviceWithStatus } from '../types/api'

const DEVICE_TYPES = ['hpe_ilorest', 'juniper', 'aruba', 'linux_ssh']
const STATUS_OPTIONS = ['ok', 'warning', 'critical', 'down', 'unknown']

export function InventoryPage() {
  const [search, setSearch] = useState('')
  const [deviceType, setDeviceType] = useState('')
  const [status, setStatus] = useState('')
  const [importantOnly, setImportantOnly] = useState(false)
  const [selected, setSelected] = useState<DeviceWithStatus | null>(null)
  const [importMessage, setImportMessage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const filters = useMemo(
    () => ({
      search: search || undefined,
      device_type: deviceType || undefined,
      status: status || undefined,
      important: importantOnly ? true : undefined,
    }),
    [search, deviceType, status, importantOnly],
  )

  const devices = useDevicesWithStatus(filters)
  const queryClient = useQueryClient()

  const toggleImportant = useMutation({
    mutationFn: ({ id, important_flag }: { id: string; important_flag: boolean }) =>
      updateDevice(id, { important_flag }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
      queryClient.invalidateQueries({ queryKey: ['high-level'] })
    },
  })

  const importCsv = useMutation({
    mutationFn: importDevicesCsv,
    onSuccess: (result) => {
      setImportMessage(`Imported ${result.imported} device(s).`)
      queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
    },
    onError: (err) =>
      setImportMessage(err instanceof Error ? err.message : 'Import failed'),
  })

  return (
    <section className="page">
      <div className="page-header inventory-header">
        <div>
          <h2>Inventory</h2>
          <p>{devices.data?.length ?? 0} devices shown (of 67 total)</p>
        </div>
        <div className="dashboard-actions">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) importCsv.mutate(file)
              e.target.value = ''
            }}
          />
          <button
            type="button"
            className="inline-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={importCsv.isPending}
          >
            {importCsv.isPending ? 'Importing…' : 'Import CSV'}
          </button>
        </div>
      </div>

      {importMessage && <p className="settings-hint">{importMessage}</p>}

      <div className="inventory-filters card">
        <input
          type="search"
          placeholder="Search name or hostname"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search devices"
        />
        <select value={deviceType} onChange={(e) => setDeviceType(e.target.value)} aria-label="Filter by type">
          <option value="">All types</option>
          {DEVICE_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={importantOnly}
            onChange={(e) => setImportantOnly(e.target.checked)}
          />
          Important only
        </label>
      </div>

      <div className="inventory-table-wrap card">
        {devices.isLoading && <p>Loading inventory...</p>}
        {devices.isError && <p className="widget-error">Failed to load devices.</p>}
        {devices.data && (
          <table className="inventory-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Connector</th>
                <th>Important</th>
                <th>Last Update</th>
              </tr>
            </thead>
            <tbody>
              {devices.data.map((device) => (
                <tr key={device.id} onClick={() => setSelected(device)} className="clickable-row">
                  <td>{device.name}</td>
                  <td>{device.device_type}</td>
                  <td>
                    <span className={`status-pill status-${device.status?.overall ?? 'unknown'}`}>
                      {device.status?.overall ?? 'unknown'}
                    </span>
                  </td>
                  <td>
                    <span className="connector-pill">
                      {device.connector_enabled ? 'on' : 'off'}
                      {device.credentials_configured ? ' · creds' : ''}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="inline-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleImportant.mutate({
                          id: device.id,
                          important_flag: !device.important_flag,
                        })
                      }}
                    >
                      {device.important_flag ? '★' : '☆'}
                    </button>
                  </td>
                  <td>
                    {device.status ? new Date(device.status.timestamp).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <DeviceDetailModal
          device={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </section>
  )
}