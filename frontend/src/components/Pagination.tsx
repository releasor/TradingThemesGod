/** 分页控件组件
 *
 * 提供页码导航，支持首页/末页和前后翻页。
 * 支持每页显示数量选择和跳转到指定页。
 */

import { useState, memo, useCallback } from 'react'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  pageSize?: number
  pageSizeOptions?: number[]
  onPageSizeChange?: (size: number) => void
  showPageSizeSelector?: boolean
  showJumpToPage?: boolean
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

export const Pagination = memo(function Pagination({
  page,
  totalPages,
  onPageChange,
  pageSize = 20,
  pageSizeOptions = [10, 20, 50, 100],
  onPageSizeChange,
  showPageSizeSelector = false,
  showJumpToPage = false,
}: PaginationProps) {
  const [jumpValue, setJumpValue] = useState('')

  if (totalPages <= 1) return null

  const visiblePages = getVisiblePages(page, totalPages)

  const handleJump = useCallback(() => {
    const pageNum = parseInt(jumpValue, 10)
    if (pageNum >= 1 && pageNum <= totalPages) {
      onPageChange(pageNum)
      setJumpValue('')
    }
  }, [jumpValue, totalPages, onPageChange])

  return (
    <nav className="flex items-center justify-center gap-4" aria-label="分页导航">
      {/* 每页显示数量选择器 */}
      {showPageSizeSelector && onPageSizeChange && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>每页</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="rounded-xl border border-input bg-background px-2 py-1 text-sm"
            aria-label="每页显示数量"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
          <span>条</span>
        </div>
      )}

      <div className="flex items-center gap-1">
      {/* 首页 */}
      <button
        onClick={() => onPageChange(1)}
        disabled={page === 1}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-xl text-sm',
          'hover:bg-accent transition-colors',
          'disabled:pointer-events-none disabled:opacity-50',
        )}
        title="首页"
        aria-label="首页"
      >
        <ChevronsLeft className="h-4 w-4" />
      </button>

      {/* 上一页 */}
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-xl text-sm',
          'hover:bg-accent transition-colors',
          'disabled:pointer-events-none disabled:opacity-50',
        )}
        title="上一页"
        aria-label="上一页"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      {/* 页码 */}
      {visiblePages.map((p, i) =>
        p === '...' ? (
          <span key={`ellipsis-${i}`} className="px-2 text-muted-foreground" aria-hidden="true">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            aria-current={p === page ? 'page' : undefined}
            className={cn(
              'inline-flex h-8 min-w-8 items-center justify-center rounded-xl px-2 text-sm',
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
          'inline-flex h-8 w-8 items-center justify-center rounded-xl text-sm',
          'hover:bg-accent transition-colors',
          'disabled:pointer-events-none disabled:opacity-50',
        )}
        title="下一页"
        aria-label="下一页"
      >
        <ChevronRight className="h-4 w-4" />
      </button>

      {/* 末页 */}
      <button
        onClick={() => onPageChange(totalPages)}
        disabled={page === totalPages}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-xl text-sm',
          'hover:bg-accent transition-colors',
          'disabled:pointer-events-none disabled:opacity-50',
        )}
        title="末页"
        aria-label="末页"
      >
        <ChevronsRight className="h-4 w-4" />
      </button>
      </div>

      {/* 跳转到指定页 */}
      {showJumpToPage && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground" role="group" aria-label="跳转到指定页">
          <span>跳转</span>
          <input
            type="number"
            min={1}
            max={totalPages}
            value={jumpValue}
            onChange={(e) => setJumpValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleJump()}
            className="w-16 rounded-xl border border-input bg-background px-2 py-1 text-center text-sm"
            placeholder="页码"
            aria-label="跳转到页码"
          />
          <button
            onClick={handleJump}
            className="rounded-xl bg-primary px-2 py-1 text-xs text-primary-foreground hover:bg-primary/90"
          >
            确定
          </button>
        </div>
      )}
    </nav>
  )
})
