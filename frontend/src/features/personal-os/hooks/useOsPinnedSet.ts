import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import {
  listOsDashboardPins,
  type DashboardSourceType,
} from '@/features/personal-os/api/dashboard'

export function useOsPinnedSet() {
  const { data: pins = [] } = useQuery({
    queryKey: ['os-dashboard-pins'],
    queryFn: listOsDashboardPins,
    staleTime: 20_000,
  })

  const set = useMemo(
    () => new Set(pins.map((p) => `${p.source_type}:${p.source_id}`)),
    [pins]
  )

  function isPinned(sourceType: DashboardSourceType, sourceId: number) {
    return set.has(`${sourceType}:${sourceId}`)
  }

  return { pins, isPinned }
}
