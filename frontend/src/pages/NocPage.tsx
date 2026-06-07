import { Maximize2, Minimize2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDefaultDashboard, useHighLevelStatus } from '../hooks/useDashboardData'
import { getWidgetComponent } from '../components/widgets/registry'

export function NocPage() {
  const dashboard = useDefaultDashboard()
  const highLevel = useHighLevelStatus(15_000)
  const [clock, setClock] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setClock(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    document.body.classList.add('noc-mode')
    return () => document.body.classList.remove('noc-mode')
  }, [])

  const banner = highLevel.data?.banner ?? 'unknown'

  return (
    <div className={`noc-shell banner-${banner}`}>
      <header className="noc-header">
        <div>
          <p className="eyebrow">NOC Display</p>
          <h1>{highLevel.data?.banner_text ?? 'Loading operational status…'}</h1>
        </div>
        <div className="noc-meta">
          <span>{clock.toLocaleString()}</span>
          <Link to="/" className="inline-btn" title="Exit NOC mode">
            <Minimize2 size={16} /> Exit
          </Link>
        </div>
      </header>

      {dashboard.data && (
        <div className="noc-widgets">
          {dashboard.data.widgets.map((widget) => {
            const Component = getWidgetComponent(widget.widget_type)
            if (!Component) return null
            return <Component key={widget.id} config={widget.config} />
          })}
        </div>
      )}
    </div>
  )
}

export function NocLaunchButton() {
  return (
    <Link to="/noc" className="inline-btn noc-launch" title="Open NOC fullscreen">
      <Maximize2 size={16} /> NOC
    </Link>
  )
}