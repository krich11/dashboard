import { useQuery } from '@tanstack/react-query'
import { getSystemInfo } from '../../api/client'

export function SystemStatusBadge() {
  const { data } = useQuery({
    queryKey: ['system-info'],
    queryFn: getSystemInfo,
    refetchInterval: 30_000,
  })

  if (!data) {
    return <span className="system-badge">…</span>
  }

  if (!data.mock_mode) {
    return <span className="system-badge production">v{data.version} · Production</span>
  }

  return (
    <span className="system-badge mock">
      v{data.version} · Mock · {(data.mock_scenario ?? 'default').replaceAll('_', ' ')}
    </span>
  )
}