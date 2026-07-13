/** 筛选栏组件
 *
 * 包含搜索输入、分类下拉和标签筛选。
 */

import { useState, useRef } from 'react'
import { Search, X, Tag, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface FilterBarProps {
  searchInput: string
  onSearchChange: (value: string) => void
  categories: string[]
  selectedCategory: string | undefined
  onCategoryChange: (value: string | undefined) => void
  selectedTags: string | undefined
  onTagsChange: (value: string | undefined) => void
  activeFilterCount: number
  onClearFilters: () => void
}

/** 解析标签字符串为数组 */
function parseTags(tags: string | undefined): string[] {
  if (!tags) return []
  return tags.split(',').map((t) => t.trim()).filter(Boolean)
}

/** 将标签数组序列化为字符串 */
function serializeTags(tags: string[]): string {
  return tags.join(',')
}

export function FilterBar({
  searchInput,
  onSearchChange,
  categories,
  selectedCategory,
  onCategoryChange,
  selectedTags,
  onTagsChange,
  activeFilterCount,
  onClearFilters,
}: FilterBarProps) {
  const tags = parseTags(selectedTags)
  const [tagInput, setTagInput] = useState('')
  const tagInputRef = useRef<HTMLInputElement>(null)

  const toggleTag = (tag: string) => {
    const next = tags.includes(tag)
      ? tags.filter((t) => t !== tag)
      : [...tags, tag]
    onTagsChange(next.length > 0 ? serializeTags(next) : undefined)
  }

  const addTagFromInput = () => {
    const trimmed = tagInput.trim()
    if (trimmed && !tags.includes(trimmed)) {
      onTagsChange(serializeTags([...tags, trimmed]))
    }
    setTagInput('')
  }

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addTagFromInput()
    }
  }

  return (
    <div className="space-y-3">
      {/* 搜索框 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          placeholder="搜索题材名称或描述..."
          value={searchInput}
          onChange={(e) => onSearchChange(e.target.value)}
          className={cn(
            'w-full rounded-md border border-input bg-background py-2 pl-10 pr-10 text-sm',
            'placeholder:text-muted-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          )}
        />
        {searchInput && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* 分类下拉 + 标签筛选 */}
      <div className="flex flex-wrap items-center gap-3">
        {/* 分类下拉 */}
        <select
          value={selectedCategory || ''}
          onChange={(e) => onCategoryChange(e.target.value || undefined)}
          className={cn(
            'rounded-md border border-input bg-background px-3 py-1.5 text-sm',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          )}
        >
          <option value="">全部分类</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>

        {/* 标签输入 */}
        <div className="flex items-center gap-1.5">
          <Tag className="h-3.5 w-3.5 text-muted-foreground" />
          <div className="relative">
            <input
              ref={tagInputRef}
              type="text"
              placeholder="添加标签..."
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              onBlur={addTagFromInput}
              className={cn(
                'w-24 rounded-md border border-input bg-background px-2 py-1 text-xs',
                'placeholder:text-muted-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              )}
            />
          </div>
          {tagInput.trim() && (
            <button
              onClick={addTagFromInput}
              className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs text-primary hover:bg-primary/20 transition-colors"
            >
              <Plus className="h-3 w-3" />
            </button>
          )}
        </div>

        {/* 标签 chips */}
        {tags.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            {tags.map((tag) => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={cn(
                  'inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary',
                  'hover:bg-primary/20 transition-colors',
                )}
              >
                {tag}
                <X className="h-3 w-3" />
              </button>
            ))}
          </div>
        )}

        {/* 清除筛选 */}
        {activeFilterCount > 0 && (
          <button
            onClick={onClearFilters}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            清除全部筛选 ({activeFilterCount})
          </button>
        )}
      </div>
    </div>
  )
}
