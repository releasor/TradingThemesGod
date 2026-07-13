/** 自动刷新 Hook

提供数据自动刷新功能，支持配置刷新间隔。
*/

import { useState, useEffect, useCallback, useRef } from 'react'

/** 自动刷新配置 */
interface AutoRefreshOptions {
  /** 刷新间隔（毫秒） */
  interval: number
  /** 是否启用 */
  enabled?: boolean
  /** 刷新回调 */
  onRefresh: () => void
}

/**
 * 自动刷新 Hook
 *
 * @example
 * ```tsx
 * const { isAutoRefresh, toggleAutoRefresh, refreshInterval, setRefreshInterval } = useAutoRefresh({
 *   interval: 30000, // 30 秒
 *   onRefresh: () => refetch(),
 * })
 *
 * // 切换自动刷新
 * <button onClick={toggleAutoRefresh}>
 *   {isAutoRefresh ? '停止自动刷新' : '开启自动刷新'}
 * </button>
 *
 * // 设置刷新间隔
 * <select value={refreshInterval} onChange={(e) => setRefreshInterval(Number(e.target.value))}>
 *   <option value={10000}>10 秒</option>
 *   <option value={30000}>30 秒</option>
 *   <option value={60000}>1 分钟</option>
 * </select>
 * ```
 */
export function useAutoRefresh({ interval, enabled = false, onRefresh }: AutoRefreshOptions) {
  const [isAutoRefresh, setIsAutoRefresh] = useState(enabled)
  const [refreshInterval, setRefreshInterval] = useState(interval)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 清除定时器
  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  // 启动定时器
  const startTimer = useCallback(() => {
    clearTimer()
    timerRef.current = setInterval(() => {
      onRefresh()
    }, refreshInterval)
  }, [clearTimer, onRefresh, refreshInterval])

  // 切换自动刷新
  const toggleAutoRefresh = useCallback(() => {
    setIsAutoRefresh((prev) => !prev)
  }, [])

  // 启用/禁用自动刷新
  const setAutoRefresh = useCallback((value: boolean) => {
    setIsAutoRefresh(value)
  }, [])

  // 管理定时器
  useEffect(() => {
    if (isAutoRefresh) {
      startTimer()
    } else {
      clearTimer()
    }

    return clearTimer
  }, [isAutoRefresh, startTimer, clearTimer])

  // 更新间隔时重启定时器
  useEffect(() => {
    if (isAutoRefresh) {
      startTimer()
    }
  }, [refreshInterval, isAutoRefresh, startTimer])

  return {
    isAutoRefresh,
    toggleAutoRefresh,
    setAutoRefresh,
    refreshInterval,
    setRefreshInterval,
  }
}
