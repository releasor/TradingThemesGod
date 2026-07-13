/** 分页控件组件
 *
 * 提供页码导航，支持首页/末页和前后翻页。
 */

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}

/** 生成可见页码列表 */
export function getVisiblePages(current: number, total: number): (number | '...')[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }

  const pages: (number | '...')[] = [1]

  if (current > 3) {
    pages.push('...')
  }

  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  if (current < total - 2) {
    pages.push('...')
  }

  pages.push(total)

  return pages
}

export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null

  const visiblePages = getVisiblePages(page, totalPages)

  return (
    <nav className="flex items-center justify-center gap-1" aria-label="分页">
      {/* 首页 */}
      <button
        onClick={() => onPageChange(1)}
        disabled={page === 1}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-md text-sm',
          'hover:bg-accent transition-colors',
          'disabled:pointer-events-none disabled:opacity-50',
        )}
        title="首页"
      >
        <ChevronsLeft className="h-4 w-4" />
      </button>

      {/* 上一页 */}
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-md text-sm',
          'hover:bg-accent transition-colors',
          'disabled:pointer-events-none disabled:opacity-50',
        )}
        title="上一页"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      {/* 页码 */}
      {visiblePages.map((p, i) =>
        p === '...' ? (
          <span key={`ellipsis-${i}`} className="px-2 text-muted-foreground">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={cn(
              'inline-flex h-8 min-w-8 items-center justify-center rounded-md px-2 text-sm',
              'transition-colors',
              p === page
                ? 'bg-primary text-primary-foreground font-medium'
                : 'hover:bg-accent',
            )}
          >
            {p}
          </button>
        ),
      )}

      {/* 下一页 */}
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page === totalPages}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-md text-sm',
          'hover:bg-accent transition-colors',
          'disabled:pointer-events-none disabled:opacity-50',
        )}
        title="下一页"
      >
        <ChevronRight className="h-4 w-4" />
      </button>

      {/* 末页 */}
      <button
        onClick={() => onPageChange(totalPages)}
        disabled={page === totalPages}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-md text-sm',
          'hover:bg-accent transition-colors',
          'disabled:pointer-events-none disabled:opacity-50',
        )}
        title="末页"
      >
        <ChevronsRight className="h-4 w-4" />
      </button>
    </nav>
  )
}
