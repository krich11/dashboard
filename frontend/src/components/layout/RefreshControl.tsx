import { useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useState } from 'react'

export function RefreshControl() {
  const queryClient = useQueryClient()
  const [spinning, setSpinning] = useState(false)

  async function handleRefresh() {
    setSpinning(true)
    await queryClient.invalidateQueries()
    setTimeout(() => setSpinning(false), 500)
  }

  return (
    <button type="button" className="refresh-btn" onClick={handleRefresh} aria-label="Refresh data">
      <RefreshCw size={16} className={spinning ? 'spin' : ''} />
      Refresh
    </button>
  )
}