/** 键盘快捷键 Hook

提供全局键盘快捷键支持。
*/

import { useEffect, useCallback, useRef } from 'react'

/** 快捷键配置 */
interface ShortcutConfig {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  meta?: boolean
  action: () => void
  description?: string
}

/**
 * 键盘快捷键 Hook
 *
 * @param shortcuts - 快捷键配置数组
 *
 * @example
 * ```tsx
 * useKeyboardShortcuts([
 *   { key: 'r', action: () => refetch(), description: '刷新数据' },
 *   { key: '/', action: () => searchInput.focus(), description: '聚焦搜索' },
 * ])
 * ```
 */
export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]): void {
  const shortcutsRef = useRef(shortcuts)
  shortcutsRef.current = shortcuts

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const target = event.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return
      }

      for (const shortcut of shortcutsRef.current) {
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase()
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey
        const altMatch = shortcut.alt ? event.altKey : !event.altKey

        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          event.preventDefault()
          shortcut.action()
          return
        }
      }
    },
    []  // no dependencies needed, uses ref
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

/**
 * 单个快捷键 Hook
 *
 * @param key - 按键
 * @param action - 动作
 * @param modifiers - 修饰键
 */
export function useKeyboardShortcut(
  key: string,
  action: () => void,
  modifiers?: { ctrl?: boolean; shift?: boolean; alt?: boolean }
): void {
  useKeyboardShortcuts([
    { key, action, ...modifiers },
  ])
}
