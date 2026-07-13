/** 滚动恢复组件

在路由切换时自动滚动到页面顶部。
*/

import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * 滚动到顶部组件
 *
 * 在路由变化时自动滚动到页面顶部。
 */
export function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return null
}
