import { lazy, Suspense, createContext, useContext, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ScrollToTop } from '@/components/ScrollToTop'
import { NotFound } from '@/components/NotFound'
import { DevPerformancePanel } from '@/components/DevPerformancePanel'
import { ToastContainer, useToast, type Toast, type ToastType } from '@/components/Toast'
import { onApiError } from '@/api/client'
import { Skeleton } from '@/components/ui/skeleton'
import { GlobalSideRaysBackground } from '@/components/GlobalSideRaysBackground'
import { ProtectedRoute } from '@/components/ProtectedRoute'

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
const ModelSettings = lazy(() =>
  import('@/features/settings/ModelSettings').then((m) => ({ default: m.ModelSettings }))
)
const ShortcutsSettings = lazy(() =>
  import('@/features/settings/ShortcutsSettings').then((m) => ({
    default: m.ShortcutsSettings,
  }))
)
const AccountSettings = lazy(() =>
  import('@/features/settings/AccountSettings').then((m) => ({
    default: m.AccountSettings,
  }))
)
const TradingCalendarSettings = lazy(() =>
  import('@/features/settings/TradingCalendarSettings').then((m) => ({
    default: m.TradingCalendarSettings,
  }))
)
const AiStockAnalysis = lazy(() =>
  import('@/features/analysis/AiStockAnalysis').then((m) => ({
    default: m.AiStockAnalysis,
  }))
)
const ReviewDesk = lazy(() =>
  import('@/features/review/ReviewDesk').then((m) => ({ default: m.ReviewDesk }))
)
const CatalystRadar = lazy(() =>
  import('@/features/catalysts/CatalystRadar').then((m) => ({ default: m.CatalystRadar }))
)
const ThemeMiningBoard = lazy(() =>
  import('@/features/mining/ThemeMiningBoard').then((m) => ({ default: m.ThemeMiningBoard }))
)
const MainlineGraphPage = lazy(() =>
  import('@/features/mainline-graph/MainlineGraphPage').then((m) => ({
    default: m.MainlineGraphPage,
  }))
)
const LoginPage = lazy(() =>
  import('@/features/auth/LoginPage').then((m) => ({ default: m.LoginPage }))
)
const RegisterPage = lazy(() =>
  import('@/features/auth/RegisterPage').then((m) => ({ default: m.RegisterPage }))
)

// Toast 上下文
interface ToastContextValue {
  toasts: Toast[]
  addToast: (type: ToastType, message: string, duration?: number) => string
  removeToast: (id: string) => void
  success: (message: string, duration?: number) => string
  error: (message: string, duration?: number) => string
  warning: (message: string, duration?: number) => string
  info: (message: string, duration?: number) => string
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToastContext() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToastContext must be used within ToastProvider')
  }
  return context
}

/** 页面加载占位符 */
function PageSkeleton() {
  return (
    <div className="relative z-10 min-h-screen">
      <header className="sticky top-3 z-20 mx-3 mt-3 rounded-xl border border-border/60 bg-background/80 shadow-lg shadow-black/5 backdrop-blur-md sm:mx-4 sm:mt-4">
        <div className="mx-auto flex w-full max-w-none items-center gap-4 px-3 py-4 sm:px-4 lg:px-5 xl:px-6">
          <Skeleton className="h-8 w-48" />
        </div>
      </header>
      <main className="mx-auto w-full max-w-none px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <div className="space-y-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </main>
    </div>
  )
}

function App() {
  const toast = useToast()

  // 监听 API 错误并显示 Toast 通知
  useEffect(() => {
    const unsubscribe = onApiError((event) => {
      // 根据状态码选择 Toast 类型
      if (event.status >= 500) {
        toast.error(event.message)
      } else if (event.status === 404) {
        toast.warning(event.message)
      } else if (event.status === 0) {
        // 网络错误
        toast.error(event.message)
      } else {
        toast.warning(event.message)
      }
    })

    return unsubscribe
  }, [toast.error, toast.warning])

  return (
    <ErrorBoundary>
      <ToastContext.Provider value={toast}>
        <Router>
          <ScrollToTop />
          <GlobalSideRaysBackground />
          <div className="relative z-10 min-h-screen">
            <Suspense fallback={<PageSkeleton />}>
              <Routes>
                <Route
                  path="/"
                  element={
                    <ErrorBoundary>
                      <ThemeDashboard />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/themes"
                  element={
                    <ErrorBoundary>
                      <ThemeLibrary />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/themes/:id"
                  element={
                    <ErrorBoundary>
                      <ThemeDetail />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/ai-analysis"
                  element={
                    <ErrorBoundary>
                      <AiStockAnalysis />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/review"
                  element={
                    <ErrorBoundary>
                      <ReviewDesk />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/catalysts"
                  element={
                    <ErrorBoundary>
                      <CatalystRadar />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/mining"
                  element={
                    <ErrorBoundary>
                      <ThemeMiningBoard />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/mainline-graph"
                  element={
                    <ErrorBoundary>
                      <MainlineGraphPage />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/login"
                  element={
                    <ErrorBoundary>
                      <LoginPage />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <ErrorBoundary>
                      <RegisterPage />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/settings/models"
                  element={
                    <ErrorBoundary>
                      <ProtectedRoute>
                        <ModelSettings />
                      </ProtectedRoute>
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/settings/shortcuts"
                  element={
                    <ErrorBoundary>
                      <ShortcutsSettings />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/settings/account"
                  element={
                    <ErrorBoundary>
                      <AccountSettings />
                    </ErrorBoundary>
                  }
                />
                <Route
                  path="/settings/calendar"
                  element={
                    <ErrorBoundary>
                      <ProtectedRoute>
                        <TradingCalendarSettings />
                      </ProtectedRoute>
                    </ErrorBoundary>
                  }
                />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </div>
        </Router>
        <ToastContainer toasts={toast.toasts} onClose={toast.removeToast} />
        <DevPerformancePanel />
      </ToastContext.Provider>
    </ErrorBoundary>
  )
}

export default App
