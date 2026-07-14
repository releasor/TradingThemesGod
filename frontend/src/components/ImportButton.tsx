/** 数据导入按钮组件

提供数据导入功能，支持 CSV 和 JSON 格式。
*/

import { useState, useRef, memo } from 'react'
import { Upload, FileSpreadsheet, FileJson, X, Check, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { type ImportResult, importFromFile } from '@/lib/import'

/** 导入按钮属性 */
interface ImportButtonProps<T extends Record<string, unknown>> {
  /** 列配置（CSV 格式需要） */
  columns?: { key: keyof T; title: string }[]
  /** 导入成功回调 */
  onImport: (data: T[]) => void
  /** 自定义类名 */
  className?: string
}

/**
 * 数据导入按钮组件
 *
 * @example
 * ```tsx
 * <ImportButton
 *   columns={[
 *     { key: 'name', title: '名称' },
 *     { key: 'code', title: '代码' },
 *   ]}
 *   onImport={(data) => console.log(data)}
 * />
 * ```
 */
export const ImportButton = memo(function ImportButton<T extends Record<string, unknown>>({
  columns,
  onImport,
  className,
}: ImportButtonProps<T>) {
  const [isOpen, setIsOpen] = useState(false)
  const [result, setResult] = useState<ImportResult<T> | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (file: File) => {
    const importResult = await importFromFile<T>(file, columns)
    setResult(importResult)

    if (importResult.success && importResult.data.length > 0) {
      onImport(importResult.data)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const reset = () => {
    setResult(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent"
      >
        <Upload className="h-4 w-4" />
        导入
      </button>

      {isOpen && (
        <>
          {/* 背景遮罩 */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => {
              setIsOpen(false)
              reset()
            }}
          />

          {/* 导入面板 */}
          <div className="absolute right-0 top-full z-50 mt-1 w-80 rounded-lg border border-border bg-card p-4 shadow-lg">
            {/* 标题 */}
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">导入数据</h3>
              <button
                onClick={() => {
                  setIsOpen(false)
                  reset()
                }}
                className="rounded p-1 text-muted-foreground hover:bg-accent"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* 文件拖放区域 */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className="mt-4 flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-6"
            >
              <Upload className="h-8 w-8 text-muted-foreground" />
              <p className="mt-2 text-sm text-muted-foreground">
                拖放文件到此处，或
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="mt-1 text-sm text-primary hover:underline"
              >
                点击选择文件
              </button>
              <p className="mt-1 text-xs text-muted-foreground">
                支持 CSV 和 JSON 格式
              </p>
            </div>

            {/* 隐藏的文件输入 */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.json"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) {
                  handleFileSelect(file)
                }
              }}
              className="hidden"
            />

            {/* 导入结果 */}
            {result && (
              <div className="mt-4">
                {result.success ? (
                  <div className="flex items-center gap-2 rounded-md bg-green-50 p-3 text-sm text-green-800 dark:bg-green-950 dark:text-green-200">
                    <Check className="h-4 w-4" />
                    <span>成功导入 {result.imported} 条数据</span>
                  </div>
                ) : (
                  <div className="rounded-md bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-200">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4" />
                      <span>导入失败</span>
                    </div>
                    {result.errors.length > 0 && (
                      <ul className="mt-2 list-disc pl-5">
                        {result.errors.slice(0, 3).map((error, i) => (
                          <li key={i}>{error}</li>
                        ))}
                        {result.errors.length > 3 && (
                          <li>...还有 {result.errors.length - 3} 个错误</li>
                        )}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 支持的格式说明 */}
            <div className="mt-4 space-y-1 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <FileSpreadsheet className="h-3 w-3" />
                <span>CSV: 需要包含表头行</span>
              </div>
              <div className="flex items-center gap-1">
                <FileJson className="h-3 w-3" />
                <span>JSON: 数组格式</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
})
