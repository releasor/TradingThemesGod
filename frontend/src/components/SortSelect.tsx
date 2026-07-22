/** 排序选择组件
 *
 * 提供排序字段和排序方向选择。
 * 使用 React.memo 避免父组件重渲染时不必要的更新。
 */

import { memo, useCallback } from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ThemeListParams } from '@/types/theme'

type SortBy = ThemeListParams['sort_by']
type SortOrder = ThemeListParams['sort_order']

interface SortSelectProps {
  sortBy: SortBy
  sortOrder: SortOrder
  onSortChange: (sortBy: SortBy, sortOrder: SortOrder) => void
}

const SORT_OPTIONS: { value: SortBy; label: string }[] = [
  { value: 'heat_index', label: '热度指数' },
  { value: 'rise_fall_pct', label: '涨跌幅' },
  { value: 'stock_count', label: '股票数量' },
  { value: 'name', label: '名称' },
]

export const SortSelect = memo(function SortSelect({ sortBy, sortOrder, onSortChange }: SortSelectProps) {
  const handleSortByChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const newSortBy = e.target.value as SortBy
      // 切换字段时，name 默认升序，其他默认降序
      const defaultOrder: SortOrder = newSortBy === 'name' ? 'asc' : 'desc'
      onSortChange(newSortBy, defaultOrder)
    },
    [onSortChange],
  )

  const toggleOrder = useCallback(() => {
    onSortChange(sortBy, sortOrder === 'asc' ? 'desc' : 'asc')
  }, [sortBy, sortOrder, onSortChange])

  return (
    <div className="flex items-center gap-2">
      <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
      <select
        value={sortBy}
        onChange={handleSortByChange}
        className={cn(
          'rounded-xl border border-input bg-background px-2 py-1.5 text-sm',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        )}
      >
        {SORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <button
        onClick={toggleOrder}
        className={cn(
          'inline-flex items-center gap-1 rounded-xl border border-input bg-background px-2 py-1.5 text-sm',
          'hover:bg-accent transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        )}
        title={sortOrder === 'asc' ? '升序' : '降序'}
      >
        {sortOrder === 'asc' ? (
          <ArrowUp className="h-4 w-4" />
        ) : (
          <ArrowDown className="h-4 w-4" />
        )}
      </button>
    </div>
  )
})
