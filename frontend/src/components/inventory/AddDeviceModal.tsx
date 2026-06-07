import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { createDevice } from '../../api/client'

const DEVICE_TYPES = ['hpe_ilorest', 'juniper', 'aruba', 'linux_ssh']

interface Props {
  onClose: () => void
}

export function AddDeviceModal({ onClose }: Props) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [hostname, setHostname] = useState('')
  const [deviceType, setDeviceType] = useState('linux_ssh')
  const [managementIp, setManagementIp] = useState('')
  const [connectorEnabled, setConnectorEnabled] = useState(false)
  const [importantFlag, setImportantFlag] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: () =>
      createDevice({
        name: name.trim(),
        hostname: hostname.trim(),
        device_type: deviceType,
        management_ip: managementIp.trim() || null,
        connector_enabled: connectorEnabled,
        important_flag: importantFlag,
        username: username || undefined,
        password: password || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
      onClose()
    },
    onError: (err) => setError(err instanceof Error ? err.message : 'Failed to create device'),
  })

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal card device-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <h3>Add Device</h3>
        <form
          className="settings-form"
          onSubmit={(e) => {
            e.preventDefault()
            if (!name.trim() || !hostname.trim()) {
              setError('Name and hostname are required.')
              return
            }
            setError(null)
            save.mutate()
          }}
        >
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Hostname
            <input value={hostname} onChange={(e) => setHostname(e.target.value)} required />
          </label>
          <label>
            Management IP
            <input value={managementIp} onChange={(e) => setManagementIp(e.target.value)} />
          </label>
          <label>
            Device type
            <select value={deviceType} onChange={(e) => setDeviceType(e.target.value)}>
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
              checked={connectorEnabled}
              onChange={(e) => setConnectorEnabled(e.target.checked)}
            />
            Enable connector polling
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={importantFlag}
              onChange={(e) => setImportantFlag(e.target.checked)}
            />
            Important device
          </label>
          <fieldset className="credentials-fieldset">
            <legend>Credentials (optional)</legend>
            <label>
              Username
              <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" />
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
          </fieldset>
          {error && <p className="widget-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="inline-btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="inline-btn primary" disabled={save.isPending}>
              {save.isPending ? 'Creating…' : 'Create device'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}