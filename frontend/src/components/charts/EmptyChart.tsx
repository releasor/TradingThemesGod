/** 图表空状态组件
 *
 * 当图表没有数据时显示占位提示。
 */

import { memo } from 'react'
import { Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyChartProps {
  /** 提示信息 */
  message?: string
  /** 自定义类名 */
  className?: string
}

/** 图表空状态组件 */
export const EmptyChart = memo(function EmptyChart({ message = '暂无数据', className }: EmptyChartProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed border-muted-foreground/25 bg-muted/30',
        className
      )}
    >
      <Inbox className="h-10 w-10 text-muted-foreground/50" />
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
    </div>
  )
})
