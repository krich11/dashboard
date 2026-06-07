import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getDevices, getDiscoveryPrefixes, importDiscovery, scanDiscovery } from '../api/client'
import type { DiscoveryCandidate } from '../types/api'

const DEVICE_TYPES = ['', 'hpe_ilorest', 'juniper', 'aruba', 'linux_ssh']
const INFRA_TYPES = new Set(['juniper', 'aruba', 'linux_ssh'])

export function DiscoveryPage() {
  const [targetsText, setTargetsText] = useState('')
  const [useDefaultRanges, setUseDefaultRanges] = useState(true)
  const [includeArpMac, setIncludeArpMac] = useState(true)
  const [infrastructureIds, setInfrastructureIds] = useState<string[]>([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [deviceTypeHint, setDeviceTypeHint] = useState('')
  const [candidates, setCandidates] = useState<DiscoveryCandidate[]>([])
  const [scanMeta, setScanMeta] = useState<{
    prefixes: string[]
    l2_neighbors_found: number
    infrastructure_sources: string[]
  } | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const prefixes = useQuery({
    queryKey: ['discovery-prefixes'],
    queryFn: getDiscoveryPrefixes,
  })

  const devices = useQuery({
    queryKey: ['devices-total'],
    queryFn: () => getDevices(),
  })

  const infraDevices = (devices.data ?? []).filter((d) => INFRA_TYPES.has(d.device_type))

  const scan = useMutation({
    mutationFn: () =>
      scanDiscovery({
        targets: targetsText
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean),
        use_default_ranges: useDefaultRanges,
        infrastructure_device_ids: infrastructureIds,
        include_arp_mac: includeArpMac,
        username: username || undefined,
        password: password || undefined,
        device_type_hint: deviceTypeHint || undefined,
      }),
    onSuccess: (result) => {
      setCandidates(result.candidates)
      setScanMeta({
        prefixes: result.scan_prefixes,
        l2_neighbors_found: result.l2_neighbors_found,
        infrastructure_sources: result.infrastructure_sources,
      })
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

  const toggleInfra = (deviceId: string) => {
    setInfrastructureIds((prev) =>
      prev.includes(deviceId) ? prev.filter((id) => id !== deviceId) : [...prev, deviceId],
    )
  }

  return (
    <section className="page">
      <div className="page-header">
        <h2>Discovery</h2>
        <p>
          Fingerprint hosts via ping, ports, banners, and credential probes. Pull ARP/MAC tables
          from routers and switches. Default scope is RFC1918 routes plus delegated IPv6 (/56→/64).
          Set <code>MOCK_MODE=false</code> for live network probes.
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
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={useDefaultRanges}
                onChange={(e) => setUseDefaultRanges(e.target.checked)}
              />
              Use default ranges (RFC1918 + delegated IPv6 from routing table)
            </label>
            {prefixes.data && prefixes.data.prefixes.length > 0 && (
              <p className="settings-hint">
                Detected prefixes: {prefixes.data.prefixes.join(', ')}
              </p>
            )}
            <label>
              Additional targets (optional — one IP, hostname, or CIDR per line)
              <textarea
                rows={4}
                value={targetsText}
                onChange={(e) => setTargetsText(e.target.value)}
                placeholder="10.0.0.50&#10;192.168.1.0/28"
              />
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={includeArpMac}
                onChange={(e) => setIncludeArpMac(e.target.checked)}
              />
              Query ARP/MAC tables from infrastructure devices
            </label>
            {infraDevices.length > 0 ? (
              <fieldset className="credentials-fieldset">
                <legend>Infrastructure devices (routers/switches/Linux gateways)</legend>
                {infraDevices.map((device) => (
                  <label key={device.id} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={infrastructureIds.includes(device.id)}
                      onChange={() => toggleInfra(device.id)}
                    />
                    {device.name} ({device.device_type}) — {device.management_ip ?? device.hostname}
                  </label>
                ))}
              </fieldset>
            ) : (
              <p className="settings-hint">
                Add Juniper, Aruba, or Linux SSH devices with credentials to enable L2 table
                discovery.
              </p>
            )}
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
          {scanMeta && (
            <p className="settings-hint">
              Prefixes: {scanMeta.prefixes.join(', ') || '—'} · L2 neighbors:{' '}
              {scanMeta.l2_neighbors_found}
              {scanMeta.infrastructure_sources.length > 0 &&
                ` · Sources: ${scanMeta.infrastructure_sources.join(', ')}`}
            </p>
          )}
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
                  <th>Source</th>
                  <th>Type</th>
                  <th>Methods</th>
                  <th>Creds</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((row) => (
                  <tr key={row.target}>
                    <td>{row.target}</td>
                    <td>{row.discovery_source ?? '—'}</td>
                    <td>{row.detected_type ?? '—'}</td>
                    <td>{row.fingerprint_methods?.join(', ') || '—'}</td>
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