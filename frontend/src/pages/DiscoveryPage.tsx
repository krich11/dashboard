import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { importDiscovery, scanDiscovery } from '../api/client'
import type { DiscoveryCandidate } from '../types/api'

const DEVICE_TYPES = ['', 'hpe_ilorest', 'juniper', 'aruba', 'linux_ssh']

export function DiscoveryPage() {
  const [targetsText, setTargetsText] = useState('10.0.0.10\n10.0.0.11')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [deviceTypeHint, setDeviceTypeHint] = useState('')
  const [candidates, setCandidates] = useState<DiscoveryCandidate[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const scan = useMutation({
    mutationFn: () =>
      scanDiscovery({
        targets: targetsText
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean),
        username: username || undefined,
        password: password || undefined,
        device_type_hint: deviceTypeHint || undefined,
      }),
    onSuccess: (result) => {
      setCandidates(result.candidates)
      setMessage(`Scanned ${result.scanned} target(s).`)
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : 'Discovery scan failed'),
  })

  const importSelected = useMutation({
    mutationFn: () =>
      importDiscovery({
        candidates: candidates.filter((c) => c.reachable && c.detected_type),
        enable_connectors: Boolean(username && password),
        import_credentials: Boolean(username && password),
        username: username || undefined,
        password: password || undefined,
      }),
    onSuccess: (result) => {
      setMessage(`Imported ${result.imported}, skipped ${result.skipped}.`)
      queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : 'Import failed'),
  })

  return (
    <section className="page">
      <div className="page-header">
        <h2>Discovery</h2>
        <p>
          Probe IPs or CIDR ranges, detect connector types, test credentials, and import into
          inventory. Set <code>MOCK_MODE=false</code> for live network probes.
        </p>
      </div>

      <div className="settings-grid">
        <article className="card settings-card">
          <h3>Scan targets</h3>
          <form
            className="settings-form"
            onSubmit={(e) => {
              e.preventDefault()
              scan.mutate()
            }}
          >
            <label>
              Targets (one IP, hostname, or CIDR per line)
              <textarea
                rows={6}
                value={targetsText}
                onChange={(e) => setTargetsText(e.target.value)}
              />
            </label>
            <label>
              Device type hint (optional)
              <select
                value={deviceTypeHint}
                onChange={(e) => setDeviceTypeHint(e.target.value)}
              >
                {DEVICE_TYPES.map((t) => (
                  <option key={t || 'auto'} value={t}>
                    {t || 'Auto-detect'}
                  </option>
                ))}
              </select>
            </label>
            <fieldset className="credentials-fieldset">
              <legend>Credentials (optional — enables login probe + import)</legend>
              <label>
                Username
                <input value={username} onChange={(e) => setUsername(e.target.value)} />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
            </fieldset>
            <button type="submit" className="inline-btn primary" disabled={scan.isPending}>
              {scan.isPending ? 'Scanning…' : 'Run discovery scan'}
            </button>
          </form>
          {message && <p className="settings-hint">{message}</p>}
        </article>

        <article className="card settings-card">
          <div className="page-header inventory-header">
            <h3>Results</h3>
            {candidates.length > 0 && (
              <button
                type="button"
                className="inline-btn primary"
                onClick={() => importSelected.mutate()}
                disabled={importSelected.isPending}
              >
                {importSelected.isPending ? 'Importing…' : 'Import reachable'}
              </button>
            )}
          </div>
          {candidates.length === 0 && <p className="widget-muted">No scan results yet.</p>}
          {candidates.length > 0 && (
            <table className="inventory-table">
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Type</th>
                  <th>Creds</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((row) => (
                  <tr key={row.target}>
                    <td>{row.target}</td>
                    <td>{row.detected_type ?? '—'}</td>
                    <td>
                      {row.credentials_ok === null
                        ? '—'
                        : row.credentials_ok
                          ? 'ok'
                          : 'fail'}
                    </td>
                    <td>{row.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </article>
      </div>
    </section>
  )
}