import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import {
  createDashboard,
  deleteDashboard,
  exportDashboard,
  getDashboard,
  importDashboard,
  listDashboards,
  updateDashboard,
} from '../api/client'
import { DashboardComposer } from '../components/dashboard/DashboardComposer'
import type { Dashboard, DashboardExport, WidgetInstance } from '../types/api'

export function DashboardsPage() {
  const queryClient = useQueryClient()
  const dashboards = useQuery({ queryKey: ['dashboards'], queryFn: listDashboards })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [draftWidgets, setDraftWidgets] = useState<WidgetInstance[] | null>(null)

  const activeId = selectedId ?? dashboards.data?.[0]?.id ?? null
  const dashboardQuery = useQuery({
    queryKey: ['dashboard', activeId],
    queryFn: () => getDashboard(activeId!),
    enabled: !!activeId,
  })

  const activeDashboard = dashboardQuery.data
  const displayWidgets = draftWidgets ?? activeDashboard?.widgets ?? []

  const saveMutation = useMutation({
    mutationFn: () =>
      updateDashboard(activeId!, {
        widgets: displayWidgets,
      }),
    onSuccess: () => {
      setDraftWidgets(null)
      setEditMode(false)
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['dashboards'] })
    },
  })

  const createMutation = useMutation({
    mutationFn: () =>
      createDashboard({
        name: `Dashboard ${(dashboards.data?.length ?? 0) + 1}`,
        layout: { cols: 12, rowHeight: 30 },
        widgets: [],
      }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['dashboards'] })
      setSelectedId(created.id)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDashboard(id),
    onSuccess: () => {
      setSelectedId(null)
      queryClient.invalidateQueries({ queryKey: ['dashboards'] })
    },
  })

  const composerDashboard: Dashboard | null = useMemo(() => {
    if (!activeDashboard) return null
    return { ...activeDashboard, widgets: displayWidgets }
  }, [activeDashboard, displayWidgets])

  async function handleExport() {
    if (!activeId) return
    const exported = await exportDashboard(activeId)
    const blob = new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${exported.name.replace(/\s+/g, '-').toLowerCase()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handleImport(file: File) {
    const text = await file.text()
    const parsed = JSON.parse(text) as DashboardExport
    const imported = await importDashboard(parsed)
    queryClient.invalidateQueries({ queryKey: ['dashboards'] })
    setSelectedId(imported.id)
  }

  return (
    <section className="page">
      <div className="page-header dashboards-header">
        <div>
          <h2>Dashboards</h2>
          <p>Compose layouts with drag-and-drop widgets. Export/import JSON for LLM workflows.</p>
        </div>
        <div className="dashboard-actions">
          <button type="button" className="inline-btn" onClick={() => createMutation.mutate()}>
            New Dashboard
          </button>
          <button type="button" className="inline-btn" onClick={() => setEditMode((v) => !v)}>
            {editMode ? 'View Mode' : 'Edit Mode'}
          </button>
          {editMode && (
            <button type="button" className="inline-btn primary" onClick={() => saveMutation.mutate()}>
              Save Layout
            </button>
          )}
          <button type="button" className="inline-btn" onClick={handleExport}>
            Export JSON
          </button>
          <label className="inline-btn file-label">
            Import JSON
            <input
              type="file"
              accept="application/json,.json"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) void handleImport(file)
              }}
            />
          </label>
        </div>
      </div>

      <div className="dashboard-tabs card">
        {dashboards.data?.map((d) => (
          <button
            key={d.id}
            type="button"
            className={d.id === activeId ? 'tab active' : 'tab'}
            onClick={() => {
              setSelectedId(d.id)
              setDraftWidgets(null)
            }}
          >
            {d.name}
            {d.is_default ? ' (default)' : ''}
          </button>
        ))}
        {activeDashboard && !activeDashboard.is_default && (
          <button
            type="button"
            className="inline-btn danger"
            onClick={() => deleteMutation.mutate(activeDashboard.id)}
          >
            Delete
          </button>
        )}
      </div>

      {dashboardQuery.isLoading && <p className="widget-muted">Loading dashboard...</p>}
      {composerDashboard && (
        <DashboardComposer
          dashboard={composerDashboard}
          editMode={editMode}
          onChange={(widgets) => setDraftWidgets(widgets)}
        />
      )}
    </section>
  )
}