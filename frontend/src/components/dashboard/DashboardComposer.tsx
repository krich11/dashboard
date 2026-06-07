import { useCallback, useMemo, useState } from 'react'
import GridLayout, { type Layout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import type { Dashboard, WidgetInstance } from '../../types/api'
import { getWidgetComponent, widgetRegistry } from '../widgets/registry'
import { WidgetConfigModal } from './WidgetConfigModal'

interface Props {
  dashboard: Dashboard
  editMode: boolean
  onChange: (widgets: WidgetInstance[]) => void
}

function toLayout(widgets: WidgetInstance[]): Layout[] {
  return widgets.map((w) => ({
    i: w.id,
    x: w.grid_x,
    y: w.grid_y,
    w: w.grid_w,
    h: w.grid_h,
    minW: 2,
    minH: 2,
  }))
}

function fromLayout(layout: Layout[], widgets: WidgetInstance[]): WidgetInstance[] {
  const byId = Object.fromEntries(widgets.map((w) => [w.id, w]))
  return layout.map((item) => {
    const existing = byId[item.i]
    return {
      ...existing,
      grid_x: item.x,
      grid_y: item.y,
      grid_w: item.w,
      grid_h: item.h,
    }
  })
}

export function DashboardComposer({ dashboard, editMode, onChange }: Props) {
  const [configTarget, setConfigTarget] = useState<WidgetInstance | null>(null)
  const layout = useMemo(() => toLayout(dashboard.widgets), [dashboard.widgets])

  const handleLayoutChange = useCallback(
    (next: Layout[]) => {
      if (!editMode) return
      onChange(fromLayout(next, dashboard.widgets))
    },
    [dashboard.widgets, editMode, onChange],
  )

  function addWidget(type: string) {
    const def = widgetRegistry.find((w) => w.type === type)
    if (!def) return
    const nextY = dashboard.widgets.reduce((max, w) => Math.max(max, w.grid_y + w.grid_h), 0)
    const newWidget: WidgetInstance = {
      id: crypto.randomUUID(),
      dashboard_id: dashboard.id,
      widget_type: type,
      title: def.title,
      config: {},
      grid_x: 0,
      grid_y: nextY,
      grid_w: 4,
      grid_h: 3,
    }
    onChange([...dashboard.widgets, newWidget])
  }

  function removeWidget(widgetId: string) {
    onChange(dashboard.widgets.filter((w) => w.id !== widgetId))
  }

  function saveConfig(widgetId: string, config: Record<string, unknown>, title: string) {
    onChange(
      dashboard.widgets.map((w) => (w.id === widgetId ? { ...w, config, title } : w)),
    )
  }

  return (
    <div className="composer">
      {editMode && (
        <aside className="widget-palette card">
          <h4>Widget Palette</h4>
          {widgetRegistry.map((w) => (
            <button key={w.type} type="button" className="palette-btn" onClick={() => addWidget(w.type)}>
              + {w.title}
            </button>
          ))}
        </aside>
      )}

      <GridLayout
        className="dashboard-grid"
        layout={layout}
        cols={12}
        rowHeight={30}
        width={1100}
        isDraggable={editMode}
        isResizable={editMode}
        onLayoutChange={handleLayoutChange}
        draggableHandle=".widget-drag-handle"
      >
        {dashboard.widgets.map((widget) => {
          const Component = getWidgetComponent(widget.widget_type)
          return (
            <div key={widget.id} className="grid-widget-wrap">
              {editMode && (
                <div className="widget-toolbar">
                  <span className="widget-drag-handle">⠿</span>
                  <button type="button" className="inline-btn" onClick={() => setConfigTarget(widget)}>
                    Config
                  </button>
                  <button type="button" className="inline-btn" onClick={() => removeWidget(widget.id)}>
                    Remove
                  </button>
                </div>
              )}
              {Component ? (
                <Component config={widget.config} />
              ) : (
                <article className="widget muted">Unknown widget: {widget.widget_type}</article>
              )}
            </div>
          )
        })}
      </GridLayout>

      <WidgetConfigModal
        widget={configTarget}
        onClose={() => setConfigTarget(null)}
        onSave={saveConfig}
      />
    </div>
  )
}