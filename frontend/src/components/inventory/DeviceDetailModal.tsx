import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { deleteDevice, getDeviceStatusHistory, pollDevice, updateDevice } from '../../api/client'
import type { DeviceUpdate, DeviceWithStatus } from '../../types/api'

const DEVICE_TYPES = ['hpe_ilorest', 'juniper', 'aruba', 'linux_ssh']

interface Props {
  device: DeviceWithStatus
  onClose: () => void
}

export function DeviceDetailModal({ device, onClose }: Props) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<DeviceUpdate>({
    name: device.name,
    hostname: device.hostname,
    device_type: device.device_type,
    management_ip: device.management_ip,
    connector_enabled: device.connector_enabled,
    important_flag: device.important_flag,
  })
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [pollMessage, setPollMessage] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  useEffect(() => {
    setForm({
      name: device.name,
      hostname: device.hostname,
      device_type: device.device_type,
      management_ip: device.management_ip,
      connector_enabled: device.connector_enabled,
      important_flag: device.important_flag,
    })
    setUsername('')
    setPassword('')
    setPollMessage(null)
  }, [device])

  const save = useMutation({
    mutationFn: () =>
      updateDevice(device.id, {
        ...form,
        username: username || undefined,
        password: password || undefined,
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
      queryClient.invalidateQueries({ queryKey: ['high-level'] })
      setUsername('')
      setPassword('')
      setForm((prev) => ({
        ...prev,
        connector_enabled: updated.connector_enabled,
      }))
      setPollMessage('Device saved.')
    },
  })

  const remove = useMutation({
    mutationFn: () => deleteDevice(device.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
      queryClient.invalidateQueries({ queryKey: ['high-level'] })
      onClose()
    },
    onError: (err) =>
      setPollMessage(err instanceof Error ? err.message : 'Delete failed'),
  })

  const history = useQuery({
    queryKey: ['device-status-history', device.id],
    queryFn: () => getDeviceStatusHistory(device.id, 24),
  })

  const poll = useMutation({
    mutationFn: () => pollDevice(device.id),
    onSuccess: (status) => {
      queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
      queryClient.invalidateQueries({ queryKey: ['high-level'] })
      queryClient.invalidateQueries({ queryKey: ['device-status-history', device.id] })
      queryClient.invalidateQueries({ queryKey: ['operational-history'] })
      setPollMessage(`Poll OK: ${status.overall} — ${status.message}`)
    },
    onError: (err) =>
      setPollMessage(err instanceof Error ? err.message : 'Poll failed'),
  })

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal card device-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <h3>{device.name}</h3>

        <form
          className="settings-form"
          onSubmit={(e) => {
            e.preventDefault()
            save.mutate()
          }}
        >
          <label>
            Name
            <input
              value={form.name ?? ''}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            Hostname
            <input
              value={form.hostname ?? ''}
              onChange={(e) => setForm({ ...form, hostname: e.target.value })}
            />
          </label>
          <label>
            Management IP
            <input
              value={form.management_ip ?? ''}
              onChange={(e) => setForm({ ...form, management_ip: e.target.value || null })}
            />
          </label>
          <label>
            Device type
            <select
              value={form.device_type ?? 'linux_ssh'}
              onChange={(e) => setForm({ ...form, device_type: e.target.value })}
            >
              {DEVICE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={form.connector_enabled ?? false}
              onChange={(e) => setForm({ ...form, connector_enabled: e.target.checked })}
            />
            Enable connector polling
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={form.important_flag ?? false}
              onChange={(e) => setForm({ ...form, important_flag: e.target.checked })}
            />
            Important device
          </label>

          <fieldset className="credentials-fieldset">
            <legend>Credentials</legend>
            <p className="settings-hint">
              {device.credentials_configured
                ? 'Credentials are configured. Leave blank to keep existing values.'
                : 'No credentials stored yet.'}
            </p>
            <label>
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="off"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
              />
            </label>
            {device.credentials_configured && (
              <button
                type="button"
                className="inline-btn danger"
                onClick={() => {
                  updateDevice(device.id, { clear_credentials: true }).then(() => {
                    queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
                    setPollMessage('Credentials cleared.')
                  })
                }}
              >
                Clear stored credentials
              </button>
            )}
          </fieldset>

          {device.status && (
            <div className="device-status-panel">
              <p>
                <strong>Current status:</strong> {device.status.overall} — {device.status.message}
              </p>
              {Object.keys(device.status.metrics).length > 0 && (
                <pre className="metrics-block">
                  {JSON.stringify(device.status.metrics, null, 2)}
                </pre>
              )}
            </div>
          )}

          {history.data && history.data.length > 0 && (
            <div className="device-history-panel">
              <h4>Status history (24h)</h4>
              <ul className="history-list">
                {[...history.data].reverse().slice(0, 8).map((point) => (
                  <li key={`${point.timestamp}-${point.source}`}>
                    <span className={`status-pill status-${point.overall}`}>{point.overall}</span>
                    <span>{point.message}</span>
                    <span className="widget-muted">
                      {new Date(point.timestamp).toLocaleString()} · {point.source}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {pollMessage && <p className="settings-hint">{pollMessage}</p>}

          <div className="modal-actions">
            {!confirmDelete ? (
              <button
                type="button"
                className="inline-btn danger"
                onClick={() => setConfirmDelete(true)}
              >
                Delete
              </button>
            ) : (
              <>
                <span className="settings-hint">Delete {device.name}?</span>
                <button
                  type="button"
                  className="inline-btn danger"
                  onClick={() => remove.mutate()}
                  disabled={remove.isPending}
                >
                  {remove.isPending ? 'Deleting…' : 'Confirm delete'}
                </button>
                <button
                  type="button"
                  className="inline-btn"
                  onClick={() => setConfirmDelete(false)}
                >
                  Cancel
                </button>
              </>
            )}
            <button
              type="button"
              className="inline-btn"
              onClick={() => poll.mutate()}
              disabled={poll.isPending}
            >
              {poll.isPending ? 'Polling…' : 'Poll now'}
            </button>
            <button type="button" className="inline-btn" onClick={onClose}>
              Close
            </button>
            <button type="submit" className="inline-btn primary" disabled={save.isPending}>
              {save.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}