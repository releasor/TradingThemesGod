/** 404 页面组件

当用户访问不存在的路由时显示。
*/

import { useNavigate } from 'react-router-dom'
import { Home, ArrowLeft, Search } from 'lucide-react'

/**
 * 404 页面组件
 *
 * @example
 * ```tsx
 * <Route path="*" element={<NotFound />} />
 * ```
 */
export function NotFound() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="mx-auto max-w-md text-center">
        {/* 404 图标 */}
        <div className="mb-6 text-8xl font-bold text-muted-foreground/30">
          404
        </div>

        {/* 标题 */}
        <h1 className="mb-2 text-2xl font-bold text-foreground">
          页面不存在
        </h1>

        {/* 描述 */}
        <p className="mb-8 text-muted-foreground">
          抱歉，您访问的页面不存在或已被移除。请检查 URL 是否正确。
        </p>

        {/* 操作按钮 */}
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={() => navigate('/')}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Home className="h-4 w-4" />
            返回首页
          </button>
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent"
          >
            <ArrowLeft className="h-4 w-4" />
            返回上页
          </button>
          <button
            onClick={() => navigate('/themes')}
            className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent"
          >
            <Search className="h-4 w-4" />
            浏览题材库
          </button>
        </div>
      </div>
    </div>
  )
}
