/** 题材表格行骨架屏
 *
 * 加载状态下显示的占位符，与 ThemeTableRow 尺寸一致。
 */

export function ThemeTableSkeleton() {
  return (
    <div className="w-full rounded-lg border border-border bg-card p-4 animate-pulse">
      <div className="flex items-center justify-between gap-4">
        {/* 左侧 */}
        <div className="min-w-0 flex-1">
          <div className="h-4 w-32 rounded bg-muted" />
          <div className="mt-1 h-5 w-16 rounded-full bg-muted" />
        </div>

        {/* 右侧 */}
        <div className="flex items-center gap-4">
          <div className="h-5 w-20 rounded-full bg-muted" />
          <div className="h-3 w-12 rounded bg-muted" />
          <div className="h-3 w-16 rounded bg-muted" />
        </div>
      </div>
    </div>
  )
}
