import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import {
  getCollectorSettings,
  getEncryptionStatus,
  getReachabilitySettings,
  testEncryption,
  updateCollectorSettings,
  updateReachabilitySettings,
} from '../api/client'
import type { CollectorSettings, ReachabilitySettings } from '../types/api'

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
  const reachability = useQuery({
    queryKey: ['settings-reachability'],
    queryFn: getReachabilitySettings,
  })
  const encryption = useQuery({ queryKey: ['settings-encryption'], queryFn: getEncryptionStatus })

  const [collectorForm, setCollectorForm] = useState<CollectorSettings | null>(null)
  const [reachabilityForm, setReachabilityForm] = useState<ReachabilitySettings | null>(null)
  const [encryptionMessage, setEncryptionMessage] = useState<string | null>(null)

  useEffect(() => {
    if (collector.data) setCollectorForm(collector.data)
  }, [collector.data])

  useEffect(() => {
    if (reachability.data) setReachabilityForm(reachability.data)
  }, [reachability.data])

  const saveCollector = useMutation({
    mutationFn: updateCollectorSettings,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings-collector'] }),
  })

  const saveReachability = useMutation({
    mutationFn: updateReachabilitySettings,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings-reachability'] }),
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
        <p>Collector, reachability, and credential encryption configuration.</p>
      </div>

      <div className="settings-grid">
        <article className="card settings-card">
          <h3>Collector</h3>
          <p className="settings-hint">Poll interval changes apply after service restart.</p>
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