import { NavLink, Outlet } from 'react-router-dom'
import { RefreshControl } from './RefreshControl'

const navItems = [
  { to: '/', label: 'Overview' },
  { to: '/inventory', label: 'Inventory' },
  { to: '/dashboards', label: 'Dashboards' },
  { to: '/settings', label: 'Settings' },
  { to: '/help', label: 'Help' },
]

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Datacenter Dashboard</p>
          <h1>Operations Console</h1>
        </div>
        <div className="header-actions">
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