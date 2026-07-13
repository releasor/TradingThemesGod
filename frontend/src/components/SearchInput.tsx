/** 搜索输入组件

支持搜索历史、搜索建议、清除按钮。
*/

import { useState, useRef, useEffect, useCallback, memo } from 'react'
import { Search, X, Clock, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSearchHistory } from '@/hooks/useSearchHistory'

/** 搜索输入组件属性 */
interface SearchInputProps {
  /** 当前值 */
  value: string
  /** 值变化回调 */
  onChange: (value: string) => void
  /** 占位符 */
  placeholder?: string
  /** 自定义类名 */
  className?: string
  /** 是否自动聚焦 */
  autoFocus?: boolean
}

/**
 * 搜索输入组件
 *
 * @example
 * ```tsx
 * const [search, setSearch] = useState('')
 *
 * <SearchInput
 *   value={search}
 *   onChange={setSearch}
 *   placeholder="搜索题材..."
 * />
 * ```
 */
export const SearchInput = memo(function SearchInput({
  value,
  onChange,
  placeholder = '搜索...',
  className,
  autoFocus,
}: SearchInputProps) {
  const [isFocused, setIsFocused] = useState(false)
  const { history, addSearch, clearHistory, removeSearch } = useSearchHistory()
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // 显示下拉框
  const showDropdown = isFocused && (history.length > 0)

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsFocused(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 提交搜索
  const handleSubmit = useCallback((query: string) => {
    if (query.trim()) {
      addSearch(query.trim())
      onChange(query.trim())
      setIsFocused(false)
    }
  }, [addSearch, onChange])

  // 选择历史记录
  const handleSelectHistory = useCallback((query: string) => {
    onChange(query)
    addSearch(query)
    setIsFocused(false)
    inputRef.current?.blur()
  }, [onChange, addSearch])

  // 清除输入
  const handleClear = useCallback(() => {
    onChange('')
    inputRef.current?.focus()
  }, [onChange])

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {/* 输入框 */}
      <div
        className={cn(
          'flex items-center rounded-lg border bg-background px-3 py-2 transition-colors',
          isFocused ? 'border-primary ring-2 ring-primary/20' : 'border-input'
        )}
      >
        <Search className="h-4 w-4 text-muted-foreground" />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleSubmit(value)
            }
          }}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className="ml-2 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          role="searchbox"
          aria-label={placeholder}
          aria-autocomplete="list"
          aria-expanded={showDropdown}
        />
        {value && (
          <button
            onClick={handleClear}
            className="rounded p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label="清除搜索"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* 下拉框 */}
      {showDropdown && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-border bg-card p-2 shadow-lg" role="listbox" aria-label="搜索历史">
          {/* 搜索历史 */}
          {history.length > 0 && (
            <div>
              <div className="flex items-center justify-between px-2 py-1">
                <span className="text-xs font-medium text-muted-foreground">
                  搜索历史
                </span>
                <button
                  onClick={clearHistory}
                  className="flex items-center gap-1 rounded px-1 py-0.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                  aria-label="清除搜索历史"
                >
                  <Trash2 className="h-3 w-3" />
                  清除
                </button>
              </div>
              <div className="mt-1 space-y-0.5">
                {history.map((item) => (
                  <div
                    key={item}
                    className="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-accent"
                  >
                    <button
                      onClick={() => handleSelectHistory(item)}
                      className="flex flex-1 items-center gap-2 text-sm"
                      role="option"
                    >
                      <Clock className="h-3 w-3 text-muted-foreground" />
                      <span>{item}</span>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        removeSearch(item)
                      }}
                      className="rounded p-0.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      aria-label={`删除搜索记录: ${item}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
})
