import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Pin, PinOff } from 'lucide-react'

import { useToastContext } from '@/App'
import {
  pinToOsDashboard,
  unpinOsDashboardBySource,
  type DashboardSourceType,
} from '@/features/personal-os/api/dashboard'
import { cn } from '@/lib/utils'

type Props = {
  sourceType: DashboardSourceType
  sourceId: number
  pinned?: boolean
  className?: string
  compact?: boolean
}

export function PinToDashboardButton({
  sourceType,
  sourceId,
  pinned = false,
  className,
  compact = false,
}: Props) {
  const toast = useToastContext()
  const queryClient = useQueryClient()

  const mutate = useMutation({
    mutationFn: async () => {
      if (pinned) {
        await unpinOsDashboardBySource(sourceType, sourceId)
        return 'removed' as const
      }
      await pinToOsDashboard({ source_type: sourceType, source_id: sourceId })
      return 'added' as const
    },
    onSuccess: async (mode) => {
      await queryClient.invalidateQueries({ queryKey: ['os-dashboard'] })
      await queryClient.invalidateQueries({ queryKey: ['os-dashboard-pins'] })
      toast.success(mode === 'added' ? '已加入仪表盘' : '已从仪表盘移除')
    },
    onError: (e: Error) => toast.error(e.message || '操作失败'),
  })

  return (
    <button
      type="button"
      className={cn(
        'inline-flex items-center gap-1 rounded-md border border-input px-2 text-xs hover:bg-accent disabled:opacity-50',
        compact ? 'h-7' : 'h-8',
        pinned && 'border-primary/40 bg-primary/10 text-primary',
        className
      )}
      disabled={mutate.isPending}
      aria-pressed={pinned}
      title={pinned ? '从仪表盘移除' : '加入仪表盘'}
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        mutate.mutate()
      }}
    >
      {pinned ? (
        <PinOff className="h-3.5 w-3.5" aria-hidden />
      ) : (
        <Pin className="h-3.5 w-3.5" aria-hidden />
      )}
      {!compact ? <span>{pinned ? '已钉' : '钉到仪表盘'}</span> : null}
    </button>
  )
}
