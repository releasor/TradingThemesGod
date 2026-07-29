/** 看板题材源切换：自定义下拉，展开面板跟随亮/暗主题；选项标注题材数与最近刷新时间 */

import { useMemo, useState } from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { DEFAULT_DASHBOARD_SOURCE } from '@/features/dashboard/activeSource'

export interface DashboardSourceOption {
  id: string
  label: string
  /** 该源库内题材数；null 表示尚未加载 */
  themeCount?: number | null
  /** 最近一次成功全量/采集完成时间（ISO） */
  lastRefreshedAt?: string | null
}

interface DashboardSourceSwitcherProps {
  value: string
  sources: DashboardSourceOption[]
  onChange: (source: string) => void
}

function formatRefreshLabel(iso: string | null | undefined): string {
  if (!iso) return '尚未刷新'
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(iso)
  const d = new Date(hasTimezone ? iso : `${iso}Z`)
  if (Number.isNaN(d.getTime())) return '尚未刷新'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function statusLine(src: DashboardSourceOption): string {
  const count =
    typeof src.themeCount === 'number' ? `${src.themeCount} 个题材` : '题材数加载中…'
  if (typeof src.themeCount === 'number' && src.themeCount === 0) {
    return `尚无题材 · ${formatRefreshLabel(src.lastRefreshedAt)}`
  }
  return `${count} · ${formatRefreshLabel(src.lastRefreshedAt)}`
}

export function DashboardSourceSwitcher({
  value,
  sources,
  onChange,
}: DashboardSourceSwitcherProps) {
  const [open, setOpen] = useState(false)
  const options = useMemo(
    () =>
      sources.length > 0
        ? sources
        : [{ id: DEFAULT_DASHBOARD_SOURCE, label: '东方财富' }],
    [sources]
  )
  const current = options.find((item) => item.id === value)
  const currentLabel = current?.label ?? value

  return (
    <div
      className="flex items-center gap-2 text-sm text-muted-foreground"
      data-testid="dashboard-source-switcher"
    >
      <span className="whitespace-nowrap">题材源</span>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label="切换题材数据源"
            aria-expanded={open}
            className={cn(
              'inline-flex h-8 min-w-[9.5rem] max-w-[14rem] items-center justify-between gap-2 rounded-md border border-border bg-background px-2 text-sm text-foreground shadow-sm',
              'transition-colors hover:bg-accent hover:text-accent-foreground',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40'
            )}
          >
            <span className="truncate">{currentLabel}</span>
            <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 opacity-60" aria-hidden />
          </button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-64 p-1">
          <ul role="listbox" aria-label="题材数据源列表" className="space-y-0.5">
            {options.map((src) => {
              const selected = src.id === value
              const empty = typeof src.themeCount === 'number' && src.themeCount === 0
              return (
                <li key={src.id} role="presentation">
                  <button
                    type="button"
                    role="option"
                    aria-selected={selected}
                    aria-label={`${src.label}，${statusLine(src)}`}
                    className={cn(
                      'flex w-full flex-col gap-0.5 rounded-md px-2.5 py-2 text-left text-sm',
                      selected
                        ? 'bg-accent text-accent-foreground'
                        : 'text-popover-foreground hover:bg-accent/70 hover:text-accent-foreground',
                      empty && !selected && 'opacity-80'
                    )}
                    onClick={() => {
                      onChange(src.id)
                      setOpen(false)
                    }}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{src.label}</span>
                      {selected ? (
                        <Check className="h-3.5 w-3.5 shrink-0" aria-hidden />
                      ) : empty ? (
                        <span className="shrink-0 rounded border border-border px-1 py-px text-[10px] text-muted-foreground">
                          未采集
                        </span>
                      ) : null}
                    </span>
                    <span
                      className={cn(
                        'text-[11px] leading-4',
                        selected ? 'text-accent-foreground/75' : 'text-muted-foreground'
                      )}
                      data-testid={`dashboard-source-meta-${src.id}`}
                    >
                      {statusLine(src)}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </PopoverContent>
      </Popover>
    </div>
  )
}
