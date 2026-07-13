/** 图表主题 Hook
 *
 * 检测当前是否为暗色模式，并返回相应的图表颜色配置。
 */

import { useState, useEffect } from 'react'
import { getChartThemeColors } from '@/lib/chart-colors'

/** 检测当前是否为暗色模式 */
function checkDarkMode(): boolean {
  if (typeof document === 'undefined') return false
  return document.documentElement.classList.contains('dark')
}

/** 图表主题 Hook
 *
 * 监听暗色模式变化，返回当前图表颜色配置。
 */
export function useChartTheme() {
  const [isDark, setIsDark] = useState(checkDarkMode)

  useEffect(() => {
    // 初始检查
    setIsDark(checkDarkMode())

    // 监听 class 变化
    const observer = new MutationObserver(() => {
      setIsDark(checkDarkMode())
    })

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })

    return () => observer.disconnect()
  }, [])

  return {
    isDark,
    colors: getChartThemeColors(isDark),
  }
}
