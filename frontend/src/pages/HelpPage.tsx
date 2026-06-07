export function HelpPage() {
  return (
    <section className="page">
      <div className="page-header">
        <h2>Help</h2>
        <p>Quick reference for operators and LLM-assisted dashboard authoring.</p>
      </div>

      <div className="help-grid">
        <article className="card">
          <h3>Navigation</h3>
          <ul>
            <li><strong>Overview</strong> — default dashboard with high-level status widgets.</li>
            <li><strong>Inventory</strong> — device table, CSV import, credential/connector editing, poll now.</li>
            <li><strong>Dashboards</strong> — compose layouts, export/import JSON, multi-dashboard tabs.</li>
            <li><strong>Settings</strong> — collector tuning, reachability targets, encryption setup.</li>
          </ul>
        </article>

        <article className="card">
          <h3>Mock mode</h3>
          <p>
            Set <code>MOCK_MODE=true</code> for development. Use <code>MOCK_SCENARIO</code> to simulate
            <code>all_clear</code>, <code>devices_down</code>, <code>internet_degraded</code>, or
            <code>mixed</code> conditions.
          </p>
        </article>

        <article className="card">
          <h3>LLM dashboard authoring</h3>
          <p>
            Widget catalog: <code>GET /api/v1/widgets/catalog</code>. Export an existing dashboard from
            the Dashboards page, edit the JSON, then import via UI or
            <code>POST /api/v1/dashboards/import</code>.
          </p>
          <p>
            Schemas live in <code>backend/schemas/json/</code> and <code>examples/dashboard-default.json</code>.
            See <code>docs/LLM_INTEGRATION.md</code> in the repository.
          </p>
        </article>

        <article className="card">
          <h3>Observability</h3>
          <p>
            Scrape <code>GET /metrics</code> with Prometheus (<code>deploy/prometheus.yml</code>).
            Import <code>examples/grafana-dashboard.json</code> for starter panels.
          </p>
          <p>
            Configure webhook alerts in Settings (JSON or Slack format). Use <strong>Send test alert</strong>
            to verify delivery before enabling.
          </p>
        </article>

        <article className="card">
          <h3>Production deploy</h3>
          <ol className="help-steps">
            <li>Build frontend: <code>cd frontend && npm run build</code></li>
            <li>Copy <code>frontend/dist</code> to your host</li>
            <li>Install backend deps and configure <code>.env</code></li>
            <li>Enable <code>deploy/dashboard.service</code> via systemd</li>
            <li>Back up <code>data/dashboard.db</code> regularly</li>
          </ol>
        </article>
      </div>
    </section>
  )
}