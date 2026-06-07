import { useDefaultDashboard } from '../hooks/useDashboardData'
import { getWidgetComponent } from '../components/widgets/registry'
import { NocLaunchButton } from './NocPage'

export function OverviewPage() {
  const dashboard = useDefaultDashboard()

  return (
    <section className="page">
      <div className="page-header inventory-header">
        <div>
          <h2>Overview</h2>
          <p>High-level operational status — priority widgets refresh every 30 seconds.</p>
        </div>
        <NocLaunchButton />
      </div>

      {dashboard.isLoading && <p className="widget-muted">Loading dashboard layout...</p>}
      {dashboard.isError && <p className="widget-error">Failed to load dashboard configuration.</p>}

      {dashboard.data && (
        <div className="overview-widgets">
          {dashboard.data.widgets.map((widget) => {
            const Component = getWidgetComponent(widget.widget_type)
            if (!Component) {
              return (
                <article key={widget.id} className="card muted">
                  Widget {widget.widget_type} not yet implemented
                </article>
              )
            }
            return <Component key={widget.id} config={widget.config} />
          })}
        </div>
      )}
    </section>
  )
}