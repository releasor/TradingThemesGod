/** 股票弹出框组件
 *
 * 点击股票时显示浮动卡片，展示股票详细信息和最近事件。
 * 使用 TanStack Query 在弹出框打开时获取股票详情。
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Minus, Building2, DollarSign, Calendar, AlertCircle } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Skeleton } from '@/components/ui/skeleton'
import { fetchStockDetail } from '@/api/stock'
import { getRiseFallColor } from '@/lib/theme-colors'
import type { StockBrief } from '@/types/stock'

interface StockPopoverProps {
  stock: StockBrief
  children: React.ReactNode
}

/** 格式化市值显示 */
function formatMarketCap(value: number | null): string {
  if (value === null) return '-'
  if (value >= 1_0000_0000) return `${(value / 1_0000_0000).toFixed(2)}亿`
  if (value >= 1_0000) return `${(value / 1_0000).toFixed(2)}万`
  return value.toFixed(2)
}

/** 格式化涨跌幅显示 */
function formatRiseFall(pct: number | null): string {
  if (pct === null) return '-'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

export function StockPopover({ stock, children }: StockPopoverProps) {
  const [open, setOpen] = useState(false)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['stock-detail', stock.code],
    queryFn: () => fetchStockDetail(stock.code),
    enabled: open,
    staleTime: 5 * 60 * 1000, // 5 分钟缓存
  })

  const riseFallColor = getRiseFallColor(stock.rise_fall_pct ?? 0)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent className="w-80" align="start">
        {/* 加载状态 */}
        {isLoading && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-5 w-24" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="space-y-2">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          </div>
        )}

        {/* 错误状态 */}
        {isError && (
          <div className="flex items-center gap-2 py-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            <span>加载失败：{error?.message ?? '未知错误'}</span>
          </div>
        )}

        {/* 数据加载完成 */}
        {!isLoading && !isError && data && (
          <div className="space-y-4">
            {/* 股票头部 */}
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-muted-foreground">
                    {data.code}
                  </span>
                  <span className="font-semibold text-foreground">{data.name}</span>
                </div>
                {data.exchange && (
                  <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                    {data.exchange}
                  </span>
                )}
              </div>
            </div>

            {/* 价格和涨跌幅 */}
            <div className="flex items-baseline gap-3">
              <span className="text-2xl font-bold text-foreground">
                {data.current_price?.toFixed(2) ?? '-'}
              </span>
              <span className={`flex items-center gap-1 text-sm font-medium ${riseFallColor}`}>
                {data.rise_fall_pct !== null && data.rise_fall_pct > 0 && (
                  <TrendingUp className="h-3.5 w-3.5" />
                )}
                {data.rise_fall_pct !== null && data.rise_fall_pct < 0 && (
                  <TrendingDown className="h-3.5 w-3.5" />
                )}
                {data.rise_fall_pct !== null && data.rise_fall_pct === 0 && (
                  <Minus className="h-3.5 w-3.5" />
                )}
                {formatRiseFall(data.rise_fall_pct)}
              </span>
            </div>

            {/* 基本信息 */}
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Building2 className="h-3.5 w-3.5" />
                <span>行业</span>
              </div>
              <span className="text-right text-foreground">
                {data.industry ?? '-'}
              </span>
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <DollarSign className="h-3.5 w-3.5" />
                <span>总市值</span>
              </div>
              <span className="text-right text-foreground">
                {formatMarketCap(data.market_cap)}
              </span>
            </div>

            {/* 最近事件 */}
            {data.recent_events && data.recent_events.length > 0 && (
              <div>
                <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-foreground">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>最近事件</span>
                </div>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {data.recent_events.map((event) => (
                    <div
                      key={event.id}
                      className="rounded-md border border-border p-2 text-xs"
                    >
                      <div className="font-medium text-foreground line-clamp-2">
                        {event.title}
                      </div>
                      {event.published_at && (
                        <div className="mt-1 text-muted-foreground">
                          {new Date(event.published_at).toLocaleDateString('zh-CN')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 无事件 */}
            {data.recent_events && data.recent_events.length === 0 && (
              <div className="text-center text-xs text-muted-foreground">
                暂无最近事件
              </div>
            )}
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
