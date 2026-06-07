import { useEffect } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { RefreshControl } from './RefreshControl'
import { SystemStatusBadge } from './SystemStatusBadge'

const navItems = [
  { to: '/', label: 'Overview' },
  { to: '/inventory', label: 'Inventory' },
  { to: '/dashboards', label: 'Dashboards' },
  { to: '/settings', label: 'Settings' },
  { to: '/help', label: 'Help' },
  { to: '/noc', label: 'NOC' },
]

export function AppLayout() {
  const navigate = useNavigate()

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.altKey && event.key.toLowerCase() === 'n') {
        event.preventDefault()
        navigate('/noc')
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [navigate])

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Datacenter Dashboard</p>
          <h1>Operations Console</h1>
        </div>
        <div className="header-actions">
          <SystemStatusBadge />
          <RefreshControl />
          <nav className="app-nav">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                end={item.to === '/'}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}