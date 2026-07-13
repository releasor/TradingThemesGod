import { lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { Skeleton } from '@/components/ui/skeleton'

// 路由级懒加载 - 实现代码分割
const ThemeDashboard = lazy(() =>
  import('@/features/dashboard/ThemeDashboard').then((m) => ({
    default: m.ThemeDashboard,
  }))
)
const ThemeLibrary = lazy(() =>
  import('@/features/themes/ThemeLibrary').then((m) => ({
    default: m.ThemeLibrary,
  }))
)
const ThemeDetail = lazy(() =>
  import('@/features/themes/ThemeDetail').then((m) => ({
    default: m.ThemeDetail,
  }))
)

/** 页面加载占位符 */
function PageSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <Skeleton className="h-8 w-48" />
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="space-y-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </main>
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <div className="min-h-screen bg-background">
          <Suspense fallback={<PageSkeleton />}>
            <Routes>
              <Route path="/" element={<ThemeDashboard />} />
              <Route path="/themes" element={<ThemeLibrary />} />
              <Route path="/themes/:id" element={<ThemeDetail />} />
            </Routes>
          </Suspense>
        </div>
      </Router>
    </ErrorBoundary>
  )
}

export default App
