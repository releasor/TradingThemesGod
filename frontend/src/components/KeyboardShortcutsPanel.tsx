/** 快捷键提示面板

显示可用的键盘快捷键。
*/

import { useState, useEffect } from 'react'
import { X, Keyboard } from 'lucide-react'
import { cn } from '@/lib/utils'

/** 快捷键定义 */
interface Shortcut {
  key: string
  description: string
  modifiers?: string[]
}

/** 快捷键列表 */
const shortcuts: Shortcut[] = [
  { key: 'R', description: '刷新数据' },
  { key: 'T', description: '打开题材库' },
  { key: '/', description: '聚焦搜索' },
  { key: '?', description: '显示快捷键帮助' },
  { key: 'Esc', description: '关闭弹窗' },
]

/** 快捷键提示面板属性 */
interface KeyboardShortcutsPanelProps {
  isOpen: boolean
  onClose: () => void
}

/**
 * 快捷键提示面板
 *
 * @example
 * ```tsx
 * const [isOpen, setIsOpen] = useState(false)
 *
 * <KeyboardShortcutsPanel isOpen={isOpen} onClose={() => setIsOpen(false)} />
 * ```
 */
export function KeyboardShortcutsPanel({ isOpen, onClose }: KeyboardShortcutsPanelProps) {
  // ESC 关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-labelledby="shortcuts-title">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* 面板内容 */}
      <div className="relative z-10 w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg">
        {/* 头部 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Keyboard className="h-5 w-5 text-muted-foreground" />
            <h2 id="shortcuts-title" className="text-lg font-semibold text-foreground">
              键盘快捷键
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label="关闭快捷键面板"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 快捷键列表 */}
        <div className="mt-4 space-y-3">
          {shortcuts.map((shortcut) => (
            <div
              key={shortcut.key}
              className="flex items-center justify-between"
            >
              <span className="text-sm text-muted-foreground">
                {shortcut.description}
              </span>
              <div className="flex items-center gap-1">
                {shortcut.modifiers?.map((mod) => (
                  <kbd
                    key={mod}
                    className={cn(
                      'inline-flex h-6 min-w-[24px] items-center justify-center rounded border border-border bg-muted px-1.5 text-xs font-medium text-muted-foreground'
                    )}
                  >
                    {mod}
                  </kbd>
                ))}
                <kbd
                  className={cn(
                    'inline-flex h-6 min-w-[24px] items-center justify-center rounded border border-border bg-muted px-1.5 text-xs font-medium text-muted-foreground'
                  )}
                >
                  {shortcut.key}
                </kbd>
              </div>
            </div>
          ))}
        </div>

        {/* 底部提示 */}
        <p className="mt-6 text-center text-xs text-muted-foreground">
          按 <kbd className="rounded border border-border bg-muted px-1">Esc</kbd> 关闭
        </p>
      </div>
    </div>
  )
}

/**
 * 快捷键帮助按钮
 */
export function KeyboardShortcutsButton() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
        title="键盘快捷键 (?)"
        aria-label="键盘快捷键帮助"
      >
        <Keyboard className="h-5 w-5" />
      </button>
      <KeyboardShortcutsPanel isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  )
}
