import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AppLayout } from './components/layout/AppLayout'
import { DashboardsPage } from './pages/DashboardsPage'
import { HelpPage } from './pages/HelpPage'
import { InventoryPage } from './pages/InventoryPage'
import { OverviewPage } from './pages/OverviewPage'
import { NocPage } from './pages/NocPage'
import { SettingsPage } from './pages/SettingsPage'
import './index.css'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <BrowserRouter>
          <Routes>
          <Route path="noc" element={<NocPage />} />
          <Route element={<AppLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="inventory" element={<InventoryPage />} />
            <Route path="dashboards" element={<DashboardsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="help" element={<HelpPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  )
}

export default App