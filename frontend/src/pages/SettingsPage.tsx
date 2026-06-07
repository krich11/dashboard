import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import {
  getAlertSettings,
  getCollectorSettings,
  getCollectorStatus,
  getHistorySettings,
  runCollectorOnce,
  getEncryptionStatus,
  getHealth,
  getMockScenario,
  getReachabilitySettings,
  testAlertWebhook,
  testEncryption,
  updateAlertSettings,
  updateCollectorSettings,
  updateHistorySettings,
  updateMockScenario,
  updateReachabilitySettings,
} from '../api/client'
import type {
  AlertSettings,
  CollectorSettings,
  HistorySettings,
  ReachabilitySettings,
} from '../types/api'

function TargetListEditor({
  label,
  values,
  onChange,
}: {
  label: string
  values: string[]
  onChange: (values: string[]) => void
}) {
  const [text, setText] = useState(values.join('\n'))

  useEffect(() => {
    setText(values.join('\n'))
  }, [values])

  return (
    <label>
      {label}
      <textarea
        rows={4}
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          onChange(
            e.target.value
              .split('\n')
              .map((line) => line.trim())
              .filter(Boolean),
          )
        }}
      />
    </label>
  )
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const collector = useQuery({ queryKey: ['settings-collector'], queryFn: getCollectorSettings })
  const history = useQuery({ queryKey: ['settings-history'], queryFn: getHistorySettings })
  const collectorStatus = useQuery({
    queryKey: ['collector-status'],
    queryFn: getCollectorStatus,
    refetchInterval: 15000,
  })
  const reachability = useQuery({
    queryKey: ['settings-reachability'],
    queryFn: getReachabilitySettings,
  })
  const encryption = useQuery({ queryKey: ['settings-encryption'], queryFn: getEncryptionStatus })
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth })
  const mockScenario = useQuery({
    queryKey: ['mock-scenario'],
    queryFn: getMockScenario,
    enabled: health.data?.mock_mode === true,
  })

  const [collectorForm, setCollectorForm] = useState<CollectorSettings | null>(null)
  const [historyForm, setHistoryForm] = useState<HistorySettings | null>(null)
  const [reachabilityForm, setReachabilityForm] = useState<ReachabilitySettings | null>(null)
  const [encryptionMessage, setEncryptionMessage] = useState<string | null>(null)
  const [collectorMessage, setCollectorMessage] = useState<string | null>(null)
  const [historyMessage, setHistoryMessage] = useState<string | null>(null)
  const alerts = useQuery({ queryKey: ['settings-alerts'], queryFn: getAlertSettings })
  const [alertsForm, setAlertsForm] = useState<AlertSettings | null>(null)
  const [alertMessage, setAlertMessage] = useState<string | null>(null)

  useEffect(() => {
    if (collector.data) setCollectorForm(collector.data)
  }, [collector.data])

  useEffect(() => {
    if (history.data) setHistoryForm(history.data)
  }, [history.data])

  useEffect(() => {
    if (reachability.data) setReachabilityForm(reachability.data)
  }, [reachability.data])

  useEffect(() => {
    if (alerts.data) setAlertsForm(alerts.data)
  }, [alerts.data])

  const saveCollector = useMutation({
    mutationFn: updateCollectorSettings,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings-collector'] }),
  })

  const saveHistory = useMutation({
    mutationFn: updateHistorySettings,
    onSuccess: () => {
      setHistoryMessage('History tier settings saved.')
      queryClient.invalidateQueries({ queryKey: ['settings-history'] })
      queryClient.invalidateQueries({ queryKey: ['system-info'] })
    },
    onError: (err) =>
      setHistoryMessage(err instanceof Error ? err.message : 'Failed to save history settings'),
  })

  const saveAlerts = useMutation({
    mutationFn: updateAlertSettings,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings-alerts'] }),
  })

  const runAlertTest = useMutation({
    mutationFn: testAlertWebhook,
    onSuccess: (result) => setAlertMessage(result.message),
    onError: (err) =>
      setAlertMessage(err instanceof Error ? err.message : 'Alert test failed'),
  })

  const saveReachability = useMutation({
    mutationFn: updateReachabilitySettings,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings-reachability'] }),
  })

  const switchScenario = useMutation({
    mutationFn: updateMockScenario,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mock-scenario'] })
      queryClient.invalidateQueries({ queryKey: ['health'] })
      queryClient.invalidateQueries({ queryKey: ['high-level'] })
      queryClient.invalidateQueries({ queryKey: ['reachability'] })
      queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
    },
  })

  const runCollector = useMutation({
    mutationFn: runCollectorOnce,
    onSuccess: (result) => {
      setCollectorMessage(
        `Polled ${result.devices_polled} device(s); reachability ${result.reachability ? 'OK' : 'failed'}.`,
      )
      queryClient.invalidateQueries({ queryKey: ['high-level'] })
      queryClient.invalidateQueries({ queryKey: ['reachability'] })
      queryClient.invalidateQueries({ queryKey: ['devices-with-status'] })
      queryClient.invalidateQueries({ queryKey: ['collector-status'] })
    },
    onError: (err) =>
      setCollectorMessage(err instanceof Error ? err.message : 'Collector run failed'),
  })

  const runEncryptionTest = useMutation({
    mutationFn: () => testEncryption('dashboard-encryption-test'),
    onSuccess: (result) => setEncryptionMessage(result.message),
    onError: (err) =>
      setEncryptionMessage(err instanceof Error ? err.message : 'Encryption test failed'),
  })

  return (
    <section className="page">
      <div className="page-header">
        <h2>Settings</h2>
        <p>Collector, status history, reachability, and credential encryption configuration.</p>
      </div>

      <div className="settings-grid">
        <article className="card settings-card">
          <h3>Collector</h3>
          <p className="settings-hint">Poll interval changes apply after service restart.</p>
          {collectorMessage && <p className="settings-hint">{collectorMessage}</p>}
          {collectorStatus.data && (
            <div className="collector-status-panel">
              <div className="collector-status-grid">
                <div>
                  <span className="stat-label">Scheduler</span>
                  <strong>{collectorStatus.data.running ? 'Running' : 'Stopped'}</strong>
                </div>
                <div>
                  <span className="stat-label">Mode</span>
                  <strong>{collectorStatus.data.mock_mode ? 'Mock' : 'Production'}</strong>
                </div>
                <div>
                  <span className="stat-label">Polling</span>
                  <strong>{collectorStatus.data.connector_enabled_devices}</strong>
                </div>
                <div>
                  <span className="stat-label">Circuits open</span>
                  <strong className={collectorStatus.data.circuits_open > 0 ? 'text-danger' : ''}>
                    {collectorStatus.data.circuits_open}
                  </strong>
                </div>
                <div>
                  <span className="stat-label">In backoff</span>
                  <strong>{collectorStatus.data.devices_in_backoff}</strong>
                </div>
                <div>
                  <span className="stat-label">Total devices</span>
                  <strong>{collectorStatus.data.total_devices}</strong>
                </div>
              </div>
            </div>
          )}
          <button
            type="button"
            className="inline-btn"
            onClick={() => runCollector.mutate()}
            disabled={runCollector.isPending}
          >
            {runCollector.isPending ? 'Running…' : 'Run collector now'}
          </button>
          {collectorForm && (
            <form
              className="settings-form"
              onSubmit={(e) => {
                e.preventDefault()
                saveCollector.mutate(collectorForm)
              }}
            >
              <label>
                Poll interval (sec)
                <input
                  type="number"
                  min={10}
                  max={3600}
                  value={collectorForm.interval_sec}
                  onChange={(e) =>
                    setCollectorForm({ ...collectorForm, interval_sec: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                Concurrency
                <input
                  type="number"
                  min={1}
                  max={64}
                  value={collectorForm.concurrency}
                  onChange={(e) =>
                    setCollectorForm({ ...collectorForm, concurrency: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                Status staleness (sec)
                <input
                  type="number"
                  min={30}
                  max={3600}
                  value={collectorForm.status_staleness_sec}
                  onChange={(e) =>
                    setCollectorForm({
                      ...collectorForm,
                      status_staleness_sec: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label>
                Default backoff (sec)
                <input
                  type="number"
                  min={5}
                  max={600}
                  value={collectorForm.default_backoff_sec}
                  onChange={(e) =>
                    setCollectorForm({
                      ...collectorForm,
                      default_backoff_sec: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label>
                Max backoff (sec)
                <input
                  type="number"
                  min={30}
                  max={3600}
                  value={collectorForm.max_backoff_sec}
                  onChange={(e) =>
                    setCollectorForm({ ...collectorForm, max_backoff_sec: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                Circuit breaker threshold
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={collectorForm.circuit_breaker_threshold}
                  onChange={(e) =>
                    setCollectorForm({
                      ...collectorForm,
                      circuit_breaker_threshold: Number(e.target.value),
                    })
                  }
                />
              </label>
              <button type="submit" className="inline-btn primary" disabled={saveCollector.isPending}>
                {saveCollector.isPending ? 'Saving…' : 'Save collector settings'}
              </button>
            </form>
          )}
        </article>

        <article className="card settings-card">
          <h3>Status history tiers</h3>
          <p className="settings-hint">
            Raw polls are kept for the first threshold, then rolled up to hourly, then daily.
            Daily summaries are kept forever. Env vars set defaults until saved here.
          </p>
          {historyMessage && <p className="settings-hint">{historyMessage}</p>}
          {historyForm && (
            <form
              className="settings-form"
              onSubmit={(e) => {
                e.preventDefault()
                saveHistory.mutate(historyForm)
              }}
            >
              <label>
                Raw retention (days) — summarize to hourly after
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={historyForm.raw_days}
                  onChange={(e) =>
                    setHistoryForm({ ...historyForm, raw_days: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                Hourly retention (days) — summarize to daily after
                <input
                  type="number"
                  min={2}
                  max={3650}
                  value={historyForm.hourly_days}
                  onChange={(e) =>
                    setHistoryForm({ ...historyForm, hourly_days: Number(e.target.value) })
                  }
                />
              </label>
              <p className="settings-hint">
                Current pipeline: raw {historyForm.raw_days}d → hourly until{' '}
                {historyForm.hourly_days}d → daily ∞
              </p>
              <button type="submit" className="inline-btn primary" disabled={saveHistory.isPending}>
                {saveHistory.isPending ? 'Saving…' : 'Save history settings'}
              </button>
            </form>
          )}
        </article>

        <article className="card settings-card">
          <h3>Internet Reachability</h3>
          {reachabilityForm && (
            <form
              className="settings-form"
              onSubmit={(e) => {
                e.preventDefault()
                saveReachability.mutate(reachabilityForm)
              }}
            >
              <TargetListEditor
                label="IPv4 targets (one per line)"
                values={reachabilityForm.ipv4_targets}
                onChange={(ipv4_targets) =>
                  setReachabilityForm({ ...reachabilityForm, ipv4_targets })
                }
              />
              <TargetListEditor
                label="IPv6 targets (one per line)"
                values={reachabilityForm.ipv6_targets}
                onChange={(ipv6_targets) =>
                  setReachabilityForm({ ...reachabilityForm, ipv6_targets })
                }
              />
              <label>
                Interval (sec)
                <input
                  type="number"
                  min={10}
                  max={3600}
                  value={reachabilityForm.interval_sec}
                  onChange={(e) =>
                    setReachabilityForm({
                      ...reachabilityForm,
                      interval_sec: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label>
                Timeout (sec)
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={reachabilityForm.timeout_sec}
                  onChange={(e) =>
                    setReachabilityForm({
                      ...reachabilityForm,
                      timeout_sec: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label>
                Method
                <select
                  value={reachabilityForm.method}
                  onChange={(e) =>
                    setReachabilityForm({
                      ...reachabilityForm,
                      method: e.target.value as ReachabilitySettings['method'],
                    })
                  }
                >
                  <option value="ping">ping</option>
                  <option value="http">http</option>
                </select>
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={reachabilityForm.require_both_families}
                  onChange={(e) =>
                    setReachabilityForm({
                      ...reachabilityForm,
                      require_both_families: e.target.checked,
                    })
                  }
                />
                Require both IPv4 and IPv6 for healthy status
              </label>
              <button
                type="submit"
                className="inline-btn primary"
                disabled={saveReachability.isPending}
              >
                {saveReachability.isPending ? 'Saving…' : 'Save reachability settings'}
              </button>
            </form>
          )}
        </article>

        {alertsForm && (
          <article className="card settings-card">
            <h3>Webhook Alerts</h3>
            <p className="settings-hint">
              POST JSON to your webhook when the operational banner changes (Slack, PagerDuty, custom).
            </p>
            <form
              className="settings-form"
              onSubmit={(e) => {
                e.preventDefault()
                saveAlerts.mutate(alertsForm)
              }}
            >
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={alertsForm.enabled}
                  onChange={(e) => setAlertsForm({ ...alertsForm, enabled: e.target.checked })}
                />
                Enable webhook alerts
              </label>
              <label>
                Webhook URL
                <input
                  type="url"
                  value={alertsForm.webhook_url}
                  onChange={(e) => setAlertsForm({ ...alertsForm, webhook_url: e.target.value })}
                  placeholder="https://hooks.example.com/..."
                />
              </label>
              <label>
                Payload format
                <select
                  value={alertsForm.format}
                  onChange={(e) =>
                    setAlertsForm({
                      ...alertsForm,
                      format: e.target.value as AlertSettings['format'],
                    })
                  }
                >
                  <option value="json">JSON (generic)</option>
                  <option value="slack">Slack (mrkdwn blocks)</option>
                  <option value="pagerduty">PagerDuty Events v2</option>
                </select>
              </label>
              {alertsForm.format === 'pagerduty' && (
                <label>
                  PagerDuty routing key
                  <input
                    type="text"
                    value={alertsForm.pagerduty_routing_key}
                    onChange={(e) =>
                      setAlertsForm({ ...alertsForm, pagerduty_routing_key: e.target.value })
                    }
                    placeholder="Integration routing key"
                  />
                </label>
              )}
              <label>
                Min interval (sec)
                <input
                  type="number"
                  min={60}
                  max={3600}
                  value={alertsForm.min_interval_sec}
                  onChange={(e) =>
                    setAlertsForm({ ...alertsForm, min_interval_sec: Number(e.target.value) })
                  }
                />
              </label>
              <div className="modal-actions">
                <button
                  type="button"
                  className="inline-btn"
                  onClick={() => runAlertTest.mutate()}
                  disabled={runAlertTest.isPending}
                >
                  {runAlertTest.isPending ? 'Sending…' : 'Send test alert'}
                </button>
                <button type="submit" className="inline-btn primary" disabled={saveAlerts.isPending}>
                  {saveAlerts.isPending ? 'Saving…' : 'Save alert settings'}
                </button>
              </div>
              {alertMessage && <p className="settings-hint">{alertMessage}</p>}
            </form>
          </article>
        )}

        {health.data?.mock_mode && mockScenario.data && (
          <article className="card settings-card">
            <h3>Mock Scenario</h3>
            <p className="settings-hint">Switch simulated failure modes for demos and testing.</p>
            <label>
              Active scenario
              <select
                value={mockScenario.data.scenario}
                onChange={(e) => switchScenario.mutate(e.target.value)}
                disabled={switchScenario.isPending}
              >
                {mockScenario.data.available.map((scenario) => (
                  <option key={scenario} value={scenario}>
                    {scenario.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            </label>
          </article>
        )}

        <article className="card settings-card">
          <h3>Encryption Key</h3>
          {encryption.data && (
            <div className="encryption-wizard">
              <p className={encryption.data.is_dev_default ? 'widget-error' : 'widget-muted'}>
                {encryption.data.message}
              </p>
              <ol className="help-steps">
                <li>Generate a strong secret: <code>openssl rand -hex 32</code></li>
                <li>Set <code>DASHBOARD_SECRET_KEY</code> in <code>.env</code> or the systemd unit</li>
                <li>Restart the backend service</li>
                <li>Run the test below to confirm round-trip encryption</li>
              </ol>
              <button
                type="button"
                className="inline-btn"
                onClick={() => runEncryptionTest.mutate()}
                disabled={runEncryptionTest.isPending}
              >
                {runEncryptionTest.isPending ? 'Testing…' : 'Test encryption'}
              </button>
              {encryptionMessage && <p className="settings-hint">{encryptionMessage}</p>}
            </div>
          )}
        </article>
      </div>
    </section>
  )
}