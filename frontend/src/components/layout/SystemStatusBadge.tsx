import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../../api/client'

export function SystemStatusBadge() {
  const { data } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
  })

  if (!data?.mock_mode) {
    return <span className="system-badge production">Production</span>
  }

  return (
    <span className="system-badge mock">
      Mock · {data.mock_scenario.replaceAll('_', ' ')}
    </span>
  )
}