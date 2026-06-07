import { useEffect, useState } from 'react'
import type { WidgetInstance } from '../../types/api'

interface Props {
  widget: WidgetInstance | null
  onClose: () => void
  onSave: (widgetId: string, config: Record<string, unknown>, title: string) => void
}

export function WidgetConfigModal({ widget, onClose, onSave }: Props) {
  const [title, setTitle] = useState('')
  const [configJson, setConfigJson] = useState('{}')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (widget) {
      setTitle(widget.title)
      setConfigJson(JSON.stringify(widget.config ?? {}, null, 2))
      setError(null)
    }
  }, [widget])

  if (!widget) return null

  function handleSave() {
    if (!widget) return
    try {
      const parsed = JSON.parse(configJson) as Record<string, unknown>
      onSave(widget.id, parsed, title)
      onClose()
    } catch {
      setError('Config must be valid JSON')
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <h3>Configure {widget.widget_type}</h3>
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          Config (JSON)
          <textarea rows={8} value={configJson} onChange={(e) => setConfigJson(e.target.value)} />
        </label>
        {error && <p className="widget-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="inline-btn" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="inline-btn primary" onClick={handleSave}>
            Save
          </button>
        </div>
      </div>
    </div>
  )
}