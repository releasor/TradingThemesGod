/** 数据导出按钮组件

提供数据导出功能，支持 CSV 和 JSON 格式。
*/

import { useState, useCallback, memo } from 'react'
import { Download, FileSpreadsheet, FileJson } from 'lucide-react'
import { cn } from '@/lib/utils'
import { type ExportFormat, type ExportThemes, exportThemes } from '@/lib/export'

/** 导出按钮属性 */
interface ExportButtonProps {
  /** 要导出的数据 */
  data: Parameters<typeof exportThemes>[0]
  /** 自定义类名 */
  className?: string
}

/**
 * 数据导出按钮组件
 *
 * @example
 * ```tsx
 * <ExportButton data={themes} />
 * ```
 */
export const ExportButton = memo(function ExportButton({ data, className }: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false)

  const handleExport = useCallback((format: ExportFormat) => {
    exportThemes(data, format)
    setIsOpen(false)
  }, [data])

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent"
      >
        <Download className="h-4 w-4" />
        导出
      </button>

      {isOpen && (
        <>
          {/* 背景遮罩 */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* 下拉菜单 */}
          <div className="absolute right-0 top-full z-50 mt-1 w-48 rounded-lg border border-border bg-card p-1 shadow-lg">
            <button
              onClick={() => handleExport('csv')}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"
            >
              <FileSpreadsheet className="h-4 w-4 text-green-500" />
              导出为 CSV
            </button>
            <button
              onClick={() => handleExport('json')}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"
            >
              <FileJson className="h-4 w-4 text-blue-500" />
              导出为 JSON
            </button>
          </div>
        </>
      )}
    </div>
  )
})
