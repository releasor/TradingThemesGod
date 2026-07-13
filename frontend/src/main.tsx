import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { initWebVitals } from './lib/web-vitals'
import './styles/globals.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 分钟
      retry: 1, // 查询失败重试 1 次
    },
    mutations: {
      retry: false, // mutation 不自动重试，避免重复操作（如触发爬虫）
    },
  },
})

// 初始化 Web Vitals 监控
initWebVitals()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
