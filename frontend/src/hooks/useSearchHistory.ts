/** 搜索历史 Hook

管理用户的搜索历史记录。
*/

import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'search-history'
const MAX_HISTORY = 10

/**
 * 搜索历史 Hook
 *
 * @example
 * ```tsx
 * const { history, addSearch, clearHistory } = useSearchHistory()
 *
 * // 添加搜索记录
 * addSearch('人工智能')
 *
 * // 显示搜索历史
 * {history.map(item => <div key={item}>{item}</div>)}
 * ```
 */
export function useSearchHistory() {
  const [history, setHistory] = useState<string[]>([])

  // 从 localStorage 加载历史
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        setHistory(JSON.parse(stored))
      }
    } catch {
      // 解析失败，忽略
    }
  }, [])

  // 添加搜索记录
  const addSearch = useCallback((query: string) => {
    if (!query.trim()) return

    setHistory((prev) => {
      // 移除重复项
      const filtered = prev.filter((item) => item !== query)
      // 添加到开头
      const newHistory = [query, ...filtered].slice(0, MAX_HISTORY)

      // 保存到 localStorage
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory))
      } catch {
        // 存储失败，忽略
      }

      return newHistory
    })
  }, [])

  // 清除历史
  const clearHistory = useCallback(() => {
    setHistory([])
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      // 忽略
    }
  }, [])

  // 删除单条记录
  const removeSearch = useCallback((query: string) => {
    setHistory((prev) => {
      const newHistory = prev.filter((item) => item !== query)
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory))
      } catch {
        // 忽略
      }
      return newHistory
    })
  }, [])

  return {
    history,
    addSearch,
    clearHistory,
    removeSearch,
  }
}
