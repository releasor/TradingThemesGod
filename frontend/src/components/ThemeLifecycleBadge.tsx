/** 题材生命周期阶段徽章 */

import { cn } from '@/lib/utils'
import {
  LIFECYCLE_STAGE_LABEL,
  type LifecycleStage,
} from '@/types/short-term'

const STAGE_CLASS: Record<LifecycleStage, string> = {
  germination: 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300',
  fermentation: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  climax: 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300',
  divergence: 'border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300',
  ebb: 'border-slate-500/30 bg-slate-500/10 text-slate-600 dark:text-slate-300',
}

interface ThemeLifecycleBadgeProps {
  stage?: LifecycleStage | null
  className?: string
}

export function ThemeLifecycleBadge({ stage, className }: ThemeLifecycleBadgeProps) {
  if (!stage || !(stage in STAGE_CLASS)) return null
  return (
    <span
      data-testid={`lifecycle-badge-${stage}`}
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
        STAGE_CLASS[stage],
        className
      )}
    >
      {LIFECYCLE_STAGE_LABEL[stage]}
    </span>
  )
}
